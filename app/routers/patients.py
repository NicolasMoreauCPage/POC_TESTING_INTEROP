# app/routers/patients.py
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from app.db import get_session, peek_next_sequence, get_next_sequence
from app.models import Patient

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/patients", tags=["patients"])

@router.get("", response_class=HTMLResponse)
def list_patients(request: Request, session=Depends(get_session)):
    patients = session.exec(select(Patient)).all()
    rows = [
        {
            "cells": [p.patient_seq, p.id, p.external_id, f"{p.family} {p.given}"],
            "detail_url": f"/dossiers?patient_id={p.id}",
        }
        for p in patients
    ]
    ctx = {
        "request": request,
        "title": "Patients",
        "headers": ["Seq", "ID", "ExtID", "Nom"],
        "rows": rows,
        "new_url": "/patients/new",
    }
    return templates.TemplateResponse("list.html", ctx)

@router.get("/new", response_class=HTMLResponse)
def new_patient(request: Request, session=Depends(get_session)):
    next_seq = peek_next_sequence(session, "patient")
    fields = [
        {"label": "Numéro de séquence (patient)", "name": "patient_seq", "type": "number", "value": next_seq},
        {"label": "External ID (SI source)", "name": "external_id", "type": "text"},
        {"label": "Nom", "name": "family", "type": "text"},
        {"label": "Prénom", "name": "given", "type": "text"},
        {"label": "Date de naissance", "name": "birth_date", "type": "date"},
        {"label": "Sexe (male|female|other|unknown)", "name": "gender", "type": "text"},
    ]
    return templates.TemplateResponse("form.html", {"request": request, "title": "Nouveau patient", "fields": fields})

@router.post("/new")
def create_patient(
    patient_seq: int | None = Form(None),
    external_id: str = Form(...),
    family: str = Form(...),
    given: str = Form(...),
    birth_date: str = Form(None),
    gender: str = Form(None),
    session=Depends(get_session),
):
    seq = patient_seq or get_next_sequence(session, "patient")
    p = Patient(
        patient_seq=seq,
        external_id=external_id,
        family=family,
        given=given,
        birth_date=birth_date,
        gender=gender,
    )
    session.add(p)
    session.commit()
    return RedirectResponse(url="/patients", status_code=303)
