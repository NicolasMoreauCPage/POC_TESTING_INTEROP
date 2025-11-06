from fastapi import APIRouter, Depends, Request, Query, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, col
from datetime import datetime
from typing import Optional
import logging
import json
import io
import zipfile

from app.db import get_session
from app.models_endpoints import MessageLog, SystemEndpoint
from app.models import Dossier
from app.db_session_factory import session_factory
from app.services.transport_inbound import on_message_inbound_async
from app.services.fhir_transport import post_fhir_bundle as send_fhir
from app.services.scenario_validation import validate_scenario

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/messages", tags=["messages"])

logger = logging.getLogger("routers.messages")

NEG_STATUSES = {"ack_error", "error"}  # ajuste selon ton usage


def _extract_ipp_and_dossier(payload: str) -> tuple[str, str]:
    """Extract IPP (from PID-3) and dossier/visit number (from PV1-19) from an HL7 v2 message.

    Returns (ipp, dossier) with empty strings when not found. Be tolerant to CR/LF.
    """
    if not isinstance(payload, str):
        return "", ""
    lines = payload.replace("\r\n", "\r").replace("\n", "\r").split("\r")
    ipp = ""
    dossier = ""
    for line in lines:
        if not line:
            continue
        if line.startswith("PID|"):
            parts = line.split("|")
            # PID-3 may contain repetitions separated by '~'
            if len(parts) > 3 and parts[3]:
                rep_first = parts[3].split("~")[0]
                cx = rep_first.split("^")
                cand = cx[0] if cx else ""
                id_type = cx[4] if len(cx) > 4 else ""
                # Prefer identifiers explicitly typed as PI when present
                if (id_type == "PI" or (isinstance(id_type, str) and id_type.endswith(".PI"))) and cand:
                    ipp = cand
                elif cand:
                    ipp = cand
        elif line.startswith("PV1|"):
            parts = line.split("|")
            # PV1-19 = Visit Number (CX)
            if len(parts) > 19 and parts[19]:
                cx = parts[19].split("^")
                dossier = cx[0] if cx else ""
    return ipp, dossier

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def list_messages(
    request: Request,
    session: Session = Depends(get_session),
    endpoint_id: Optional[str] = Query(None),
    date_start: Optional[str] = Query(None),  # "2025-10-01T00:00"
    date_end: Optional[str] = Query(None),    # "2025-10-31T23:59"
    neg_ack_only: bool = Query(False),
    kind: Optional[str] = Query(None),        # "MLLP" | "FHIR"
    direction: Optional[str] = Query(None),   # "in" | "out"
    limit: int = Query(500, ge=1, le=5000),
):
    stmt = select(MessageLog).order_by(MessageLog.created_at.desc())

    # Convertir endpoint_id en int si présent et non vide
    endpoint_id_int = None
    if endpoint_id and endpoint_id.strip():
        try:
            endpoint_id_int = int(endpoint_id)
        except ValueError:
            pass
    
    if endpoint_id_int:
        stmt = stmt.where(MessageLog.endpoint_id == endpoint_id_int)

    if date_start:
        try:
            ds = datetime.fromisoformat(date_start)
            stmt = stmt.where(MessageLog.created_at >= ds)
        except Exception:
            pass

    if date_end:
        try:
            de = datetime.fromisoformat(date_end)
            stmt = stmt.where(MessageLog.created_at <= de)
        except Exception:
            pass

    if neg_ack_only:
        stmt = stmt.where(col(MessageLog.status).in_(NEG_STATUSES))

    if kind in ("MLLP", "FHIR"):
        stmt = stmt.where(MessageLog.kind == kind)
    
    if direction in ("in", "out"):
        stmt = stmt.where(MessageLog.direction == direction)

    msgs = session.exec(stmt.limit(limit)).all()
    endpoints = session.exec(select(SystemEndpoint).order_by(SystemEndpoint.name)).all()
    ep_name = {e.id: e.name for e in endpoints}

    return templates.TemplateResponse(
        request,
        "messages.html",
        {
            "request": request,
            "messages": msgs,
            "endpoints": endpoints,
            "ep_name": ep_name,
            "filters": {
                "endpoint_id": endpoint_id or "",
                "date_start": date_start or "",
                "date_end": date_end or "",
                "neg_ack_only": neg_ack_only,
                "kind": kind or "",
                "direction": direction or "",
                "limit": limit,
            },
        },
    )


