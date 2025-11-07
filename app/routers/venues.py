from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from datetime import datetime
from app.db import get_session, get_next_sequence, peek_next_sequence
from app.models import Venue, Dossier
from app.services.emit_on_create import emit_to_senders
from app.dependencies.ght import require_ght_context

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(
    prefix="/venues",
    tags=["venues"],
    dependencies=[Depends(require_ght_context)],
)

@router.get("", response_class=HTMLResponse)
def list_venues(
    request: Request,
    dossier_id: int | None = Query(None, description="ID du dossier dont on veut voir les venues"),
    patient_id: int | None = Query(None, description="ID du patient pour filtrer les venues par tous ses dossiers"),
    session=Depends(get_session)
):
    venues = []
    dossier = None
    patient = None
    if dossier_id:
        dossier = session.get(Dossier, dossier_id)
        if not dossier:
            return templates.TemplateResponse(
                request,
                "error.html",
                {
                    "request": request,
                    "title": "Dossier introuvable",
                    "message": "Le dossier spécifié n'existe pas. Veuillez sélectionner un dossier valide.",
                    "back_url": "/dossiers"
                },
                status_code=404
            )
        session.refresh(dossier, ['patient'])
        venues = session.exec(select(Venue).where(Venue.dossier_id == dossier_id)).all()
        patient = dossier.patient if hasattr(dossier, 'patient') else None
    elif patient_id:
        from app.models import Patient
        patient = session.get(Patient, patient_id)
        if not patient:
            return templates.TemplateResponse(
                request,
                "error.html",
                {
                    "request": request,
                    "title": "Patient introuvable",
                    "message": "Le patient spécifié n'existe pas.",
                    "back_url": "/patients"
                },
                status_code=404
            )
        # Récupérer tous les dossiers du patient et leurs venues
        dossiers = getattr(patient, 'dossiers', [])
        for d in dossiers:
            venues.extend(session.exec(select(Venue).where(Venue.dossier_id == d.id)).all())
    else:
        venues = session.exec(select(Venue)).all()

    rows = [
        {
            "cells": [
                v.venue_seq,
                v.id,
                v.dossier_id,
                v.uf_medicale,
                v.uf_hebergement,
                v.uf_soins,
                getattr(v, 'hospital_service', None),
                v.start_time.strftime("%d/%m/%Y %H:%M") if v.start_time else None,
                v.code,
                v.label
            ],
            "detail_url": f"/venues/{v.id}",
            "edit_url": f"/venues/{v.id}/edit",
            "delete_url": f"/venues/{v.id}/delete"
        }
        for v in venues
    ]

    breadcrumbs = [{"label": "Venues", "url": "/venues"}]
    if dossier_id and dossier:
        breadcrumbs.insert(0, {"label": f"Dossier #{dossier.dossier_seq}", "url": f"/dossiers/{dossier_id}"})
        if dossier.patient:
            breadcrumbs.insert(0, {
                "label": f"Patient: {dossier.patient.family} {dossier.patient.given}",
                "url": f"/patients/{dossier.patient.id}"
            })
    elif patient_id and patient:
        breadcrumbs.insert(0, {
            "label": f"Patient: {patient.family} {patient.given}",
            "url": f"/patients/{patient.id}"
        })

    filters = [
        {
            "label": "UF responsabilité",
            "name": "uf",
            "type": "text",
            "placeholder": "Filtrer par UF"
        },
        {
            "label": "Service",
            "name": "service",
            "type": "select",
            "placeholder": "Tous les services",
            "options": [
                {"value": "cardiology", "label": "Cardiologie"},
                {"value": "neurology", "label": "Neurologie"},
                {"value": "oncology", "label": "Oncologie"},
                {"value": "pediatrics", "label": "Pédiatrie"},
                {"value": "other", "label": "Autre"}
            ]
        },
        {
            "label": "Local",
            "name": "location",
            "type": "text",
            "placeholder": "Filtrer par local"
        }
    ]

    # Définir les actions disponibles
    actions = [
        {
            "type": "link",
            "label": "Export FHIR",
            "url": "/venues/export/fhir"
        },
        {
            "type": "link",
            "label": "Export HL7",
            "url": "/venues/export/hl7"
        }
    ]

    # Construire le contexte complet
    ctx = {
        "request": request,
        "title": "Venues" if not dossier_id else f"Venues du dossier #{dossier.dossier_seq}",
        "breadcrumbs": breadcrumbs,
        "headers": ["Seq", "ID", "Dossier", "UF Méd.", "UF Héb.", "UF Soins", "Service", "Début", "Code", "Libellé"],
        "rows": rows,
        "context": {"dossier_id": dossier_id},
        "new_url": f"/venues/new?dossier_id={dossier_id}",
        "filters": filters,
        "actions": actions,
        "show_actions": True
    }

    return templates.TemplateResponse(request, "list.html", ctx)

