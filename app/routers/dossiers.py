from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from datetime import datetime
from app.db import get_session, get_next_sequence, peek_next_sequence
from app.models import Dossier, Patient

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/dossiers", tags=["dossiers"])

@router.get("", response_class=HTMLResponse)
def list_dossiers(request: Request, patient_id: int | None = Query(None), session=Depends(get_session)):
    stmt = select(Dossier)
    if patient_id:
        stmt = stmt.where(Dossier.patient_id == patient_id)
    dossiers = session.exec(stmt).all()
    rows = [
        {"cells": [d.dossier_seq, d.id, d.patient_id, d.uf_responsabilite, d.admit_time, d.discharge_time],
         "detail_url": f"/dossiers/{d.id}"}
        for d in dossiers
    ]
    ctx = {"request": request, "title": "Dossiers",
           "headers": ["Seq", "ID", "Patient", "UF resp.", "Admission", "Sortie"],
           "rows": rows, "new_url": "/dossiers/new"}
    return templates.TemplateResponse("list.html", ctx)

@router.get("/new", response_class=HTMLResponse)
def new_dossier(request: Request, session=Depends(get_session)):
    next_seq = peek_next_sequence(session, "dossier")
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")  # valeur par défaut = maintenant
    fields = [
        {"label": "Patient ID", "name": "patient_id", "type": "number"},
        {"label": "UF de responsabilité", "name": "uf_responsabilite", "type": "text"},
        {"label": "Date d’admission", "name": "admit_time", "type": "datetime-local", "value": now_str},
        {"label": "Numéro de séquence", "name": "dossier_seq", "type": "number", "value": next_seq},
    ]
    return templates.TemplateResponse("form.html", {"request": request, "title": "Nouveau dossier", "fields": fields})

@router.post("/new")
def create_dossier(
    patient_id: int = Form(...),
    uf_responsabilite: str = Form(...),
    admit_time: str = Form(...),
    dossier_seq: int | None = Form(None),
    session=Depends(get_session),
):
    admit_dt = datetime.fromisoformat(admit_time)
    seq = dossier_seq or get_next_sequence(session, "dossier")
    d = Dossier(
        patient_id=patient_id,
        uf_responsabilite=uf_responsabilite,
        admit_time=admit_dt,
        dossier_seq=seq,
    )
    session.add(d); session.commit()
    return RedirectResponse(url="/dossiers", status_code=303)

@router.get("/{dossier_id}", response_class=HTMLResponse)
def dossier_detail(dossier_id: int, request: Request, session=Depends(get_session)):
    d = session.get(Dossier, dossier_id)
    session.refresh(d, attribute_names=["patient", "venues"])
    for v in d.venues:
        session.refresh(v, attribute_names=["mouvements"])
    return templates.TemplateResponse("dossier_detail.html", {"request": request, "dossier": d})
