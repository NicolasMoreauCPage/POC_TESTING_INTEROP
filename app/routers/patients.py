"""
Routes Patients (UI HTML)

Ce routeur expose les écrans de liste, création, édition et suppression de
patients. Il s'appuie sur des templates Jinja et sur une dépendance
`require_ght_context` pour s'assurer qu'un contexte GHT est actif.

Principes clés
- Toutes les vues rendent des pages HTML (pas d'API JSON ici).
- Les formulaires utilisent un template générique `form.html` avec une
    description des champs (label, type, options, etc.).
- Les événements d'enregistrement déclenchent `emit_to_senders` pour publier
    vers les transports configurés (HL7/FHIR sortants si activés).
"""
import random
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Request
from sqlmodel import select
from app.db import get_session, peek_next_sequence, get_next_sequence
from app.models import Patient
from app.services.emit_on_create import emit_to_senders
from app.dependencies.ght import require_ght_context


def get_templates(request: Request):
    # Récupère l'instance de templates enrichie (avec filtres globaux)
    return request.app.state.templates


def generate_sample_patient_data():
    """Génère des données de patient réalistes pour pré-remplir le formulaire."""
    # Listes de noms et prénoms français
    family_names = [
        "MARTIN", "BERNARD", "DUBOIS", "THOMAS", "ROBERT", "RICHARD", "PETIT", "DURAND",
        "LEROY", "MOREAU", "SIMON", "LAURENT", "LEFEBVRE", "MICHEL", "GARCIA", "DAVID",
        "BERTRAND", "ROUX", "VINCENT", "FOURNIER", "MOREL", "GIRARD", "ANDRE", "MERCIER"
    ]
    
    given_names_m = [
        "Jean", "Pierre", "Michel", "André", "Philippe", "Alain", "Jacques", "Bernard",
        "François", "Claude", "Louis", "Paul", "Nicolas", "Julien", "Thomas", "Alexandre"
    ]
    
    given_names_f = [
        "Marie", "Nathalie", "Isabelle", "Sylvie", "Catherine", "Françoise", "Sophie",
        "Monique", "Martine", "Christine", "Jacqueline", "Annie", "Claire", "Emma", "Julie"
    ]
    
    middle_names = ["Marie", "Jean", "Paul", "Pierre", "Anne", "Louis", "René", "Claude"]
    
    cities = [
        "Paris", "Lyon", "Marseille", "Toulouse", "Nice", "Nantes", "Strasbourg",
        "Montpellier", "Bordeaux", "Lille", "Rennes", "Reims", "Le Havre", "Saint-Étienne"
    ]
    
    streets = [
        "Rue de la République", "Avenue des Champs", "Boulevard Victor Hugo",
        "Rue du Commerce", "Place de la Liberté", "Rue Jean Jaurès", "Avenue de la Paix",
        "Rue Pasteur", "Boulevard Gambetta", "Rue Voltaire"
    ]
    
    # Génération aléatoire
    gender = random.choice(["M", "F", "U"])
    
    if gender == "M":
        given = random.choice(given_names_m)
        prefix = "M."
    elif gender == "F":
        given = random.choice(given_names_f)
        prefix = random.choice(["Mme", "Mlle"])
    else:
        given = random.choice(given_names_m + given_names_f)
        prefix = ""
    
    family = random.choice(family_names)
    middle = random.choice([None, None, random.choice(middle_names)])  # 33% chance
    
    # Date de naissance (entre 18 et 95 ans)
    age_days = random.randint(18*365, 95*365)
    birth_date = (datetime.now() - timedelta(days=age_days)).strftime("%Y-%m-%d")
    
    # Adresse
    street_number = random.randint(1, 200)
    street = random.choice(streets)
    city = random.choice(cities)
    postal_code = f"{random.randint(1, 95):05d}"
    
    # Téléphone
    phone = f"0{random.randint(1, 5)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)}"
    mobile = f"0{random.randint(6, 7)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)}"
    
    # Email
    email = f"{given.lower()}.{family.lower()}@example.fr"
    
    # NIR (fake mais format valide)
    gender_code = "1" if gender == "M" else "2"
    year = birth_date[2:4]
    month = birth_date[5:7]
    dept = f"{random.randint(1, 95):02d}"
    commune = f"{random.randint(1, 999):03d}"
    ordre = f"{random.randint(1, 999):03d}"
    nir = f"{gender_code} {year} {month} {dept} {commune} {ordre}"
    
    # Statut marital
    marital_status = random.choice(["S", "M", "D", "W", ""])
    
    return {
        "prefix": prefix,
        "family": family,
        "given": given,
        "middle": middle or "",
        "birth_date": birth_date,
        "gender": gender,
        "address": f"{street_number} {street}",
        "city": city,
        "postal_code": postal_code,
        "country": "FRA",
        "phone": phone,
        "mobile": mobile,
        "email": email,
        "nir": nir,
        "marital_status": marital_status,
        "nationality": "FRA"
    }


router = APIRouter(
    prefix="/patients",
    tags=["patients"],
    dependencies=[Depends(require_ght_context)],
)

