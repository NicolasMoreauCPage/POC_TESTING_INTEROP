from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, col
from datetime import datetime
from typing import Optional
import logging

from app.db import get_session
from app.models_endpoints import MessageLog, SystemEndpoint
from app.db_session_factory import session_factory
from app.services.transport_inbound import on_message_inbound_async
from app.services.fhir_transport import post_fhir_bundle as send_fhir

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
    endpoint_id: Optional[int] = Query(None),
    date_start: Optional[str] = Query(None),  # "2025-10-01T00:00"
    date_end: Optional[str] = Query(None),    # "2025-10-31T23:59"
    neg_ack_only: bool = Query(False),
    kind: Optional[str] = Query(None),        # "MLLP" | "FHIR"
    limit: int = Query(500, ge=1, le=5000),
):
    stmt = select(MessageLog).order_by(MessageLog.created_at.desc())

    if endpoint_id:
        stmt = stmt.where(MessageLog.endpoint_id == endpoint_id)

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
                "limit": limit,
            },
        },
    )


@router.get("/rejections", response_class=HTMLResponse)
def list_rejections(
    request: Request,
    session: Session = Depends(get_session),
    endpoint_id: Optional[int] = Query(None),
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

    if endpoint_id:
        stmt = stmt.where(MessageLog.endpoint_id == endpoint_id)
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


@router.get("/{message_id}", response_class=HTMLResponse)
def message_detail(message_id: int, request: Request, session: Session = Depends(get_session)):
    m = session.get(MessageLog, message_id)
    if not m:
        return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Message introuvable"}, status_code=404)
    ep = session.get(SystemEndpoint, m.endpoint_id) if m.endpoint_id else None
    return templates.TemplateResponse(
        request,
        "message_detail.html",
        {"request": request, "m": m, "endpoint": ep},
    )

