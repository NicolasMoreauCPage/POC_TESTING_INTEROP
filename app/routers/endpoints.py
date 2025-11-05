from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select, Session
from starlette import status
from datetime import datetime, timezone
import logging

from app.db import get_session

logger = logging.getLogger(__name__)
from app.models_endpoints import SystemEndpoint
from app.models_context import (
    EndpointContext, PatientContextMapping, DossierContextMapping,
    VenueContextMapping, MouvementContextMapping
)
from app.models_structure_fhir import GHTContext, EntiteJuridique
from app.runners import registry
from sqlmodel.sql.expression import select as sqlmodel_select
from sqlalchemy.orm import selectinload

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/endpoints", tags=["endpoints"])

def _bool_from_str(v: str | None, default: bool = False) -> bool:
    if v is None:
        return default
    return str(v).lower() in {"1","true","on","yes","y"}

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def list_endpoints(request: Request, session=Depends(get_session)):
    # Load endpoints with GHT context and EJ
    stmt = (
        sqlmodel_select(SystemEndpoint)
        .options(
            selectinload(SystemEndpoint.ght_context).selectinload(GHTContext.entites_juridiques),
            selectinload(SystemEndpoint.entite_juridique)
        )
    )
    eps = session.exec(stmt).unique().all()
    running_ids = set(registry.running_ids())
    
    # Group endpoints by GHT and EJ
    ght_groups = {}
    no_ght_endpoints = []
    
    for e in eps:
        if e.ght_context:
            ght_id = e.ght_context.id
            if ght_id not in ght_groups:
                ght_groups[ght_id] = {
                    "ght": e.ght_context,
                    "ej_groups": {},
                    "no_ej_endpoints": []
                }
            
            # Group by EJ if endpoint has one
            if e.entite_juridique:
                ej_id = e.entite_juridique.id
                if ej_id not in ght_groups[ght_id]["ej_groups"]:
                    ght_groups[ght_id]["ej_groups"][ej_id] = {
                        "ej": e.entite_juridique,
                        "endpoints": []
                    }
                ght_groups[ght_id]["ej_groups"][ej_id]["endpoints"].append(e)
            else:
                ght_groups[ght_id]["no_ej_endpoints"].append(e)
        else:
            no_ght_endpoints.append(e)
    
    def _make_endpoint_row(e):
        runtime = "RUNNING" if e.id in running_ids else "STOPPED"
        return {
            "cells": [e.id, e.name, e.kind, e.role, e.host or "-", e.port or "-", e.base_url or "-", "ON" if e.is_enabled else "OFF", runtime],
            "detail_url": f"/endpoints/{e.id}",
            "context_url": f"/endpoints/{e.id}/context"
        }
    
    # Build hierarchical structure for template
    hierarchy = []
    
    # GHT groups
    for ght_id in sorted(ght_groups.keys()):
        ght_data = ght_groups[ght_id]
        ght_children = []
        
        # EJ subgroups
        for ej_id in sorted(ght_data["ej_groups"].keys()):
            ej_info = ght_data["ej_groups"][ej_id]
            ej_endpoints = [_make_endpoint_row(e) for e in ej_info["endpoints"]]
            ght_children.append({
                "type": "ej",
                "ej": ej_info["ej"],
                "endpoints": ej_endpoints
            })
        
        # Endpoints without EJ in this GHT
        for e in ght_data["no_ej_endpoints"]:
            ght_children.append({
                "type": "endpoint",
                "endpoint": _make_endpoint_row(e)
            })
        
        hierarchy.append({
            "type": "ght",
            "ght": ght_data["ght"],
            "children": ght_children
        })
    
    # Endpoints without GHT
    if no_ght_endpoints:
        hierarchy.append({
            "type": "no_ght",
            "endpoints": [_make_endpoint_row(e) for e in no_ght_endpoints]
        })
    
    ctx = {
        "request": request,
        "title": "Systèmes (Paramétrage)",
        "hierarchy": hierarchy,
        "new_url": "/endpoints/new"
    }
    return templates.TemplateResponse(request, "endpoints_hierarchical.html", ctx)