@router.get("/new", response_class=HTMLResponse)
def new_venue(
    request: Request, 
    dossier_id: int | None = Query(None, description="ID du dossier parent (pré-rempli si fourni)"),
    session=Depends(get_session)
):
    next_seq = peek_next_sequence(session, "venue")
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
    
    # Si dossier_id fourni en query param, pré-remplir le champ
    # Sinon, tenter de récupérer depuis le contexte
    prefill_dossier_id = dossier_id
    if prefill_dossier_id is None and hasattr(request.state, 'dossier_context') and request.state.dossier_context:
        prefill_dossier_id = request.state.dossier_context.id
    
    # Si toujours None, on ne peut pas créer de venue sans dossier
    if prefill_dossier_id is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Impossible de créer une venue : aucun dossier n'est spécifié.")
    
    fields = [
        {"label": "Dossier ID", "name": "dossier_id", "type": "number", "required": True,
         "value": prefill_dossier_id or '',
         "help": "ID du dossier existant dans la base"},
        {"label": "UF médicale", "name": "uf_medicale", "type": "text", "required": False,
         "help": "Unité fonctionnelle de responsabilité médicale"},
        {"label": "UF hébergement", "name": "uf_hebergement", "type": "text", "required": False,
         "help": "Unité fonctionnelle de responsabilité d'hébergement"},
        {"label": "UF soins", "name": "uf_soins", "type": "text", "required": False,
         "help": "Unité fonctionnelle de responsabilité de soins"},
        {"label": "Début de venue", "name": "start_time", "type": "datetime-local", 
         "value": now_str, "required": True,
         "help": "Date et heure de début de la venue"},
        {"label": "Service hospitalier", "name": "hospital_service", "type": "select",
         "options": ["cardiology", "neurology", "oncology", "pediatrics", "other"],
         "help": "Service médical responsable"},
        {"label": "Local assigné", "name": "assigned_location", "type": "text",
         "help": "Localisation physique du patient"},
        {"label": "Médecin responsable", "name": "attending_provider", "type": "text",
         "help": "Médecin responsable de la venue"},
        {"label": "Lit", "name": "bed", "type": "text",
         "help": "Numéro ou identifiant du lit"},
        {"label": "Chambre", "name": "room", "type": "text",
         "help": "Numéro ou identifiant de la chambre"},
        {"label": "Code", "name": "code", "type": "text",
         "help": "Code optionnel de la venue"},
        {"label": "Libellé", "name": "label", "type": "text",
         "help": "Description libre de la venue"},
        {"label": "Numéro de séquence", "name": "venue_seq", "type": "number", 
         "value": next_seq,
         "help": "Généré automatiquement si non renseigné"},
        {"label": "Département gestionnaire", "name": "managing_department", "type": "text",
         "help": "Département administratif responsable"},
        {"label": "Type physique", "name": "physical_type", "type": "text",
         "help": "Nature du lieu physique (chambre, box, etc.)"},
        {"label": "Statut opérationnel", "name": "operational_status", "type": "select",
         "options": ["active", "suspended", "inactive"],
         "help": "État opérationnel de la venue"},
    ]
    return templates.TemplateResponse(request, "form.html", {"request": request, "title": "Nouvelle venue", "fields": fields})