@router.get("/rejections", response_class=HTMLResponse)
def list_rejections(
    request: Request,
    session: Session = Depends(get_session),
    endpoint_id: Optional[str] = Query(None),
    date_start: Optional[str] = Query(None),
    date_end: Optional[str] = Query(None),
    kind: Optional[str] = Query("MLLP"),  # default to HL7
    limit: int = Query(2000, ge=1, le=10000),
):
    """Vue d'analyse des rejets groupés par endpoint, IPP et dossier."""
    # Include explicit "rejected" status as well
    reject_statuses = {"rejected", "ack_error", "error"}
    stmt = (
        select(MessageLog)
        .where(col(MessageLog.status).in_(reject_statuses))
        .where(MessageLog.direction == "in")
        .order_by(MessageLog.created_at.desc())
    )

    # Convertir endpoint_id en int si présent et non vide
    endpoint_id_int = None
    if endpoint_id and endpoint_id.strip():
        try:
            endpoint_id_int = int(endpoint_id)
        except ValueError:
            pass

    if endpoint_id_int:
        stmt = stmt.where(MessageLog.endpoint_id == endpoint_id_int)
    if kind in ("MLLP", "FHIR"):
        stmt = stmt.where(MessageLog.kind == kind)
    if date_start:
        try:
            ds = datetime.fromisoformat(date_start)
            stmt = stmt.where(MessageLog.created_at >= ds)
        except Exception:
            pass
    if date_end:
        try:
            de = datetime.fromisoformat(date_end)
            stmt = stmt.where(MessageLog.created_at <= de)
        except Exception:
            pass

    logs = session.exec(stmt.limit(limit)).all()

    # Group rows
    groups: dict[tuple[Optional[int], str, str], dict] = {}
    for m in logs:
        ipp = ""
        dossier = ""
        if m.kind == "MLLP" and m.payload:
            ipp, dossier = _extract_ipp_and_dossier(m.payload)
        key = (m.endpoint_id, ipp, dossier)
        g = groups.get(key)
        if not g:
            g = {
                "endpoint_id": m.endpoint_id,
                "ipp": ipp,
                "dossier": dossier,
                "count": 0,
                "last_created": None,
                "last_status": m.status,
                "last_type": m.message_type,
                "last_ack_excerpt": (m.ack_payload or "")[:280],
                "last_message_id": m.id,
            }
            groups[key] = g
        g["count"] += 1
        if not g["last_created"] or m.created_at > g["last_created"]:
            g["last_created"] = m.created_at
            g["last_status"] = m.status
            g["last_type"] = m.message_type
            g["last_ack_excerpt"] = (m.ack_payload or "")[:280]
            g["last_message_id"] = m.id

    # Sort by most recent group first
    grouped = sorted(groups.values(), key=lambda x: x["last_created"] or datetime.min, reverse=True)

    endpoints = session.exec(select(SystemEndpoint).order_by(SystemEndpoint.name)).all()
    ep_name = {e.id: e.name for e in endpoints}

    return templates.TemplateResponse(
        request,
        "messages_rejections.html",
        {
            "request": request,
            "groups": grouped,
            "endpoints": endpoints,
            "ep_name": ep_name,
            "filters": {
                "endpoint_id": endpoint_id or "",
                "date_start": date_start or "",
                "date_end": date_end or "",
                "kind": kind or "",
                "limit": limit,
            },
        },
    )