@router.get("/new", response_class=HTMLResponse)
def new_endpoint(request: Request):
    fields = [
        {"label":"Nom","name":"name","type":"text"},
        {"label":"Type (MLLP|FHIR)","name":"kind","type":"text"},
        {"label":"Rôle (sender|receiver|both)","name":"role","type":"text","value":"both"},
        {"label":"Actif (true/false)","name":"is_enabled","type":"text","value":"true"},
        {"label":"Host (MLLP)","name":"host","type":"text","placeholder":"0.0.0.0"},
        {"label":"Port (MLLP)","name":"port","type":"number"},
        {"label":"Sending App (MSH-3)","name":"sending_app","type":"text"},
        {"label":"Sending Facility (MSH-4)","name":"sending_facility","type":"text"},
        {"label":"Receiving App (MSH-5)","name":"receiving_app","type":"text"},
        {"label":"Receiving Facility (MSH-6)","name":"receiving_facility","type":"text"},
        {"label":"FHIR base URL","name":"base_url","type":"text"},
        {"label":"Auth kind (none|bearer)","name":"auth_kind","type":"text","value":"none"},
        {"label":"Auth token (si bearer)","name":"auth_token","type":"text"},
    ]
    return templates.TemplateResponse(request, "form.html", {"request": request, "title":"Nouveau système", "fields":fields})