@router.post("/new")
def create_venue(
    dossier_id: int = Form(...),
    uf_medicale: str = Form(None),
    uf_hebergement: str = Form(None),
    uf_soins: str = Form(None),
    start_time: str = Form(...),
    hospital_service: str = Form(None),
    assigned_location: str = Form(None),
    attending_provider: str = Form(None),
    bed: str = Form(None),
    room: str = Form(None),
    code: str = Form(None),
    label: str = Form(None),
    venue_seq: int | None = Form(None),
    managing_department: str = Form(None),
    physical_type: str = Form(None),
    operational_status: str = Form(None),
    session=Depends(get_session)
):
    start_dt = datetime.fromisoformat(start_time)
    seq = venue_seq or get_next_sequence(session, "venue")
    v = Venue(
        dossier_id=dossier_id,
        uf_medicale=uf_medicale if uf_medicale else None,
        uf_hebergement=uf_hebergement if uf_hebergement else None,
        uf_soins=uf_soins if uf_soins else None,
        start_time=start_dt,
        hospital_service=hospital_service,
        assigned_location=assigned_location,
        attending_provider=attending_provider,
        bed=bed,
        room=room,
        code=code,
        label=label,
        venue_seq=seq,
        managing_department=managing_department,
        physical_type=physical_type,
        operational_status=operational_status,
    )
    session.add(v); session.commit()
    emit_to_senders(v, "venue", session)
    return RedirectResponse(url="/venues", status_code=303)

@router.get("/{venue_id}", response_class=HTMLResponse)
def get_venue(venue_id: int, request: Request, session=Depends(get_session)):
    from app.models import Mouvement, Patient
    from sqlmodel import select
    
    v = session.get(Venue, venue_id)
    if not v:
        return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Venue introuvable"}, status_code=404)
    
    # Charger le dossier et le patient pour le contexte
    dossier = session.get(Dossier, v.dossier_id) if v.dossier_id else None
    patient = session.get(Patient, dossier.patient_id) if dossier and dossier.patient_id else None
    
    # Récupérer tous les mouvements de cette venue triés par date
    mouvements = session.exec(
        select(Mouvement)
        .where(Mouvement.venue_id == venue_id)
        .order_by(Mouvement.when)
    ).all()
    
    # Construire la timeline des responsabilités
    timeline = []
    for m in mouvements:
        timeline_item = {
            "when": m.when,
            "trigger": m.trigger_event or "?",
            "movement_type": m.movement_type,
            "nature": m.movement_nature or "",
            "uf_medicale": m.uf_medicale,
            "uf_hebergement": m.uf_hebergement,
            "uf_soins": m.uf_soins,
            "location": m.location,
        }
        timeline.append(timeline_item)
    
    return templates.TemplateResponse(request, "venue_detail.html", {
        "request": request,
        "venue": v,
        "dossier": dossier,
        "patient": patient,
        "timeline": timeline,
    })