@router.get("/by-dossier", response_class=HTMLResponse)
def list_by_dossier(
    request: Request,
    session: Session = Depends(get_session),
    endpoint_id: Optional[str] = Query(None),
    date_start: Optional[str] = Query(None),
    date_end: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),  # "in" or "out"
    limit: int = Query(1000, ge=1, le=10000),
):
    """Vue des messages groupés par dossier avec statut global."""
    stmt = select(MessageLog).where(MessageLog.kind == "MLLP")
    
    # Convertir endpoint_id en int si présent et non vide
    endpoint_id_int = None
    if endpoint_id and endpoint_id.strip():
        try:
            endpoint_id_int = int(endpoint_id)
        except ValueError:
            pass
    
    if endpoint_id_int:
        stmt = stmt.where(MessageLog.endpoint_id == endpoint_id_int)
    if direction in ("in", "out"):
        stmt = stmt.where(MessageLog.direction == direction)
    if date_start:
        try:
            ds = datetime.fromisoformat(date_start)
            stmt = stmt.where(MessageLog.created_at >= ds)
        except Exception:
            pass
    if date_end:
        try:
            de = datetime.fromisoformat(date_end)
            stmt = stmt.where(MessageLog.created_at <= de)
        except Exception:
            pass
    
    stmt = stmt.order_by(MessageLog.created_at.desc()).limit(limit)
    logs = session.exec(stmt).all()
    
    # Grouper par numéro de dossier
    dossiers_map: dict[str, dict] = {}
    
    for msg in logs:
        if not msg.payload:
            continue
        
        ipp, dossier_num = _extract_ipp_and_dossier(msg.payload)
        
        if not dossier_num:
            # Pas de numéro de dossier, ignorer
            continue
        
        if dossier_num not in dossiers_map:
            dossiers_map[dossier_num] = {
                "dossier_number": dossier_num,
                "ipp": ipp,
                "message_count": 0,
                "error_count": 0,
                "warning_count": 0,
                "success_count": 0,
                "last_activity": None,
                "last_message_id": None,
                "endpoint_ids": set(),
                "message_types": set(),
                "message_types_with_errors": set(),  # Types de messages ayant des erreurs
                "has_pam_errors": False,
                "has_ack_errors": False,
            }
        
        dossier_info = dossiers_map[dossier_num]
        dossier_info["message_count"] += 1
        
        # Vérifier si ce message est en erreur
        has_error = False
        
        # Comptabiliser les statuts
        if msg.status in {"error", "ack_error", "rejected"}:
            dossier_info["error_count"] += 1
            has_error = True
            if msg.status == "ack_error":
                dossier_info["has_ack_errors"] = True
        elif msg.pam_validation_status == "fail":
            dossier_info["error_count"] += 1
            dossier_info["has_pam_errors"] = True
            has_error = True
        elif msg.pam_validation_status == "warn":
            dossier_info["warning_count"] += 1
        else:
            dossier_info["success_count"] += 1
        
        # Dernière activité
        if not dossier_info["last_activity"] or msg.created_at > dossier_info["last_activity"]:
            dossier_info["last_activity"] = msg.created_at
            dossier_info["last_message_id"] = msg.id
        
        # Collecter les endpoints et types de messages
        if msg.endpoint_id:
            dossier_info["endpoint_ids"].add(msg.endpoint_id)
        if msg.message_type:
            dossier_info["message_types"].add(msg.message_type)
            # Marquer le type si ce message a une erreur
            if has_error:
                dossier_info["message_types_with_errors"].add(msg.message_type)
    
    # Convertir en liste et calculer le statut global
    dossiers_list = []
    for dossier_num, info in dossiers_map.items():
        # Déterminer le statut global
        if info["error_count"] > 0:
            global_status = "error"
        elif info["warning_count"] > 0:
            global_status = "warning"
        else:
            global_status = "ok"
        
        info["global_status"] = global_status
        info["endpoint_ids"] = list(info["endpoint_ids"])
        info["message_types"] = sorted(list(info["message_types"]))  # Trier pour cohérence
        info["message_types_with_errors"] = list(info["message_types_with_errors"])
        dossiers_list.append(info)
    
    # Trier par dernière activité (plus récent en premier)
    dossiers_list.sort(key=lambda x: x["last_activity"] or datetime.min, reverse=True)
    
    # Récupérer les endpoints pour affichage
    endpoints = session.exec(select(SystemEndpoint).order_by(SystemEndpoint.name)).all()
    ep_name = {e.id: e.name for e in endpoints}
    
    return templates.TemplateResponse(
        request,
        "messages_by_dossier.html",
        {
            "request": request,
            "dossiers": dossiers_list,
            "endpoints": endpoints,
            "ep_name": ep_name,
            "filters": {
                "endpoint_id": endpoint_id or "",
                "date_start": date_start or "",
                "date_end": date_end or "",
                "direction": direction or "",
                "limit": limit,
            },
        },
    )


