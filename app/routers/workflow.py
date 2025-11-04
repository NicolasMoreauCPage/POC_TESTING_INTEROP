from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from datetime import datetime

from app.db import get_session
from app.models import Dossier, Venue, Mouvement, DossierType
from app.utils.dossier_helpers import sync_dossier_class
from app.models_structure import (
    Lit, Chambre, UniteHebergement, UniteFonctionnelle, 
    Service, LocationStatus
)

from app.services.emit_on_create import emit_to_senders as emit_on_create
from app.state_transitions import SUPPORTED_WORKFLOW_EVENTS, WORKFLOW_GRAPH

router = APIRouter(prefix="/workflow", tags=["workflow"])
templates = Jinja2Templates(directory="app/templates")

def _collect_workflow_context(venue_id: int, session: Session) -> Dict[str, object]:
    # Récupérer la venue et son dossier
    venue = session.get(Venue, venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    
    dossier = session.get(Dossier, venue.dossier_id)
    
    # Récupérer tous les mouvements de la venue, ordonnés par date
    mouvements = session.exec(
        select(Mouvement)
        .where(Mouvement.venue_id == venue_id)
        .order_by(Mouvement.when)
    ).all()
    
    # Récupérer la structure disponible pour le sélecteur de localisation
    # On joint toute la hiérarchie pour avoir le chemin complet
    # Joins explicites pour éviter l'ambiguïté SQLAlchemy
    locations = session.exec(
        select(Lit, Chambre, UniteHebergement, UniteFonctionnelle, Service)
        .select_from(Lit)
        .join(Lit.chambre)
        .join(Chambre.unite_hebergement)
        .join(UniteHebergement.unite_fonctionnelle)
        .join(UniteFonctionnelle.service)
        .where(Lit.status == LocationStatus.ACTIVE)
    ).all()
    
    # Organiser les données par service/UF/etc
    structure_tree = {}
    for lit, chambre, uh, uf, service in locations:
        if service.id not in structure_tree:
            structure_tree[service.id] = {
                "id": service.id,
                "name": service.name,
                "service_type": service.service_type,
                "ufs": {}
            }
        
        if uf.id not in structure_tree[service.id]["ufs"]:
            structure_tree[service.id]["ufs"][uf.id] = {
                "id": uf.id,
                "name": uf.name,
                "unites_hebergement": {}
            }
            
        if uh.id not in structure_tree[service.id]["ufs"][uf.id]["unites_hebergement"]:
            structure_tree[service.id]["ufs"][uf.id]["unites_hebergement"][uh.id] = {
                "id": uh.id,
                "name": uh.name,
                "chambres": {}
            }
            
        if chambre.id not in structure_tree[service.id]["ufs"][uf.id]["unites_hebergement"][uh.id]["chambres"]:
            structure_tree[service.id]["ufs"][uf.id]["unites_hebergement"][uh.id]["chambres"][chambre.id] = {
                "id": chambre.id,
                "name": chambre.name,
                "lits": []
            }
            
        structure_tree[service.id]["ufs"][uf.id]["unites_hebergement"][uh.id]["chambres"][chambre.id]["lits"].append({
            "id": lit.id,
            "name": lit.name,
            "status": lit.status,
            "operationalStatus": getattr(lit, 'operational_status', None)
        })
    
    return {
        "venue": venue,
        "dossier": dossier,
        "mouvements": mouvements,
        "structure": structure_tree
    }


@router.get("/{venue_id}")
async def get_workflow(
    venue_id: int,
    session: Session = Depends(get_session)
):
    """Données JSON du workflow de mouvements pour une venue."""
    return _collect_workflow_context(venue_id, session)


@router.get("/venue/{venue_id}/view", response_class=HTMLResponse)
async def workflow_view(
    venue_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    from app.state_transitions import ALLOWED_TRANSITIONS, INITIAL_EVENTS
    
    data = _collect_workflow_context(venue_id, session)
    
    # Déterminer l'état actuel basé sur le dernier mouvement
    mouvements = data["mouvements"]
    if mouvements:
        last_event = mouvements[-1].type.split('^')[-1] if mouvements[-1].type else None
        allowed_events = ALLOWED_TRANSITIONS.get(last_event, set())
    else:
        # Pas de mouvements = état initial "no_current"
        # On évite d'exposer A38 (annulation de pré-admission) en IHM initiale
        allowed_events = {e for e in INITIAL_EVENTS if e != "A38"}
    
    # Filtrer les événements du catalogue pour ne garder que ceux autorisés
    filtered_catalog = {
        code: meta for code, meta in SUPPORTED_WORKFLOW_EVENTS.items()
        if code in allowed_events
    }
    
    return templates.TemplateResponse(
        "mouvement_workflow.html",
        {
            "request": request,
            **data,
            "graph": WORKFLOW_GRAPH,
            "event_catalog": filtered_catalog,
            "all_events": SUPPORTED_WORKFLOW_EVENTS,
        },
    )

@router.post("/{venue_id}/mouvement")
async def create_mouvement(
    venue_id: int,
    event_code: str = Form(...),
    location: str = Form(None),
    reason: str = Form(None),
    performer: str = Form(None),
    request: Request = None,
    session: Session = Depends(get_session)
):
    """Crée un nouveau mouvement dans le workflow"""
    
    venue = session.get(Venue, venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    event_code = (event_code or "").upper()
    event_mapping = {
        "A01": ("admission", True),
        "A02": ("transfer", True),
        "A03": ("discharge", False),
        "A04": ("consultation_out", False),
        "A05": ("preadmission", False),
        "A06": ("class_change", True),  # Location requise pour urgence->hospi
        "A07": ("from_consult", True),
        "A21": ("temporary_leave", False),
        "A22": ("return", True),
        "A38": ("cancel_preadmission", False),
    }

    if event_code not in event_mapping:
        raise HTTPException(status_code=400, detail=f"Unsupported event code {event_code}")

    movement_type, requires_location = event_mapping[event_code]

    if requires_location and not location:
        raise HTTPException(status_code=400, detail="Location is required for this movement")

    # Vérifier que l'événement est autorisé depuis l'état actuel
    from app.state_transitions import ALLOWED_TRANSITIONS, INITIAL_EVENTS
    last = session.exec(
        select(Mouvement)
        .where(Mouvement.venue_id == venue_id)
        .order_by(Mouvement.when)
    ).all()
    last_event = last[-1].type.split('^')[-1] if last else None
    allowed = (ALLOWED_TRANSITIONS.get(last_event, set()) if last_event else {e for e in INITIAL_EVENTS if e != "A38"})
    if event_code not in allowed:
        raise HTTPException(status_code=400, detail=f"Event {event_code} not allowed from current state")
        
    # Déterminer le type ADT en fonction du type de mouvement
    adt_type = f"ADT^{event_code}"
    
    # Créer le mouvement
    mouvement = Mouvement(
        venue_id=venue_id,
        type=adt_type,
        when=datetime.now(),
        location=location,
        reason=reason,
        performer=performer,
        movement_type=movement_type,
        movement_reason=reason,
    )
    
    # Pour les transferts, on garde trace du from_location
    previous_location = venue.assigned_location

    if event_code in {"A02", "A22"}:
        if previous_location:
            mouvement.from_location = previous_location
        if location:
            mouvement.to_location = location
            venue.assigned_location = location
    elif event_code == "A06":
        mouvement.from_location = previous_location
        # Si le patient vient des urgences, on le passe en hospitalisé
        if venue.dossier.dossier_type == DossierType.URGENCE:
            if not location:
                raise HTTPException(status_code=400, detail="Location required for emergency to inpatient transition")
            mouvement.to_location = location
            venue.assigned_location = location
            venue.dossier.dossier_type = DossierType.HOSPITALISE
            sync_dossier_class(venue.dossier)
        else:
            # Comportement standard : passage en externe
            mouvement.to_location = "Consultation"
            venue.assigned_location = mouvement.to_location
            venue.dossier.dossier_type = DossierType.EXTERNE
            sync_dossier_class(venue.dossier)
    elif event_code == "A07":
        if previous_location:
            mouvement.from_location = previous_location
        if location:
            mouvement.to_location = location
            venue.assigned_location = location
        # Changer le type de dossier en hospitalisé
        venue.dossier.dossier_type = DossierType.HOSPITALISE
        sync_dossier_class(venue.dossier)
    elif event_code == "A03":
        venue.assigned_location = None
    elif event_code == "A38":
        # Annulation de pré-admission: on revient à l'état sans venue courante
        venue.assigned_location = None
    elif event_code in {"A01", "A05"} and location:
        venue.assigned_location = location

    if location and event_code not in {"A06"}:
        mouvement.location = location

    session.add(venue)
    
    session.add(mouvement)
    await emit_on_create(mouvement, "mouvement", session)
    session.commit()
    
    # Rediriger vers la page du workflow avec message de succès
    return RedirectResponse(
        url=f"/workflow/venue/{venue_id}/view?success=1",
        status_code=303
    )