@router.post("/new")
def create_endpoint(
    name: str = Form(...),
    kind: str = Form(...),
    role: str = Form("both"),
    is_enabled: str = Form("true"),
    host: str = Form(None),
    port: int = Form(None),
    sending_app: str = Form(None),
    sending_facility: str = Form(None),
    receiving_app: str = Form(None),
    receiving_facility: str = Form(None),
    base_url: str = Form(None),
    auth_kind: str = Form("none"),
    auth_token: str = Form(None),
    session=Depends(get_session),
):
    e = SystemEndpoint(
        name=name, kind=kind.upper(), role=role, is_enabled=_bool_from_str(is_enabled, True),
        host=host, port=port,
        sending_app=sending_app, sending_facility=sending_facility,
        receiving_app=receiving_app, receiving_facility=receiving_facility,
        base_url=base_url, auth_kind=auth_kind, auth_token=auth_token
    )
    session.add(e); session.commit()
    return RedirectResponse(url="/endpoints", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/{endpoint_id}", response_class=HTMLResponse)
def detail_endpoint(endpoint_id: int, request: Request, session=Depends(get_session)):
    e = session.get(SystemEndpoint, endpoint_id)
    if not e:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    is_running = endpoint_id in set(registry.running_ids())
    return templates.TemplateResponse(request, "endpoint_detail.html", {"request": request, "e": e, "is_running": is_running})

# ========= AJOUTS =========

@router.post("/{endpoint_id}/update")
def update_endpoint(
    endpoint_id: int,
    name: str = Form(...),
    kind: str = Form(...),
    role: str = Form("both"),
    is_enabled: str = Form("true"),
    host: str = Form(None),
    port: int = Form(None),
    sending_app: str = Form(None),
    sending_facility: str = Form(None),
    receiving_app: str = Form(None),
    receiving_facility: str = Form(None),
    base_url: str = Form(None),
    auth_kind: str = Form("none"),
    auth_token: str = Form(None),
    session=Depends(get_session),
):
    e = session.get(SystemEndpoint, endpoint_id)
    if not e:
        raise HTTPException(404, "Endpoint not found")

    e.name = name
    e.kind = kind.upper()
    e.role = role
    e.is_enabled = _bool_from_str(is_enabled, True)
    e.host, e.port = host, port
    e.sending_app, e.sending_facility = sending_app, sending_facility
    e.receiving_app, e.receiving_facility = receiving_app, receiving_facility
    e.base_url, e.auth_kind, e.auth_token = base_url, auth_kind, auth_token
    e.updated_at = datetime.now(timezone.utc)

    session.add(e); session.commit()
    return RedirectResponse(url=f"/endpoints/{endpoint_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/{endpoint_id}/delete")
def delete_endpoint(endpoint_id: int, session=Depends(get_session)):
    e = session.get(SystemEndpoint, endpoint_id)
    if not e:
        raise HTTPException(404, "Endpoint not found")
    # stop si en cours d'exécution
    if endpoint_id in set(registry.running_ids()):
        registry.stop(e, session)
    session.delete(e); session.commit()
    return RedirectResponse(url="/endpoints", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/{endpoint_id}/start")
def start_endpoint(endpoint_id: int, session=Depends(get_session)):
    e = session.get(SystemEndpoint, endpoint_id)
    if not e:
        raise HTTPException(404, "Endpoint not found")
    if endpoint_id not in set(registry.running_ids()):
        registry.start(e, session); session.commit()
    return RedirectResponse(url=f"/endpoints/{endpoint_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/{endpoint_id}/stop")
def stop_endpoint(endpoint_id: int, session=Depends(get_session)):
    e = session.get(SystemEndpoint, endpoint_id)
    if not e:
        raise HTTPException(404, "Endpoint not found")
    if endpoint_id in set(registry.running_ids()):
        registry.stop(e, session); session.commit()
    return RedirectResponse(url=f"/endpoints/{endpoint_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/{endpoint_id}/restart")
def restart_endpoint(endpoint_id: int, session=Depends(get_session)):
    e = session.get(SystemEndpoint, endpoint_id)
    if not e:
        raise HTTPException(404, "Endpoint not found")
    if endpoint_id in set(registry.running_ids()):
        registry.stop(e, session)
    registry.start(e, session); session.commit()
    return RedirectResponse(url=f"/endpoints/{endpoint_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/{endpoint_id}/clone-structure", response_class=HTMLResponse)
def show_clone_structure_form(endpoint_id: int, request: Request, session: Session = Depends(get_session)):
    """Affiche le formulaire pour cloner la structure d'un endpoint vers un autre"""
    source = session.get(SystemEndpoint, endpoint_id)
    if not source:
        raise HTTPException(404, "Endpoint source not found")
        
    # Récupérer tous les autres endpoints disponibles comme cibles potentielles
    targets = session.exec(
        select(SystemEndpoint)
        .where(SystemEndpoint.id != endpoint_id)
        .where(SystemEndpoint.role.in_(["receiver", "both"]))
    ).all()
    
    return templates.TemplateResponse(
        request,
        "endpoint_clone_structure.html",
        {
            "request": request,
            "source": source,
            "targets": targets
        }
    )

@router.post("/{source_id}/clone-structure/{target_id}")
async def clone_structure(
    source_id: int,
    target_id: int,
    session: Session = Depends(get_session)
):
    """Clone la structure et les mappings d'un endpoint vers un autre"""
    source = session.get(SystemEndpoint, source_id)
    target = session.get(SystemEndpoint, target_id)
    
    if not source or not target:
        raise HTTPException(404, "Endpoint not found")
    
    if target.role not in ["receiver", "both"]:
        raise HTTPException(400, "Target endpoint must be a receiver")
        
    try:
        # Récupérer les contextes
        source_context = session.exec(
            select(EndpointContext)
            .where(EndpointContext.endpoint_id == source_id)
        ).first()
        
        if not source_context:
            raise HTTPException(400, "Source endpoint has no context")
            
        target_context = session.exec(
            select(EndpointContext)
            .where(EndpointContext.endpoint_id == target_id)
        ).first()
        
        if not target_context:
            target_context = EndpointContext(endpoint_id=target_id)
            session.add(target_context)
            session.commit()
            session.refresh(target_context)
            
        # Cloner les mappings de patients
        source_mappings = session.exec(
            select(PatientContextMapping)
            .where(PatientContextMapping.context_id == source_context.id)
        ).all()
        
        for mapping in source_mappings:
            new_mapping = PatientContextMapping(
                context_id=target_context.id,
                patient_id=mapping.patient_id,
                external_id=mapping.external_id
            )
            session.add(new_mapping)
            
        # Cloner les mappings de dossiers
        source_mappings = session.exec(
            select(DossierContextMapping)
            .where(DossierContextMapping.context_id == source_context.id)
        ).all()
        
        for mapping in source_mappings:
            new_mapping = DossierContextMapping(
                context_id=target_context.id,
                dossier_id=mapping.dossier_id,
                external_id=mapping.external_id
            )
            session.add(new_mapping)
            
        # Cloner les mappings de venues
        source_mappings = session.exec(
            select(VenueContextMapping)
            .where(VenueContextMapping.context_id == source_context.id)
        ).all()
        
        for mapping in source_mappings:
            new_mapping = VenueContextMapping(
                context_id=target_context.id,
                venue_id=mapping.venue_id,
                external_id=mapping.external_id
            )
            session.add(new_mapping)
            
        # Cloner les mappings de mouvements
        source_mappings = session.exec(
            select(MouvementContextMapping)
            .where(MouvementContextMapping.context_id == source_context.id)
        ).all()
        
        for mapping in source_mappings:
            new_mapping = MouvementContextMapping(
                context_id=target_context.id,
                mouvement_id=mapping.mouvement_id,
                external_id=mapping.external_id
            )
            session.add(new_mapping)
            
        # Mettre à jour la dernière valeur de séquence
        target_context.last_sequence_value = source_context.last_sequence_value
        target_context.updated_at = datetime.now(timezone.utc)
        session.add(target_context)
        
        session.commit()
        
        return RedirectResponse(
            url=f"/endpoints/{target_id}/context",
            status_code=status.HTTP_303_SEE_OTHER
        )
        
    except Exception as e:
        logger.exception("Error cloning structure")
        raise HTTPException(500, f"Error cloning structure: {str(e)}")

@router.get("/{endpoint_id}/context", response_class=HTMLResponse)
def show_endpoint_context(endpoint_id: int, request: Request, session: Session = Depends(get_session)):
    """Affiche le contexte d'un endpoint et tous ses mappings"""
    endpoint = session.get(SystemEndpoint, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
        
    # Récupérer le contexte
    context = session.exec(
        select(EndpointContext)
        .where(EndpointContext.endpoint_id == endpoint_id)
    ).first()
    
    if not context:
        # Créer un nouveau contexte si nécessaire
        context = EndpointContext(endpoint_id=endpoint_id)
        session.add(context)
        session.commit()
        session.refresh(context)
    
    # Récupérer tous les mappings
    patient_mappings = session.exec(
        select(PatientContextMapping)
        .where(PatientContextMapping.context_id == context.id)
    ).all()
    
    dossier_mappings = session.exec(
        select(DossierContextMapping)
        .where(DossierContextMapping.context_id == context.id)
    ).all()
    
    venue_mappings = session.exec(
        select(VenueContextMapping)
        .where(VenueContextMapping.context_id == context.id)
    ).all()
    
    mouvement_mappings = session.exec(
        select(MouvementContextMapping)
        .where(MouvementContextMapping.context_id == context.id)
    ).all()
    
    return templates.TemplateResponse(
        "endpoint_context.html",
        {
            "request": request,
            "endpoint": endpoint,
            "context": context,
            "patient_mappings": patient_mappings,
            "dossier_mappings": dossier_mappings,
            "venue_mappings": venue_mappings,
            "mouvement_mappings": mouvement_mappings
        }
    )
