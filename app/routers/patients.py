# app/routers/patients.py
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from app.db import get_session, peek_next_sequence, get_next_sequence
from app.models import Patient
from app.services.emit_on_create import emit_to_senders

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/patients", tags=["patients"])

@router.get("", response_class=HTMLResponse)
def list_patients(request: Request, session=Depends(get_session)):
    patients = session.exec(select(Patient)).all()
    rows = [
        {
            "cells": [p.patient_seq, p.id, p.external_id, f"{p.family} {p.given}"],
            "detail_url": f"/patients/{p.id}",
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


@router.get("/{patient_id:int}", response_class=HTMLResponse)
def patient_detail(patient_id: int, request: Request, session=Depends(get_session)):
    p = session.get(Patient, patient_id)
    if not p:
        return templates.TemplateResponse("not_found.html", {"request": request, "title": "Patient introuvable"}, status_code=404)
    return templates.TemplateResponse("patient_detail.html", {"request": request, "patient": p})


@router.get("/{patient_id:int}/edit", response_class=HTMLResponse)
def edit_patient(patient_id: int, request: Request, session=Depends(get_session)):
    p = session.get(Patient, patient_id)
    if not p:
        return templates.TemplateResponse("not_found.html", {"request": request, "title": "Patient introuvable"}, status_code=404)
    fields = [
        {"label": "Numéro de séquence (patient)", "name": "patient_seq", "type": "number", "value": p.patient_seq},
        {"label": "External ID (SI source)", "name": "external_id", "type": "text", "value": p.external_id},
        {"label": "Nom", "name": "family", "type": "text", "value": p.family},
        {"label": "Prénom", "name": "given", "type": "text", "value": p.given},
        {"label": "Date de naissance", "name": "birth_date", "type": "date", "value": p.birth_date},
        {"label": "Sexe (male|female|other|unknown)", "name": "gender", "type": "select", "options": ["male", "female", "other", "unknown"], "value": p.gender},
        {"label": "Deuxième prénom / middle", "name": "middle", "type": "text", "value": getattr(p, "middle", None)},
        {"label": "Préfixe (M./Mme)", "name": "prefix", "type": "text", "value": getattr(p, "prefix", None)},
        {"label": "Suffixe", "name": "suffix", "type": "text", "value": getattr(p, "suffix", None)},
        {"label": "Adresse (rue)", "name": "address", "type": "text", "value": getattr(p, "address", None)},
        {"label": "Ville", "name": "city", "type": "text", "value": getattr(p, "city", None)},
        {"label": "État/Région", "name": "state", "type": "text", "value": getattr(p, "state", None)},
        {"label": "Code postal", "name": "postal_code", "type": "text", "value": getattr(p, "postal_code", None)},
        {"label": "Téléphone", "name": "phone", "type": "text", "value": getattr(p, "phone", None)},
        {"label": "Email", "name": "email", "type": "text", "value": getattr(p, "email", None)},
        {"label": "N° sécurité sociale", "name": "ssn", "type": "text", "value": getattr(p, "ssn", None)},
        {"label": "Statut marital", "name": "marital_status", "type": "text", "value": getattr(p, "marital_status", None)},
        {"label": "Nom de jeune fille de la mère", "name": "mothers_maiden_name", "type": "text", "value": getattr(p, "mothers_maiden_name", None)},
        {"label": "Race", "name": "race", "type": "text", "value": getattr(p, "race", None)},
        {"label": "Religion", "name": "religion", "type": "text", "value": getattr(p, "religion", None)},
        {"label": "Médecin traitant / PCP", "name": "primary_care_provider", "type": "text", "value": getattr(p, "primary_care_provider", None)},
        {"label": "NIR (Numéro d'inscription au répertoire)", "name": "nir", "type": "text", "value": getattr(p, "nir", None)},
        {"label": "Nationalité", "name": "nationality", "type": "text", "value": getattr(p, "nationality", None)},
        {"label": "Lieu de naissance", "name": "place_of_birth", "type": "text", "value": getattr(p, "place_of_birth", None)},
        {"label": "Genre administratif", "name": "administrative_gender", "type": "select", "options": ["male", "female", "other", "unknown"], "value": getattr(p, "administrative_gender", None)},
    ]
    return templates.TemplateResponse("form.html", {"request": request, "title": "Modifier patient", "fields": fields, "action_url": f"/patients/{patient_id}/edit"})


@router.post("/{patient_id:int}/edit")
def update_patient(
    patient_id: int,
    patient_seq: int = Form(...),
    external_id: str = Form(...),
    family: str = Form(...),
    given: str = Form(...),
    birth_date: str = Form(None),
    gender: str = Form(None),
    middle: str = Form(None),
    prefix: str = Form(None),
    suffix: str = Form(None),
    address: str = Form(None),
    city: str = Form(None),
    state: str = Form(None),
    postal_code: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    ssn: str = Form(None),
    marital_status: str = Form(None),
    mothers_maiden_name: str = Form(None),
    race: str = Form(None),
    religion: str = Form(None),
    primary_care_provider: str = Form(None),
    nir: str = Form(None),
    nationality: str = Form(None),
    place_of_birth: str = Form(None),
    administrative_gender: str = Form(None),
    session=Depends(get_session),
):
    p = session.get(Patient, patient_id)
    if not p:
        return templates.TemplateResponse("not_found.html", {"request": {}, "title": "Patient introuvable"}, status_code=404)
    p.patient_seq = patient_seq
    p.external_id = external_id
    p.family = family
    p.given = given
    p.birth_date = birth_date
    p.gender = gender
    p.middle = middle
    p.prefix = prefix
    p.suffix = suffix
    p.address = address
    p.city = city
    p.state = state
    p.postal_code = postal_code
    p.phone = phone
    p.email = email
    p.ssn = ssn
    p.marital_status = marital_status
    p.mothers_maiden_name = mothers_maiden_name
    p.race = race
    p.religion = religion
    p.primary_care_provider = primary_care_provider
    p.nir = nir
    p.nationality = nationality
    p.place_of_birth = place_of_birth
    p.administrative_gender = administrative_gender
    session.add(p); session.commit()
    emit_to_senders(p, "patient", session)
    return RedirectResponse(url="/patients", status_code=303)


@router.post("/{patient_id:int}/delete")
def delete_patient(patient_id: int, session=Depends(get_session)):
    p = session.get(Patient, patient_id)
    if not p:
        return templates.TemplateResponse("not_found.html", {"request": {}, "title": "Patient introuvable"}, status_code=404)
    session.delete(p); session.commit()
    emit_to_senders(p, "patient", session)
    return RedirectResponse(url="/patients", status_code=303)

@router.get("/new", response_class=HTMLResponse)
def new_patient(request: Request, session=Depends(get_session)):
    next_seq = peek_next_sequence(session, "patient")
    fields = [
        {"label": "Numéro de séquence (patient)", "name": "patient_seq", "type": "number", "value": next_seq},
        {"label": "External ID (SI source)", "name": "external_id", "type": "text"},
        {"label": "Nom", "name": "family", "type": "text"},
        {"label": "Prénom", "name": "given", "type": "text"},
        {"label": "Date de naissance", "name": "birth_date", "type": "date"},
        {"label": "Sexe (male|female|other|unknown)", "name": "gender", "type": "select", "options": ["male", "female", "other", "unknown"]},
        {"label": "Deuxième prénom / middle", "name": "middle", "type": "text"},
        {"label": "Préfixe (M./Mme)", "name": "prefix", "type": "text"},
        {"label": "Suffixe", "name": "suffix", "type": "text"},
        {"label": "Adresse (rue)", "name": "address", "type": "text"},
        {"label": "Ville", "name": "city", "type": "text"},
        {"label": "État/Région", "name": "state", "type": "text"},
        {"label": "Code postal", "name": "postal_code", "type": "text"},
        {"label": "Téléphone", "name": "phone", "type": "text"},
        {"label": "Email", "name": "email", "type": "text"},
        {"label": "N° sécurité sociale", "name": "ssn", "type": "text"},
        {"label": "Statut marital", "name": "marital_status", "type": "text"},
        {"label": "Nom de jeune fille de la mère", "name": "mothers_maiden_name", "type": "text"},
        {"label": "Race", "name": "race", "type": "text"},
        {"label": "Religion", "name": "religion", "type": "text"},
        {"label": "Médecin traitant / PCP", "name": "primary_care_provider", "type": "text"},
        {"label": "NIR (Numéro d'inscription au répertoire)", "name": "nir", "type": "text"},
        {"label": "Nationalité", "name": "nationality", "type": "text"},
        {"label": "Lieu de naissance", "name": "place_of_birth", "type": "text"},
        {"label": "Genre administratif", "name": "administrative_gender", "type": "select", "options": ["male", "female", "other", "unknown"]},
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
    middle: str = Form(None),
    prefix: str = Form(None),
    suffix: str = Form(None),
    address: str = Form(None),
    city: str = Form(None),
    state: str = Form(None),
    postal_code: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    ssn: str = Form(None),
    marital_status: str = Form(None),
    mothers_maiden_name: str = Form(None),
    race: str = Form(None),
    religion: str = Form(None),
    primary_care_provider: str = Form(None),
    nir: str = Form(None),
    nationality: str = Form(None),
    place_of_birth: str = Form(None),
    administrative_gender: str = Form(None),
    session=Depends(get_session),
):
    seq = patient_seq or get_next_sequence(session, "patient")
    p = Patient(
        patient_seq=seq,
        external_id=external_id,
        family=family,
        given=given,
        middle=middle,
        prefix=prefix,
        suffix=suffix,
        birth_date=birth_date,
        gender=gender,
        address=address,
        city=city,
        state=state,
        postal_code=postal_code,
        phone=phone,
        email=email,
        ssn=ssn,
        marital_status=marital_status,
        mothers_maiden_name=mothers_maiden_name,
        race=race,
        religion=religion,
        primary_care_provider=primary_care_provider,
        nir=nir,
        nationality=nationality,
        place_of_birth=place_of_birth,
        administrative_gender=administrative_gender,
    )
    session.add(p)
    session.commit()
    emit_to_senders(p, "patient", session)
    return RedirectResponse(url="/patients", status_code=303)