@router.get("/{venue_id}/edit", response_class=HTMLResponse)
def edit_venue(venue_id: int, request: Request, session=Depends(get_session)):
    v = session.get(Venue, venue_id)
    if not v:
            return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Venue introuvable"}, status_code=404)
    fields = [
    {"label": "Dossier ID", "name": "dossier_id", "type": "number", "value": v.dossier_id, "required": True,
     "help": "ID du dossier existant dans la base"},
    {"label": "UF médicale", "name": "uf_medicale", "type": "text", "value": v.uf_medicale, "required": False,
     "help": "Unité fonctionnelle de responsabilité médicale"},
    {"label": "UF hébergement", "name": "uf_hebergement", "type": "text", "value": v.uf_hebergement, "required": False,
     "help": "Unité fonctionnelle de responsabilité d'hébergement"},
    {"label": "UF soins", "name": "uf_soins", "type": "text", "value": v.uf_soins, "required": False,
     "help": "Unité fonctionnelle de responsabilité de soins"},
    {"label": "Début de venue", "name": "start_time", "type": "datetime-local", 
     "value": v.start_time.strftime('%Y-%m-%dT%H:%M') if v.start_time else '', "required": True,
     "help": "Date et heure de début de la venue"},
        {"label": "Service hospitalier", "name": "hospital_service", "type": "select", 
         "options": ["cardiology", "neurology", "oncology", "pediatrics", "other"], 
         "value": getattr(v,'hospital_service',None),
         "help": "Service médical responsable"},
        {"label": "Local assigné", "name": "assigned_location", "type": "text", 
         "value": getattr(v,'assigned_location',None),
         "help": "Localisation physique du patient"},
        {"label": "Médecin responsable", "name": "attending_provider", "type": "text", 
         "value": getattr(v,'attending_provider',None),
         "help": "Médecin responsable de la venue"},
        {"label": "Lit", "name": "bed", "type": "text", 
         "value": getattr(v,'bed',None),
         "help": "Numéro ou identifiant du lit"},
        {"label": "Chambre", "name": "room", "type": "text", 
         "value": getattr(v,'room',None),
         "help": "Numéro ou identifiant de la chambre"},
        {"label": "Code", "name": "code", "type": "text", 
         "value": v.code,
         "help": "Code optionnel de la venue"},
        {"label": "Libellé", "name": "label", "type": "text", 
         "value": v.label,
         "help": "Description libre de la venue"},
        {"label": "Numéro de séquence", "name": "venue_seq", "type": "number", 
         "value": v.venue_seq,
         "help": "Numéro de séquence unique de la venue"},
        {"label": "Département gestionnaire", "name": "managing_department", "type": "text", "value": getattr(v, "managing_department", None)},
        {"label": "Type physique", "name": "physical_type", "type": "text", "value": getattr(v, "physical_type", None)},
        {"label": "Statut opérationnel", "name": "operational_status", "type": "text", "value": getattr(v, "operational_status", None)},
    ]
    return templates.TemplateResponse(request, "form.html", {"request": request, "title": "Modifier venue", "fields": fields, "action_url": f"/venues/{venue_id}/edit"})


@router.post("/{venue_id}/edit")
def update_venue(
    venue_id: int,
    dossier_id: int = Form(...),
    uf_medicale: str = Form(None),
    uf_hebergement: str = Form(None),
    uf_soins: str = Form(None),
    start_time: str = Form(...),
    hospital_service: str = Form(None),
    assigned_location: str = Form(None),
    attending_provider: str = Form(None),
    bed: str = Form(None),
    room: str = Form(None),
    code: str = Form(None),
    label: str = Form(None),
    venue_seq: int = Form(...),
    managing_department: str = Form(None),
    physical_type: str = Form(None),
    operational_status: str = Form(None),
    session=Depends(get_session),
    request: Request = None
):
    v = session.get(Venue, venue_id)
    if not v:
        return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Venue introuvable"}, status_code=404)
    v.dossier_id = dossier_id
    v.uf_medicale = uf_medicale if uf_medicale else None
    v.uf_hebergement = uf_hebergement if uf_hebergement else None
    v.uf_soins = uf_soins if uf_soins else None
    v.start_time = datetime.fromisoformat(start_time)
    v.hospital_service = hospital_service
    v.assigned_location = assigned_location
    v.attending_provider = attending_provider
    v.bed = bed
    v.room = room
    v.code = code
    v.label = label
    v.venue_seq = venue_seq
    v.managing_department = managing_department
    v.physical_type = physical_type
    v.operational_status = operational_status
    session.add(v); session.commit()
    emit_to_senders(v, "venue", session)
    return RedirectResponse(url="/venues", status_code=303)


@router.post("/{venue_id}/delete")
def delete_venue(venue_id: int, request: Request, session=Depends(get_session)):
    v = session.get(Venue, venue_id)
    if not v:
        return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Venue introuvable"}, status_code=404)
    dossier_id = v.dossier_id  # Capture l'ID du dossier avant de supprimer
    session.delete(v); session.commit()
    emit_to_senders(v, "venue", session)
    return RedirectResponse(url=f"/venues?dossier_id={dossier_id}", status_code=303)

