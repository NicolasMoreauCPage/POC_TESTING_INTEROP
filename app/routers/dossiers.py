from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from datetime import datetime
from typing import List
from app.db import get_session, get_next_sequence, peek_next_sequence
from app.models import Dossier, Patient, DossierType
from app.models_endpoints import SystemEndpoint
from app.models_scenarios import ScenarioBinding, InteropScenario
from app.services.emit_on_create import emit_to_senders
from app.services.scenario_runner import send_scenario
from app.form_config import get_field_config, MODEL_FIELDS
from app.utils.flash import flash
from app.dependencies.ght import require_ght_context

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(
    prefix="/dossiers",
    tags=["dossiers"],
    dependencies=[Depends(require_ght_context)],
)

@router.get("", response_class=HTMLResponse)
def list_dossiers(
    request: Request,
    patient_id: int | None = Query(None),
    dossier_type: DossierType | None = Query(None),
    dossier_seq: int | None = Query(None),
    uf: str | None = Query(None),
    admission_type: str | None = Query(None),
    status: str | None = Query(None),
    session=Depends(get_session)
):
    # Construction de la requête de base
    stmt = select(Dossier)
    if patient_id:
        stmt = stmt.where(Dossier.patient_id == patient_id)
        # Récupérer les infos du patient pour le fil d'Ariane
        patient = session.get(Patient, patient_id)
        
    if dossier_type:
        stmt = stmt.where(Dossier.dossier_type == dossier_type)
    
    if dossier_seq:
        stmt = stmt.where(Dossier.dossier_seq == dossier_seq)
    if uf:
        # Filtrer si l'UF correspond à l'une des responsabilités
        stmt = stmt.where(
            (Dossier.uf_medicale == uf) | (Dossier.uf_hebergement == uf) | (Dossier.uf_soins == uf)
        )
    if admission_type:
        stmt = stmt.where(Dossier.admission_type == admission_type)
    if status:
        # Interprétation simple: ACTIF = pas de date de sortie; TERMINE = avec date de sortie
        if status.upper() == "ACTIF":
            stmt = stmt.where(Dossier.discharge_time.is_(None))
        elif status.upper() == "TERMINE":
            stmt = stmt.where(Dossier.discharge_time.is_not(None))

    # Exécuter la requête
    dossiers = session.exec(stmt).all()

    # Préparer les lignes avec les actions détaillées
    rows = [
        {
            "cells": [
                d.dossier_seq, 
                d.id, 
                d.patient_id, 
                d.uf_medicale, 
                d.uf_hebergement, 
                d.uf_soins, 
                getattr(d, 'dossier_type', DossierType.HOSPITALISE).value.capitalize(),
                (getattr(d, 'admission_type', None) or "—"),
                d.admit_time.strftime("%d/%m/%Y %H:%M") if d.admit_time else None,
                d.discharge_time.strftime("%d/%m/%Y %H:%M") if d.discharge_time else None
            ],
            "detail_url": f"/dossiers/{d.id}",
            "context_url": f"/context/dossier/{d.id}",
            "edit_url": f"/dossiers/{d.id}/edit",
            "delete_url": f"/dossiers/{d.id}/delete"
        }
        for d in dossiers
    ]

    # Construire le fil d'Ariane
    breadcrumbs = [{"label": "Dossiers", "url": "/dossiers"}]
    if patient_id and patient:
        breadcrumbs.insert(0, {"label": f"Patient: {patient.family} {patient.given}", "url": f"/patients/{patient_id}"})

    # Définir les filtres de recherche
    filters = [
        {
            "label": "Numéro de dossier",
            "name": "dossier_seq",
            "type": "number",
            "placeholder": "Numéro de dossier",
            "value": dossier_seq
        },
        {
            "label": "UF (méd./héb./soins)",
            "name": "uf",
            "type": "text",
            "placeholder": "Filtrer par UF",
            "value": uf
        },
        {
            "label": "Type de dossier",
            "name": "dossier_type",
            "type": "select",
            "placeholder": "Tous les types",
            "options": [{"value": t.value, "label": t.value.capitalize()} for t in DossierType],
            "value": dossier_type.value if dossier_type else None
        },
        {
            "label": "Type d'admission",
            "name": "admission_type",
            "type": "select",
            "placeholder": "Tous les types",
            "options": [
                {"value": "URGENCE", "label": "Urgence"},
                {"value": "PROGRAMME", "label": "Programmé"},
                {"value": "MUTATION", "label": "Mutation"}
            ],
            "value": admission_type
        },
        {
            "label": "Statut",
            "name": "status",
            "type": "select",
            "placeholder": "Tous les statuts",
            "options": [
                {"value": "ACTIF", "label": "En cours"},
                {"value": "TERMINE", "label": "Terminé"}
            ],
            "value": status
        }
    ]

    # Définir les actions disponibles
    actions = [
        {
            "type": "link",
            "label": "Export FHIR",
            "url": "/dossiers/export/fhir"
        },
        {
            "type": "link",
            "label": "Export HL7",
            "url": "/dossiers/export/hl7"
        }
    ]

    # Construire le contexte complet
    ctx = {
        "request": request,
        "title": "Dossiers" if not patient_id else f"Dossiers du patient {patient.family} {patient.given}",
        "breadcrumbs": breadcrumbs,
    "headers": ["Seq", "ID", "Patient", "UF Méd.", "UF Héb.", "UF Soins", "Type", "Adm.type", "Admission", "Sortie"],
        "rows": rows,
        "new_url": "/dossiers/new" + (f"?patient_id={patient_id}" if patient_id else ""),
        "filters": filters,
        "actions": actions,
        "show_actions": True
    }
    return templates.TemplateResponse(request, "list.html", ctx)