@router.get("/dossier/{dossier_number}/detail", response_class=HTMLResponse)
def dossier_detail(
    request: Request,
    dossier_number: str,
    session: Session = Depends(get_session),
):
    """Vue détaillée d'un dossier : tous les messages avec statuts et validations."""
    # Récupérer tous les messages du dossier
    stmt = (
        select(MessageLog)
        .where(MessageLog.kind == "MLLP")
        .order_by(MessageLog.created_at.asc())
    )
    all_logs = session.exec(stmt).all()
    
    # Filtrer par numéro de dossier et extraire le statut ACK
    dossier_messages = []
    ack_statuses = {}  # Dictionnaire pour stocker les statuts ACK extraits
    
    for msg in all_logs:
        if not msg.payload:
            continue
        _, dos_num = _extract_ipp_and_dossier(msg.payload)
        if dos_num == dossier_number:
            # Extraire le statut ACK depuis MSA-1
            ack_status = None
            if msg.ack_payload:
                for line in msg.ack_payload.split('\r'):
                    if line.startswith('MSA|'):
                        parts = line.split('|')
                        if len(parts) > 1:
                            ack_status = parts[1]
                        break
            # Stocker dans le dictionnaire
            ack_statuses[msg.id] = ack_status
            dossier_messages.append(msg)
    
    # Récupérer les endpoints pour affichage
    endpoints = session.exec(select(SystemEndpoint)).all()
    ep_map = {e.id: e for e in endpoints}
    
    return templates.TemplateResponse(
        "messages_dossier_detail.html",
        {
            "request": request,
            "dossier_number": dossier_number,
            "messages": dossier_messages,
            "ack_statuses": ack_statuses,
            "ep_map": ep_map,
        },
    )


@router.get("/dossier/{dossier_number}/export")
def dossier_export(
    dossier_number: str,
    session: Session = Depends(get_session),
):
    """Exporte tous les messages d'un dossier dans un fichier ZIP."""
    # Récupérer tous les messages du dossier
    stmt = (
        select(MessageLog)
        .where(MessageLog.kind == "MLLP")
        .order_by(MessageLog.created_at.asc())
    )
    all_logs = session.exec(stmt).all()
    
    # Filtrer par numéro de dossier
    dossier_messages = []
    for msg in all_logs:
        if not msg.payload:
            continue
        _, dos_num = _extract_ipp_and_dossier(msg.payload)
        if dos_num == dossier_number:
            dossier_messages.append(msg)
    
    if not dossier_messages:
        return HTMLResponse(content="Aucun message trouvé pour ce dossier", status_code=404)
    
    # Créer le ZIP en mémoire
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Ajouter un fichier récapitulatif
        summary_lines = [
            f"Dossier: {dossier_number}",
            f"Nombre de messages: {len(dossier_messages)}",
            f"Date d'export: {datetime.now().isoformat()}",
            "",
            "Liste des messages:",
            "",
        ]
        
        for idx, msg in enumerate(dossier_messages, 1):
            # Nom de fichier pour ce message
            msg_prefix = f"message_{idx:03d}_{msg.id}"
            
            # Ajouter le message HL7
            if msg.payload:
                zip_file.writestr(f"{msg_prefix}_message.hl7", msg.payload)
            
            # Ajouter l'ACK si présent
            if msg.ack_payload:
                zip_file.writestr(f"{msg_prefix}_ack.hl7", msg.ack_payload)
            
            # Ajouter le rapport de validation JSON
            validation_report = {
                "message_id": msg.id,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "message_type": msg.message_type,
                "status": msg.status,
                "pam_validation_status": msg.pam_validation_status,
                "pam_validation_issues": json.loads(msg.pam_validation_issues) if msg.pam_validation_issues else [],
            }
            zip_file.writestr(
                f"{msg_prefix}_validation.json",
                json.dumps(validation_report, indent=2, ensure_ascii=False)
            )
            
            # Ajouter au récapitulatif
            summary_lines.append(
                f"{idx}. Message #{msg.id} - {msg.message_type or 'N/A'} - "
                f"{msg.created_at.strftime('%Y-%m-%d %H:%M:%S') if msg.created_at else 'N/A'} - "
                f"Statut: {msg.status}"
            )
            if msg.pam_validation_status == "fail":
                summary_lines.append(f"   ⚠️ Erreurs PAM détectées")
            if msg.status in {"error", "ack_error", "rejected"}:
                # Extraire le texte de l'ACK si disponible
                ack_text = "N/A"
                if msg.ack_payload:
                    for line in msg.ack_payload.split('\r'):
                        if line.startswith('MSA|'):
                            parts = line.split('|')
                            if len(parts) > 3:
                                ack_text = parts[3]
                            break
                summary_lines.append(f"   ❌ Erreur: {ack_text}")
        
        # Écrire le récapitulatif
        zip_file.writestr("README.txt", "\n".join(summary_lines))
    
    # Préparer la réponse
    zip_buffer.seek(0)
    return StreamingResponse(
        io.BytesIO(zip_buffer.read()),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=dossier_{dossier_number}_export.zip"
        },
    )