@router.get("", response_class=HTMLResponse)
def list_patients(request: Request, session=Depends(get_session)):
    """Liste paginée des patients (vue HTML).

    - Récupère les patients et prépare des lignes pour le composant `list.html`.
    - Définit breadcrumbs, filtres et actions complémentaires.
    """
    patients = session.exec(select(Patient)).all()
    rows = [
        {
            "cells": [p.patient_seq, p.id, p.external_id, f"{p.family} {p.given}", p.birth_date, p.gender],
            "detail_url": f"/patients/{p.id}",
            "context_url": f"/context/patient/{p.id}",
            "edit_url": f"/patients/{p.id}/edit",
            "delete_url": f"/patients/{p.id}/delete"
        }
        for p in patients
    ]

    # Définir le fil d'Ariane
    breadcrumbs = [
        {"label": "Patients", "url": "/patients"}
    ]
    
    # Définir les filtres
    filters = [
        {
            "label": "Nom",
            "name": "name",
            "type": "text",
            "placeholder": "Rechercher par nom"
        },
        {
            "label": "Genre",
            "name": "gender",
            "type": "select",
            "placeholder": "Tous les genres",
            "options": [
                {"value": "male", "label": "Homme"},
                {"value": "female", "label": "Femme"},
                {"value": "other", "label": "Autre"},
                {"value": "unknown", "label": "Non spécifié"}
            ]
        }
    ]

    # Définir les actions supplémentaires
    actions = [
        {
            "type": "link",
            "label": "Export FHIR",
            "url": "/patients/export/fhir"
        },
        {
            "type": "link", 
            "label": "Import FHIR",
            "url": "/patients/import/fhir"
        }
    ]

    ctx = {
        "request": request,
        "title": "Patients",
        "breadcrumbs": breadcrumbs,
        "headers": ["Seq", "ID", "ExtID", "Nom", "Date naiss.", "Genre"],
        "rows": rows,
        "new_url": "/patients/new",
        "filters": filters,
        "actions": actions,
        "show_actions": True
    }
    
    templates = get_templates(request)
    return templates.TemplateResponse(request, "list.html", ctx)


@router.get("/{patient_id:int}", response_class=HTMLResponse)
def patient_detail(patient_id: int, request: Request, session=Depends(get_session)):
    """Affiche le détail d'un patient (lecture seule)."""
    p = session.get(Patient, patient_id)
    templates = get_templates(request)
    if not p:
        return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Patient introuvable"}, status_code=404)

    # Définir le contexte patient en session
    request.session["patient_id"] = p.id

    # Charger la hiérarchie dossiers > venues > mouvements
    dossiers = session.exec(select(type(p.dossiers[0])).where(type(p.dossiers[0]).patient_id == p.id)).all() if p.dossiers else []
    for dossier in dossiers:
        dossier.venues = session.exec(select(type(dossier.venues[0])).where(type(dossier.venues[0]).dossier_id == dossier.id)).all() if dossier.venues else []
        for venue in dossier.venues:
            venue.mouvements = session.exec(select(type(venue.mouvements[0])).where(type(venue.mouvements[0]).venue_id == venue.id)).all() if venue.mouvements else []

    return templates.TemplateResponse(request, "patient_detail.html", {
        "request": request,
        "patient": p,
        "dossiers": dossiers
    })


@router.get("/{patient_id:int}/edit", response_class=HTMLResponse)
def edit_patient(patient_id: int, request: Request, session=Depends(get_session)):
    """Affiche le formulaire d'édition d'un patient existant (conforme RGPD France)."""
    p = session.get(Patient, patient_id)
    templates = get_templates(request)
    if not p:
        return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Patient introuvable"}, status_code=404)
    
    return templates.TemplateResponse(request, "patient_form.html", {
        "request": request,
        "title": "Modifier patient",
        "patient": p,
        "action_url": f"/patients/{patient_id}/edit"
    })