@router.get("/new", response_class=HTMLResponse)
def new_dossier(request: Request, session=Depends(get_session)):
    next_seq = peek_next_sequence(session, "dossier")
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")  # valeur par défaut = maintenant
    # Construction des champs avec la configuration centralisée
    base_fields = [
        {"name": "patient_id", "label": "Patient ID", "type": "number"},
    {"name": "uf_medicale", "label": "UF médicale", "type": "text"},
    {"name": "uf_hebergement", "label": "UF hébergement", "type": "text"},
    {"name": "uf_soins", "label": "UF soins", "type": "text"},
        {"name": "admission_type", "label": "Type d'admission"},
        {"name": "admission_source", "label": "Source d'admission", "type": "text"},
        {"name": "attending_provider", "label": "Médecin responsable (attending)", "type": "text"},
        {"name": "admit_time", "label": "Date d'admission", "type": "datetime-local"},
        {"name": "dossier_seq", "label": "Numéro de séquence", "type": "number"},
        # Add state transition fields so client-side validation can hook into them
        {"name": "current_state", "label": "État courant", "type": "select", "options": ["Pas de venue courante", "Pré-admis consult.ext.", "Pré-admis hospit.", "Hospitalisé", "Absence temporaire", "Consultant externe"]},
        {"name": "event_code", "label": "Code événement", "type": "select", "options": ["A01","A03","A04","A05","A06","A07","A11","A13","A21","A22","A38","A52","A53"]},
    ]
    
    # Enrichir les champs avec la configuration
    fields = []
    for field in base_fields:
        field_name = field["name"]
        config = get_field_config("Dossier", field_name)
        
        if field_name == "admit_time":
            field["value"] = now_str
        elif field_name == "dossier_seq":
            field["value"] = next_seq
            
        # Fusionner la configuration avec les valeurs de base
        field.update(config)
        fields.append(field)
    return templates.TemplateResponse(request, "form.html", {"request": request, "title": "Nouveau dossier", "fields": fields})