# --- Place /send routes BEFORE /{message_id} to avoid path conflict ---
@router.get("/send", response_class=HTMLResponse)
def send_message_form(request: Request, session: Session = Depends(get_session)):
    endpoints = session.exec(select(SystemEndpoint).order_by(SystemEndpoint.name)).all()
    return templates.TemplateResponse(request, "send_message.html", {"request": request, "endpoints": endpoints})

@router.post("/send")
async def send_message(request: Request):
    form = await request.form()
    kind = form.get("kind")
    endpoint_id = form.get("endpoint_id")
    payload = form.get("payload")

    # normalize common line endings so transport_inbound sees \r-separated segments
    if isinstance(payload, str):
        # convert CRLF and LF to HL7 segment separator CR
        payload = payload.replace('\r\n', '\r').replace('\n', '\r')
        payload = payload.strip()
    logger.info(f"/messages/send kind={kind} endpoint_id={endpoint_id} payload_len={len(payload) if payload else 0}")

    # HL7 via on_message_inbound
    if kind == "MLLP":
        with session_factory() as s:
            try:
                endpoint_pk = int(endpoint_id) if endpoint_id else None
            except (TypeError, ValueError):
                endpoint_pk = None
            ep = s.get(SystemEndpoint, endpoint_pk) if endpoint_pk else None
            endpoints = s.exec(select(SystemEndpoint).order_by(SystemEndpoint.name)).all()
            if ep and ep.kind != "MLLP":
                return templates.TemplateResponse(
                    request,
                    "send_message.html",
                    {"request": request, "error": "Endpoint invalide", "endpoints": endpoints},
                )
            # allow processing even if no endpoint selected (simulate inbound)
            logger.info(f"Calling on_message_inbound_async with payload length={len(payload)}, endpoint={ep}")
            try:
                ack = await on_message_inbound_async(payload, s, ep)
                logger.info(f"ACK received: {ack[:100] if ack else 'None'}")
            except Exception as e:
                logger.error(f"Error in on_message_inbound_async: {e}", exc_info=True)
                ack = f"ERROR: {str(e)}"
        return templates.TemplateResponse(
            request,
            "send_message_result.html",
            {"request": request, "kind": kind, "ack": ack, "endpoints": endpoints},
        )

    # FHIR inbound simulation: just log and return a simple response
    if kind == "FHIR":
        # try to parse payload as JSON
        import json
        try:
            obj = json.loads(payload)
        except Exception:
            obj = None
        # find endpoint
        with session_factory() as s:
            ep = s.get(SystemEndpoint, int(endpoint_id)) if endpoint_id else None
            log = MessageLog(direction="in", kind="FHIR", endpoint_id=(ep.id if ep else None), payload=payload, ack_payload="", status="received", created_at=datetime.utcnow())
            s.add(log); s.commit(); s.refresh(log)
    return templates.TemplateResponse(request, "send_message_result.html", {"request": request, "kind": kind, "ack": f"Logged message id={log.id}"})

    return templates.TemplateResponse(request, "send_message.html", {"request": request, "error": "Kind non supporté", "endpoints": []})