@router.post("/{patient_id:int}/edit")
def update_patient(
    patient_id: int,
    patient_seq: int = Form(...),
    external_id: str = Form(None),
    family: str = Form(...),
    given: str = Form(...),
    birth_date: str = Form(None),
    gender: str = Form(None),
    middle: str = Form(None),
    prefix: str = Form(None),
    suffix: str = Form(None),
    birth_family: str = Form(None),
    address: str = Form(None),
    city: str = Form(None),
    state: str = Form(None),
    postal_code: str = Form(None),
    country: str = Form(None),
    phone: str = Form(None),
    mobile: str = Form(None),
    work_phone: str = Form(None),
    email: str = Form(None),
    birth_address: str = Form(None),
    birth_city: str = Form(None),
    birth_state: str = Form(None),
    birth_postal_code: str = Form(None),
    birth_country: str = Form(None),
    marital_status: str = Form(None),
    mothers_maiden_name: str = Form(None),
    primary_care_provider: str = Form(None),
    nir: str = Form(None),
    nationality: str = Form(None),
    identity_reliability_code: str = Form(None),
    session=Depends(get_session),
    request: Request = None,
):
    """Met à jour un patient existant (conforme RGPD - pas de race/religion)."""
    p = session.get(Patient, patient_id)
    if not p:
        templates = get_templates(request)
        if not p:
            return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Patient introuvable"}, status_code=404)
    # Mise à jour des champs - Identité
    p.patient_seq = patient_seq
    p.external_id = external_id or p.external_id
    p.family = family
    p.given = given
    p.middle = middle
    p.prefix = prefix
    p.suffix = suffix
    p.birth_family = birth_family
    p.birth_date = birth_date
    p.gender = gender
    
    # Coordonnées domicile
    p.address = address
    p.city = city
    p.state = state
    p.postal_code = postal_code
    p.country = country
    p.phone = phone
    p.mobile = mobile
    p.work_phone = work_phone
    p.email = email
    
    # Lieu de naissance
    p.birth_address = birth_address
    p.birth_city = birth_city
    p.birth_state = birth_state
    p.birth_postal_code = birth_postal_code
    p.birth_country = birth_country
    
    # Informations administratives
    p.marital_status = marital_status
    p.mothers_maiden_name = mothers_maiden_name
    p.primary_care_provider = primary_care_provider
    p.nir = nir
    p.nationality = nationality
    p.identity_reliability_code = identity_reliability_code
    
    # RGPD: on ne met PAS à jour race/religion/ssn/administrative_gender
    
    session.add(p)
    session.commit()
    # Note: L'émission automatique est gérée par entity_events.py (after_update listener)
    return RedirectResponse(url="/patients", status_code=303)


@router.post("/{patient_id:int}/delete")
def delete_patient(patient_id: int, request: Request, session=Depends(get_session)):
    """Supprime un patient et revient à la liste."""
    p = session.get(Patient, patient_id)
    templates = get_templates(request)
    if not p:
        return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Patient introuvable"}, status_code=404)
    session.delete(p)
    session.commit()
    # Note: L'émission automatique pour les suppressions n'est pas encore implémentée
    return RedirectResponse(url="/patients", status_code=303)

@router.get("/new", response_class=HTMLResponse)
def new_patient_form(request: Request, session=Depends(get_session)):
    """Affiche le formulaire de création patient (conforme RGPD France)."""
    templates = get_templates(request)
    next_seq = peek_next_sequence(session, "patient")
    
    # Générer des données de démonstration pré-remplies
    sample_data = generate_sample_patient_data()
    
    return templates.TemplateResponse(request, "patient_form.html", {
        "request": request,
        "title": "Nouveau patient",
        "patient": None,
        "next_seq": next_seq,
        "action_url": "/patients/new",
        "sample_data": sample_data
    })

@router.post("/new")
async def create_patient(
    request: Request,
    patient_seq: int = Form(None),
    external_id: str = Form(None),
    family: str = Form(...),
    given: str = Form(...),
    middle: str = Form(None),
    prefix: str = Form(None),
    suffix: str = Form(None),
    birth_family: str = Form(None),
    birth_date: str = Form(None),
    gender: str = Form(None),
    address: str = Form(None),
    city: str = Form(None),
    state: str = Form(None),
    postal_code: str = Form(None),
    country: str = Form(None),
    phone: str = Form(None),
    mobile: str = Form(None),
    work_phone: str = Form(None),
    email: str = Form(None),
    birth_address: str = Form(None),
    birth_city: str = Form(None),
    birth_state: str = Form(None),
    birth_postal_code: str = Form(None),
    birth_country: str = Form(None),
    nir: str = Form(None),
    marital_status: str = Form(None),
    nationality: str = Form(None),
    identity_reliability_code: str = Form(None),
    mothers_maiden_name: str = Form(None),
    primary_care_provider: str = Form(None),
    session=Depends(get_session)
):
    """Crée un nouveau patient (conforme RGPD - pas de race/religion) et redirige."""
    is_ajax = request.headers.get('accept') == 'application/json'

    try:
        patient_seq = get_next_sequence(session, "patient") if patient_seq is None else patient_seq
        patient = Patient(
            patient_seq=patient_seq,
            external_id=external_id,
            family=family,
            given=given,
            middle=middle,
            prefix=prefix,
            suffix=suffix,
            birth_family=birth_family,
            birth_date=birth_date,
            gender=gender,
            address=address,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
            phone=phone,
            mobile=mobile,
            work_phone=work_phone,
            email=email,
            birth_address=birth_address,
            birth_city=birth_city,
            birth_state=birth_state,
            birth_postal_code=birth_postal_code,
            birth_country=birth_country,
            nir=nir,
            marital_status=marital_status,
            nationality=nationality,
            identity_reliability_code=identity_reliability_code,
            mothers_maiden_name=mothers_maiden_name,
            primary_care_provider=primary_care_provider
        )
        session.add(patient)
        session.commit()
        # Note: L'émission automatique est gérée par entity_events.py (after_insert listener)

        if is_ajax:
            return {"status": "success", "message": "Patient créé avec succès", "redirect": "/patients"}
        return RedirectResponse(url="/patients", status_code=303)

    except Exception as e:
        session.rollback()
        if is_ajax:
            return {"status": "error", "message": str(e)}
        # En cas d'erreur, retourner au formulaire avec les données
        return RedirectResponse(url="/patients/new", status_code=303)