@router.post("/new")
def create_dossier(
    request: Request,
    patient_id: int = Form(...),
    uf_medicale: str = Form(None),
    uf_hebergement: str = Form(None),
    uf_soins: str = Form(None),
    admission_type: str = Form(None),
    admission_source: str = Form(None),
    attending_provider: str = Form(None),
    admit_time: str = Form(...),
    dossier_seq: int | None = Form(None),
    session=Depends(get_session),
):
    admit_dt = datetime.fromisoformat(admit_time)
    seq = dossier_seq or get_next_sequence(session, "dossier")
    d = Dossier(
        patient_id=patient_id,
    uf_medicale=uf_medicale if uf_medicale else None,
    uf_hebergement=uf_hebergement if uf_hebergement else None,
    uf_soins=uf_soins if uf_soins else None,
        admission_type=admission_type,
        admission_source=admission_source,
        attending_provider=attending_provider,
        admit_time=admit_dt,
        dossier_seq=seq,
    )
    session.add(d); session.commit()
    emit_to_senders(d, "dossier", session)
    
    # Support AJAX/JSON and HTML responses
    if request.headers.get("Accept") == "application/json":
        return {"message": "Enregistrement réussi", "redirect": "/dossiers"}
    return RedirectResponse(url="/dossiers", status_code=303)


@router.get("/{dossier_id}", response_class=HTMLResponse)
def dossier_detail(dossier_id: int, request: Request, session=Depends(get_session)):

    d = session.get(Dossier, dossier_id)
    if not d:
        return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Dossier introuvable"}, status_code=404)
    # Définir le contexte dossier en session
    request.session["dossier_id"] = d.id
    if hasattr(d, 'patient') and d.patient:
        request.session["patient_id"] = d.patient.id
    session.refresh(d, attribute_names=["patient", "venues"])
    for v in d.venues:
        session.refresh(v, attribute_names=["mouvements"])

    patient = d.patient if hasattr(d, 'patient') else None

    bindings = session.exec(
        select(ScenarioBinding).where(ScenarioBinding.dossier_id == dossier_id)
    ).all()
    scenario_entries = []
    for binding in bindings:
        scenario = session.get(InteropScenario, binding.scenario_id)
        if scenario:
            scenario_entries.append({"binding": binding, "scenario": scenario})

    endpoints = session.exec(
        select(SystemEndpoint)
        .where(SystemEndpoint.is_enabled == True)
        .where(SystemEndpoint.role.in_(["sender", "both"]))
        .order_by(SystemEndpoint.name)
    ).all()

    return templates.TemplateResponse(request, "dossier_detail.html", {
            "request": request,
            "dossier": d,
            "patient": patient,
            "scenario_entries": scenario_entries,
            "replay_endpoints": endpoints,
        })


@router.get("/{dossier_id}/edit", response_class=HTMLResponse)
def edit_dossier(dossier_id: int, request: Request, session=Depends(get_session)):
    d = session.get(Dossier, dossier_id)
    if not d:
        return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Dossier introuvable"}, status_code=404)
    fields = [
        {"label": "Patient ID", "name": "patient_id", "type": "number", "value": d.patient_id},
    {"label": "UF médicale", "name": "uf_medicale", "type": "text", "value": d.uf_medicale},
    {"label": "UF hébergement", "name": "uf_hebergement", "type": "text", "value": d.uf_hebergement},
    {"label": "UF soins", "name": "uf_soins", "type": "text", "value": d.uf_soins},
        {"label": "Type d'admission", "name": "admission_type", "type": "select", "options": ["emergency", "elective", "newborn", "urgent", "other"], "value": getattr(d,'admission_type',None)},
        {"label": "Source d'admission", "name": "admission_source", "type": "text", "value": getattr(d, "admission_source", None)},
        {"label": "Médecin responsable (attending)", "name": "attending_provider", "type": "text", "value": getattr(d,'attending_provider',None)},
        {"label": "Date d’admission", "name": "admit_time", "type": "datetime-local", "value": d.admit_time.strftime('%Y-%m-%dT%H:%M') if d.admit_time else ''},
        {"label": "Numéro de séquence", "name": "dossier_seq", "type": "number", "value": d.dossier_seq},
        {"label": "Type de rencontre", "name": "encounter_type", "type": "text", "value": getattr(d, "encounter_type", None)},
        {"label": "Priorité", "name": "priority", "type": "text", "value": getattr(d, "priority", None)},
        {"label": "Raison", "name": "reason", "type": "text", "value": getattr(d, "reason", None)},
        {"label": "Disposition de sortie", "name": "discharge_disposition", "type": "text", "value": getattr(d, "discharge_disposition", None)},
    ]
    return templates.TemplateResponse(request, "form.html", {"request": request, "title": "Modifier dossier", "fields": fields, "action_url": f"/dossiers/{dossier_id}/edit"})