@router.post("/scan")
async def scan_file_endpoints_manual(request: Request, session: Session = Depends(get_session)):
    """Manually trigger scanning of all file-based endpoints"""
    from app.services.file_poller import scan_file_endpoints
    
    try:
        stats = await scan_file_endpoints(session)
        return {
            "success": True,
            "stats": stats,
            "message": f"Scanned {stats['endpoints_scanned']} endpoints, processed {stats['files_processed']} files"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/scheduler/status")
def get_scheduler_status():
    """Get the status of the file polling scheduler"""
    from app.services.scheduler import get_scheduler
    
    scheduler = get_scheduler()
    return {
        "running": scheduler.running,
        "poll_interval_seconds": scheduler.poll_interval_seconds,
        "next_poll": "in progress" if scheduler.running else "stopped"
    }


@router.get("/validate-dossier", response_class=HTMLResponse)
def validate_dossier_form(request: Request, session: Session = Depends(get_session)):
    """Affiche le formulaire de validation d'un dossier."""
    endpoints = session.exec(select(SystemEndpoint).order_by(SystemEndpoint.name)).all()
    return templates.TemplateResponse(
        request,
        "validate_dossier.html",
        {
            "request": request,
            "endpoints": endpoints,
            "dossier_number": "",
            "scenario_result": None,
        },
    )


@router.post("/validate-dossier", response_class=HTMLResponse)
async def validate_dossier(
    request: Request,
    dossier_number: str = Form(...),
    endpoint_id: Optional[int] = Form(None),
    session: Session = Depends(get_session),
):
    """Valide les messages HL7 reçus/émis pour un dossier donné.
    
    Le numéro de dossier peut être:
    - Un ID interne (Dossier.id)
    - Un numéro de dossier externe (contenu dans PV1-19 des messages)
    """
    logger.info(f"Validation dossier: {dossier_number}, endpoint: {endpoint_id}")
    
    # 1. Rechercher d'abord par ID interne si c'est un nombre
    dossier_from_db = None
    if dossier_number.isdigit():
        dossier_from_db = session.get(Dossier, int(dossier_number))
        if dossier_from_db:
            # On a trouvé un dossier, récupérer son dossier_seq comme identifiant externe
            external_visit_number = str(dossier_from_db.dossier_seq) if dossier_from_db.dossier_seq else None
            logger.info(f"Dossier trouvé par ID: {dossier_from_db.id}, seq: {external_visit_number}")
        else:
            external_visit_number = dossier_number
    else:
        external_visit_number = dossier_number
    
    # 2. Récupérer tous les messages MLLP
    stmt = select(MessageLog).where(MessageLog.kind == "MLLP").order_by(MessageLog.created_at)
    if endpoint_id:
        stmt = stmt.where(MessageLog.endpoint_id == endpoint_id)
    
    all_messages = session.exec(stmt).all()
    logger.info(f"Total messages MLLP: {len(all_messages)}")
    
    # 3. Filtrer les messages correspondant au dossier
    matching_messages = []
    for msg in all_messages:
        if msg.payload:
            ipp, dossier_extracted = _extract_ipp_and_dossier(msg.payload)
            # Matcher par numéro externe (PV1-19) OU par ID interne si on l'a trouvé
            if dossier_extracted == external_visit_number or dossier_extracted == dossier_number:
                matching_messages.append(msg)
                logger.info(f"Message {msg.id} matched: dossier={dossier_extracted}")
    
    logger.info(f"Messages correspondants: {len(matching_messages)}")
    
    # 4. Si aucun message trouvé, retourner une erreur
    if not matching_messages:
        endpoints = session.exec(select(SystemEndpoint).order_by(SystemEndpoint.name)).all()
        return templates.TemplateResponse(
            request,
            "validate_dossier.html",
            {
                "request": request,
                "endpoints": endpoints,
                "dossier_number": dossier_number,
                "scenario_result": None,
                "error": f"Aucun message trouvé pour le dossier '{dossier_number}'",
            },
        )
    
    # 5. Construire le scénario (concaténer les payloads)
    scenario_text = "\n".join(msg.payload for msg in matching_messages if msg.payload)
    
    # 6. Valider le scénario
    scenario_result = validate_scenario(scenario_text)
    
    # 7. Afficher les résultats
    endpoints = session.exec(select(SystemEndpoint).order_by(SystemEndpoint.name)).all()
    return templates.TemplateResponse(
        request,
        "validate_dossier.html",
        {
            "request": request,
            "endpoints": endpoints,
            "dossier_number": dossier_number,
            "scenario_result": scenario_result,
            "messages_count": len(matching_messages),
        },
    )


@router.get("/{message_id}", response_class=HTMLResponse)
def message_detail(message_id: int, request: Request, session: Session = Depends(get_session)):
    m = session.get(MessageLog, message_id)
    if not m:
        return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Message introuvable"}, status_code=404)
    ep = session.get(SystemEndpoint, m.endpoint_id) if m.endpoint_id else None
    
    # Parser le JSON des issues de validation si présent
    validation_issues = None
    if m.pam_validation_issues:
        try:
            validation_issues = json.loads(m.pam_validation_issues)
        except (json.JSONDecodeError, TypeError):
            validation_issues = None
    
    return templates.TemplateResponse(
        request,
        "message_detail.html",
        {"request": request, "m": m, "endpoint": ep, "validation_issues": validation_issues},
    )

