from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from datetime import datetime
from app.db import get_session, get_next_sequence, peek_next_sequence
from app.models import Dossier, Patient
from app.services.emit_on_create import emit_to_senders

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/dossiers", tags=["dossiers"])

@router.get("", response_class=HTMLResponse)
def list_dossiers(request: Request, patient_id: int | None = Query(None), session=Depends(get_session)):
    stmt = select(Dossier)
    if patient_id:
        stmt = stmt.where(Dossier.patient_id == patient_id)
    dossiers = session.exec(stmt).all()
    rows = [
        {"cells": [d.dossier_seq, d.id, d.patient_id, d.uf_responsabilite, getattr(d,'admission_type',None), d.admit_time, d.discharge_time],
         "detail_url": f"/dossiers/{d.id}"}
        for d in dossiers
    ]
    ctx = {"request": request, "title": "Dossiers",
           "headers": ["Seq", "ID", "Patient", "UF resp.", "Adm.type", "Admission", "Sortie"],
           "rows": rows, "new_url": "/dossiers/new"}
    return templates.TemplateResponse("list.html", ctx)

@router.get("/new", response_class=HTMLResponse)
def new_dossier(request: Request, session=Depends(get_session)):
    next_seq = peek_next_sequence(session, "dossier")
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")  # valeur par défaut = maintenant
    fields = [
        {"label": "Patient ID", "name": "patient_id", "type": "number"},
        {"label": "UF de responsabilité", "name": "uf_responsabilite", "type": "text"},
        {"label": "Type d'admission", "name": "admission_type", "type": "text"},
        {"label": "Source admission", "name": "admit_source", "type": "text"},
        {"label": "Médecin responsable (attending)", "name": "attending_provider", "type": "text"},
        {"label": "Date d’admission", "name": "admit_time", "type": "datetime-local", "value": now_str},
        {"label": "Numéro de séquence", "name": "dossier_seq", "type": "number", "value": next_seq},
    ]
    return templates.TemplateResponse("form.html", {"request": request, "title": "Nouveau dossier", "fields": fields})

@router.post("/new")
def create_dossier(
    patient_id: int = Form(...),
    uf_responsabilite: str = Form(...),
    admission_type: str = Form(None),
    admit_source: str = Form(None),
    attending_provider: str = Form(None),
    admit_time: str = Form(...),
    dossier_seq: int | None = Form(None),
    session=Depends(get_session),
):
    admit_dt = datetime.fromisoformat(admit_time)
    seq = dossier_seq or get_next_sequence(session, "dossier")
    d = Dossier(
        patient_id=patient_id,
        uf_responsabilite=uf_responsabilite,
        admission_type=admission_type,
        admit_source=admit_source,
        attending_provider=attending_provider,
        admit_time=admit_dt,
        dossier_seq=seq,
    )
    session.add(d); session.commit()
    emit_to_senders(d, "dossier", session)
    return RedirectResponse(url="/dossiers", status_code=303)


@router.get("/{dossier_id}", response_class=HTMLResponse)
def dossier_detail(dossier_id: int, request: Request, session=Depends(get_session)):
    d = session.get(Dossier, dossier_id)
    if not d:
        return templates.TemplateResponse("not_found.html", {"request": request, "title": "Dossier introuvable"}, status_code=404)
    session.refresh(d, attribute_names=["patient", "venues"])
    for v in d.venues:
        session.refresh(v, attribute_names=["mouvements"])
    return templates.TemplateResponse("dossier_detail.html", {"request": request, "dossier": d})


@router.get("/{dossier_id}/edit", response_class=HTMLResponse)
def edit_dossier(dossier_id: int, request: Request, session=Depends(get_session)):
    d = session.get(Dossier, dossier_id)
    if not d:
        return templates.TemplateResponse("not_found.html", {"request": request, "title": "Dossier introuvable"}, status_code=404)
    fields = [
        {"label": "Patient ID", "name": "patient_id", "type": "number", "value": d.patient_id},
        {"label": "UF de responsabilité", "name": "uf_responsabilite", "type": "text", "value": d.uf_responsabilite},
        {"label": "Type d'admission", "name": "admission_type", "type": "select", "options": ["emergency", "elective", "newborn", "urgent", "other"], "value": getattr(d,'admission_type',None)},
        {"label": "Source admission", "name": "admit_source", "type": "text", "value": getattr(d,'admit_source',None)},
        {"label": "Médecin responsable (attending)", "name": "attending_provider", "type": "text", "value": getattr(d,'attending_provider',None)},
        {"label": "Date d’admission", "name": "admit_time", "type": "datetime-local", "value": d.admit_time.strftime('%Y-%m-%dT%H:%M') if d.admit_time else ''},
        {"label": "Numéro de séquence", "name": "dossier_seq", "type": "number", "value": d.dossier_seq},
        {"label": "Type de rencontre", "name": "encounter_type", "type": "text", "value": getattr(d, "encounter_type", None)},
        {"label": "Priorité", "name": "priority", "type": "text", "value": getattr(d, "priority", None)},
        {"label": "Raison", "name": "reason", "type": "text", "value": getattr(d, "reason", None)},
        {"label": "Source d'admission", "name": "admission_source", "type": "text", "value": getattr(d, "admission_source", None)},
        {"label": "Disposition de sortie", "name": "discharge_disposition", "type": "text", "value": getattr(d, "discharge_disposition", None)},
    ]
    return templates.TemplateResponse("form.html", {"request": request, "title": "Modifier dossier", "fields": fields, "action_url": f"/dossiers/{dossier_id}/edit"})


@router.post("/{dossier_id}/edit")
def update_dossier(
    dossier_id: int,
    patient_id: int = Form(...),
    uf_responsabilite: str = Form(...),
    admission_type: str = Form(None),
    admit_source: str = Form(None),
    attending_provider: str = Form(None),
    admit_time: str = Form(...),
    dossier_seq: int = Form(...),
    session=Depends(get_session),
):
    d = session.get(Dossier, dossier_id)
    if not d:
        return templates.TemplateResponse("not_found.html", {"request": {}, "title": "Dossier introuvable"}, status_code=404)
    d.patient_id = patient_id
    d.uf_responsabilite = uf_responsabilite
    d.admission_type = admission_type
    d.admit_source = admit_source
    d.attending_provider = attending_provider
    d.admit_time = datetime.fromisoformat(admit_time)
    d.dossier_seq = dossier_seq
    session.add(d); session.commit()
    emit_to_senders(d, "dossier", session)
    return RedirectResponse(url="/dossiers", status_code=303)


@router.post("/{dossier_id}/delete")
def delete_dossier(dossier_id: int, session=Depends(get_session)):
    d = session.get(Dossier, dossier_id)
    if not d:
        return templates.TemplateResponse("not_found.html", {"request": {}, "title": "Dossier introuvable"}, status_code=404)
    session.delete(d); session.commit()
    emit_to_senders(d, "dossier", session)
    return RedirectResponse(url="/dossiers", status_code=303)