@router.post("/{dossier_id}/edit")
def update_dossier(
    dossier_id: int,
    patient_id: int = Form(...),
    uf_medicale: str = Form(None),
    uf_hebergement: str = Form(None),
    uf_soins: str = Form(None),
    admission_type: str = Form(None),
    admission_source: str = Form(None),
    attending_provider: str = Form(None),
    admit_time: str = Form(...),
    dossier_seq: int = Form(...),
    session=Depends(get_session),
    request: Request = None,
):
    d = session.get(Dossier, dossier_id)
    if not d:
        return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Dossier introuvable"}, status_code=404)
    d.patient_id = patient_id
    d.uf_medicale = uf_medicale if uf_medicale else None
    d.uf_hebergement = uf_hebergement if uf_hebergement else None
    d.uf_soins = uf_soins if uf_soins else None
    d.admission_type = admission_type
    d.admission_source = admission_source
    d.attending_provider = attending_provider
    d.admit_time = datetime.fromisoformat(admit_time)
    d.dossier_seq = dossier_seq
    session.add(d); session.commit()
    emit_to_senders(d, "dossier", session)
    return RedirectResponse(url="/dossiers", status_code=303)


@router.post("/{dossier_id}/replay")
async def replay_dossier_scenario(
    dossier_id: int,
    request: Request,
    scenario_id: int = Form(...),
    endpoint_ids: List[str] = Form(...),
    session=Depends(get_session),
):
    dossier = session.get(Dossier, dossier_id)
    if not dossier:
        return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Dossier introuvable"}, status_code=404)

    if not endpoint_ids:
        flash(request, "Veuillez sélectionner au moins un endpoint expéditeur.", level="error")
        return RedirectResponse(url=f"/dossiers/{dossier_id}", status_code=303)

    scenario = session.get(InteropScenario, scenario_id)
    if not scenario:
        flash(request, "Scénario introuvable pour ce dossier.", level="error")
        return RedirectResponse(url=f"/dossiers/{dossier_id}", status_code=303)

    try:
        endpoint_ids_int = [int(eid) for eid in endpoint_ids]
    except ValueError:
        flash(request, "Identifiants d'endpoint invalides.", level="error")
        return RedirectResponse(url=f"/dossiers/{dossier_id}", status_code=303)

    endpoints = session.exec(
        select(SystemEndpoint)
        .where(SystemEndpoint.id.in_(endpoint_ids_int))
        .where(SystemEndpoint.role.in_(["sender", "both"]))
    ).all()

    if not endpoints:
        flash(request, "Aucun endpoint valide sélectionné.", level="error")
        return RedirectResponse(url=f"/dossiers/{dossier_id}", status_code=303)

    summary_lines = []
    for endpoint in endpoints:
        try:
            logs = await send_scenario(session, scenario, endpoint)
        except Exception as exc:
            flash(request, f"{endpoint.name}: {exc}", level="error")
            continue
        sent = sum(1 for log in logs if log.status == "sent")
        skipped = sum(1 for log in logs if log.status == "skipped")
        errors = [log for log in logs if log.status not in {"sent", "skipped"}]
        line = f"{endpoint.name}: {sent} envoyés"
        if skipped:
            line += f", {skipped} ignorés"
        if errors:
            line += f", {len(errors)} erreurs"
        summary_lines.append(line)

    if not summary_lines:
        return RedirectResponse(url=f"/dossiers/{dossier_id}", status_code=303)
    flash(
        request,
        "Relecture du scénario terminée. " + " ; ".join(summary_lines),
        level="success",
    )
    return RedirectResponse(url=f"/dossiers/{dossier_id}", status_code=303)


@router.post("/{dossier_id}/delete")
def delete_dossier(dossier_id: int, request: Request, session=Depends(get_session)):
    d = session.get(Dossier, dossier_id)
    if not d:
        return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Dossier introuvable"}, status_code=404)
    session.delete(d); session.commit()
    emit_to_senders(d, "dossier", session)
    return RedirectResponse(url="/dossiers", status_code=303)
