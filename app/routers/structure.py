import logging
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from app.db import get_session
from app.models_endpoints import SystemEndpoint
from app.services.fhir_structure import entity_to_fhir_location
from app.services.fhir_transport import post_fhir_bundle
from app.services.structure_schedule import (
    apply_scheduled_status,
    form_datetime_to_hl7,
    hl7_to_form_datetime,
)
from app.services.mfn_importer import import_mfn
from app.dependencies.ght import require_ght_context

logger = logging.getLogger(__name__)
from app.models_structure import (
    EntiteGeographique, Pole, Service, UniteFonctionnelle,
    UniteHebergement, Chambre, Lit,
    LocationStatus, LocationMode, LocationPhysicalType, LocationServiceType
)

# Route principale pour les pages web
router = APIRouter(
    prefix="/structure",
    tags=["structure"],
    dependencies=[Depends(require_ght_context)],
)

# Route API pour les endpoints JSON
api_router = APIRouter(
    prefix="/api/structure",
    tags=["structure_api"],
    dependencies=[Depends(require_ght_context)],
)

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@api_router.get("/tree")
async def get_structure_tree(
    session: Session = Depends(get_session),
    ej: Optional[int] = Query(None, description="ID de l'établissement juridique à filtrer"),
    eg_ids: Optional[str] = Query(None, description="Liste d'IDs d'entités géographiques séparés par des virgules")
):
    # Apply scheduled status updates
    changed = False
    for model in (Pole, Service, UniteFonctionnelle, UniteHebergement, Chambre, Lit):
        entities = session.exec(select(model)).all()
        if apply_scheduled_status(entities):
            changed = True
    if changed:
        session.commit()
    
    # Start with EGs (filtered by ej OR eg_ids, with eg_ids taking precedence)
    query = select(EntiteGeographique)
    if eg_ids:
        # Filter by specific EG IDs
        eg_id_list = [int(id_str) for id_str in eg_ids.split(',')]
        query = query.where(EntiteGeographique.id.in_(eg_id_list))
    elif ej:
        # Filter by entite juridique
        query = query.where(EntiteGeographique.entite_juridique_id == ej)
    
    # Load full hierarchy
    query = (query
        .options(selectinload(EntiteGeographique.poles)
            .selectinload(Pole.services)
            .selectinload(Service.unites_fonctionnelles)
            .selectinload(UniteFonctionnelle.unites_hebergement)
            .selectinload(UniteHebergement.chambres)
            .selectinload(Chambre.lits)))
    
    egs = session.exec(query).all()
    
    # Build tree structure
    tree = []
    for eg in egs:
        eg_node = {
            "id": eg.id,
            "name": eg.name,
            "type": "eg",
            "poles": [],
            "services": [],
            "ufs": [],
            "unites_hebergement": [],
            "chambres": [],
            "lits": []
        }
        
        for pole in eg.poles:
            pole_node = {
                "id": pole.id,
                "name": pole.name,
                "type": "pole",
                "services": [],
                "ufs": [],
                "unites_hebergement": [],
                "chambres": [],
                "lits": []
            }
            
            for service in pole.services:
                service_node = {
                    "id": service.id,
                    "name": service.name,
                    "type": "service",
                    "ufs": [],
                    "unites_hebergement": [],
                    "chambres": [],
                    "lits": []
                }
                
                for uf in service.unites_fonctionnelles:
                    uf_node = {
                        "id": uf.id,
                        "name": uf.name,
                        "type": "uf",
                        "unites_hebergement": [],
                        "chambres": [],
                        "lits": []
                    }
                    
                    for uh in uf.unites_hebergement:
                        uh_node = {
                            "id": uh.id,
                            "name": uh.name,
                            "type": "uh",
                            "chambres": [],
                            "lits": []
                        }
                        
                        for chambre in uh.chambres:
                            chambre_node = {
                                "id": chambre.id,
                                "name": chambre.name,
                                "type": "chambre",
                                "lits": []
                            }
                            
                            for lit in chambre.lits:
                                lit_node = {
                                    "id": lit.id,
                                    "name": lit.name,
                                    "type": "lit"
                                }
                                chambre_node["lits"].append(lit_node)
                            
                            uh_node["chambres"].append(chambre_node)
                        
                        uf_node["unites_hebergement"].append(uh_node)
                    
                    service_node["ufs"].append(uf_node)
                
                pole_node["services"].append(service_node)
            
            eg_node["poles"].append(pole_node)
        
        tree.append(eg_node)
    
    return tree

@api_router.get("/details/{type}/{id}")
async def get_structure_details(
    type: str,
    id: int,
    session: Session = Depends(get_session)
):
    # Sélectionner l'entité appropriée selon le type
    model_map = {
        'eg': EntiteGeographique,
        'pole': Pole,
        'service': Service,
        'uf': UniteFonctionnelle,
        'uh': UniteHebergement,
        'chambre': Chambre,
        'lit': Lit
    }
    
    model = model_map.get(type)
    if not model:
        raise HTTPException(status_code=400, detail="Type invalide")
        
    entity = session.get(model, id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entité non trouvée")
        
    # Construire un dictionnaire avec les détails
    details = {
        "id": entity.id,
        "name": entity.name,
        "type": type,
        "identifier": getattr(entity, 'identifier', None),
        "description": getattr(entity, 'description', None),
        "status": getattr(entity, 'status', 'active')
    }
    
    # Ajouter les champs spécifiques selon le type
    if type == 'service':
        details["service_type"] = getattr(entity, 'service_type', None)
    elif type == 'uf':
        details["uf_type"] = getattr(entity, 'uf_type', None)
        
    return details


@router.get("", response_class=HTMLResponse)
async def structure_dashboard(
    request: Request,
    session: Session = Depends(get_session),
    ej: Optional[int] = Query(None, description="ID de l'établissement juridique à filtrer")
):
    context = {
        "request": request,
        "service_types": [stype.value for stype in LocationServiceType],
    }
    
    if ej:
        # Récupérer les EG de l'établissement et son nom
        egs = session.exec(
            select(EntiteGeographique)
            .where(EntiteGeographique.entite_juridique_id == ej)
        ).all()
        context["filtered_ej_id"] = ej
        context["filtered_egs"] = [eg.id for eg in egs]
    
    return templates.TemplateResponse("structure_new.html", context)

@router.post("/import/hl7")
async def import_structure_hl7(
    request: Request,
    session: Session = Depends(get_session),
):
    """Importe un message HL7 MFN^M05 (text/plain) dans le GHT courant.

    - Le GHT est déterminé via le middleware de contexte (request.state.ght_context).
    - Retourne un JSON de synthèse: nombre d'EJ, d'EG et de services créés/mis à jour.
    """
    # Vérifier contexte GHT
    ght = getattr(request.state, "ght_context", None)
    if not ght:
        raise HTTPException(status_code=400, detail="Contexte GHT manquant")

    try:
        body = await request.body()
        text = body.decode("utf-8", errors="ignore")
    except Exception:
        raise HTTPException(status_code=400, detail="Impossible de lire le payload text/plain")

    if not text or "MSH" not in text or "MFN^M05" not in text:
        # On reste permissif: certains extracts peuvent ne pas inclure ^M05
        if not text:
            raise HTTPException(status_code=400, detail="Payload vide")

    summary = import_mfn(text, session, ght)
    return {"status": "ok", "created": summary}

# --- Entité Géographique ---
@router.get("/eg", response_class=HTMLResponse)
async def list_entites_geographiques(
    request: Request,
    session: Session = Depends(get_session),
    q: Optional[str] = Query(None, alias="q"),
):
    query = select(EntiteGeographique)
    if q:
        like = f"%{q}%"
        query = query.where(
            (EntiteGeographique.name.ilike(like))
            | (EntiteGeographique.identifier.ilike(like))
            | (EntiteGeographique.finess.ilike(like))
        )
    
    egs = session.exec(query.order_by(EntiteGeographique.name)).all()
    
    return templates.TemplateResponse(
        "structure/eg_list.html",
        {
            "request": request,
            "entites_geographiques": egs,
            "search_term": q,
        },
    )

@router.get("/api/eg", response_model=List[EntiteGeographique])
async def list_entites_geographiques_api(
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    return session.exec(select(EntiteGeographique).offset(skip).limit(limit)).all()

@router.post("/eg", response_model=EntiteGeographique)
async def create_entite_geographique(
    eg: EntiteGeographique,
    session: Session = Depends(get_session)
):
    session.add(eg)
    session.commit()
    session.refresh(eg)
    
    # Convertir en FHIR et envoyer aux destinataires
    fhir_location = entity_to_fhir_location(eg, session)
    
    # Recherche des endpoints FHIR actifs
    fhir_endpoints = session.exec(
        select(SystemEndpoint)
        .where(SystemEndpoint.kind == "fhir")
        .where(SystemEndpoint.is_enabled == True)
    ).all()
    
    # Création et envoi du bundle
    if fhir_endpoints:
        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [{
                "resource": fhir_location,
                "request": {
                    "method": "PUT",
                    "url": f"Location/{eg.id}"
                }
            }]
        }
        
        # Envoi à chaque endpoint
        for endpoint in fhir_endpoints:
            try:
                await post_fhir_bundle(endpoint, bundle)
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi FHIR à {endpoint.name}: {e}")
    
    return eg

# --- Pôles ---
@router.get("/poles", response_class=HTMLResponse)
async def list_poles(
    request: Request,
    session: Session = Depends(get_session),
    eg_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None, alias="q"),
):
    query = select(Pole)
    if eg_id:
        query = query.where(Pole.entite_geo_id == eg_id)
    if q:
        like = f"%{q}%"
        query = query.where(
            (Pole.name.ilike(like))
            | (Pole.identifier.ilike(like))
        )
    
    poles = session.exec(query.order_by(Pole.name)).all()
    if apply_scheduled_status(poles):
        session.commit()
    
    egs = session.exec(select(EntiteGeographique).order_by(EntiteGeographique.name)).all()
    eg_map = {eg.id: eg.name for eg in egs}
    
    return templates.TemplateResponse(
        "structure/poles_list.html",
        {
            "request": request,
            "poles": poles,
            "entites_geographiques": egs,
            "eg_map": eg_map,
            "selected_eg_id": eg_id,
            "search_term": q,
        },
    )

@router.get("/api/poles", response_model=List[Pole])
async def list_poles_api(
    session: Session = Depends(get_session),
    eg_id: Optional[int] = None
):
    query = select(Pole)
    if eg_id:
        query = query.where(Pole.entite_geo_id == eg_id)
    poles = session.exec(query).all()
    if apply_scheduled_status(poles):
        session.commit()
    return poles

@router.post("/poles", response_model=Pole)
async def create_pole(
    pole: Pole,
    session: Session = Depends(get_session)
):
    apply_scheduled_status([pole])
    session.add(pole)
    session.commit()
    session.refresh(pole)
    return pole

# --- Services ---
@router.get("/services", response_class=HTMLResponse)
async def list_services(
    request: Request,
    session: Session = Depends(get_session),
    pole_id: Optional[int] = Query(None),
    service_type: Optional[LocationServiceType] = Query(None),
    q: Optional[str] = Query(None, alias="q"),
):
    query = select(Service)
    if pole_id:
        query = query.where(Service.pole_id == pole_id)
    if service_type:
        query = query.where(Service.service_type == service_type)
    if q:
        like = f"%{q}%"
        query = query.where(
            (Service.name.ilike(like))
            | (Service.identifier.ilike(like))
        )
    
    services = session.exec(query.order_by(Service.name)).all()
    if apply_scheduled_status(services):
        session.commit()
    
    poles = session.exec(select(Pole).order_by(Pole.name)).all()
    pole_map = {pole.id: pole.name for pole in poles}
    
    return templates.TemplateResponse(
        "structure/services_list.html",
        {
            "request": request,
            "services": services,
            "poles": poles,
            "pole_map": pole_map,
            "service_types": LocationServiceType,
            "selected_pole_id": pole_id,
            "selected_service_type": service_type.value if service_type else None,
            "search_term": q,
        },
    )

@router.get("/api/services", response_model=List[Service])
async def list_services_api(
    session: Session = Depends(get_session),
    pole_id: Optional[int] = None,
    service_type: Optional[LocationServiceType] = None
):
    query = select(Service)
    if pole_id:
        query = query.where(Service.pole_id == pole_id)
    if service_type:
        query = query.where(Service.service_type == service_type)
    services = session.exec(query).all()
    if apply_scheduled_status(services):
        session.commit()
    return services

@router.post("/services", response_model=Service)
async def create_service(
    service: Service,
    session: Session = Depends(get_session)
):
    apply_scheduled_status([service])
    session.add(service)
    session.commit()
    session.refresh(service)
    return service

# --- Unités Fonctionnelles ---
@router.get("/ufs", response_class=HTMLResponse)
async def list_unites_fonctionnelles(
    request: Request,
    session: Session = Depends(get_session),
    service_id: Optional[int] = Query(None),
    service_type: Optional[LocationServiceType] = Query(None),
    q: Optional[str] = Query(None, alias="q"),
):
    query = select(UniteFonctionnelle)
    if service_id:
        query = query.where(UniteFonctionnelle.service_id == service_id)
    if service_type:
        service_ids = session.exec(
            select(Service.id).where(Service.service_type == service_type)
        ).all()
        if service_ids:
            query = query.where(UniteFonctionnelle.service_id.in_(service_ids))
        else:
            query = query.where(False)  # Aucun service ne correspond
    if q:
        like = f"%{q}%"
        query = query.where(
            (UniteFonctionnelle.name.ilike(like))
            | (UniteFonctionnelle.identifier.ilike(like))
        )

    ufs = session.exec(query.order_by(UniteFonctionnelle.name)).all()
    changed = apply_scheduled_status(ufs)
    services = session.exec(select(Service).order_by(Service.name)).all()
    if apply_scheduled_status(services):
        changed = True
    if changed:
        session.commit()
    service_map = {service.id: service.name for service in services}

    return templates.TemplateResponse(
        "structure/ufs.html",
        {
            "request": request,
            "unites_fonctionnelles": ufs,
            "services": services,
            "service_map": service_map,
            "service_type_labels": {
                st.value: st.name for st in LocationServiceType
            },
            "selected_service_id": service_id,
            "selected_service_type": service_type.value if service_type else None,
            "search_term": q,
        },
    )

@router.get("/api/ufs", response_model=List[UniteFonctionnelle])
async def list_unites_fonctionnelles_api(
    session: Session = Depends(get_session),
    service_id: Optional[int] = None,
):
    query = select(UniteFonctionnelle)
    if service_id:
        query = query.where(UniteFonctionnelle.service_id == service_id)
    ufs = session.exec(query).all()
    if apply_scheduled_status(ufs):
        session.commit()
    return ufs

@router.post("/ufs", response_model=UniteFonctionnelle)
async def create_unite_fonctionnelle(
    uf: UniteFonctionnelle,
    session: Session = Depends(get_session)
):
    apply_scheduled_status([uf])
    session.add(uf)
    session.commit()
    session.refresh(uf)
    return uf

# --- Unités d'Hébergement ---
@router.get("/uh", response_class=HTMLResponse)
async def list_unites_hebergement(
    request: Request,
    session: Session = Depends(get_session),
    uf_id: Optional[int] = None,
    mode: Optional[str] = None,
    status: Optional[str] = None
):
    # Construction de la requête avec les filtres
    query = select(UniteHebergement)
    if uf_id:
        query = query.where(UniteHebergement.unite_fonctionnelle_id == uf_id)
    if mode:
        query = query.where(UniteHebergement.mode == mode)
    if status:
        query = query.where(UniteHebergement.status == status)
    
    uhs = session.exec(query).all()
    changed = apply_scheduled_status(uhs)

    # Récupération des UFs pour le filtre
    ufs = session.exec(select(UniteFonctionnelle)).all()
    if apply_scheduled_status(ufs):
        changed = True
    if changed:
        session.commit()
    
    return templates.TemplateResponse(
        "structure/uh.html",
        {
            "request": request,
            "unites_hebergement": uhs,
            "unites_fonctionnelles": ufs,
            "modes": ["instance", "hospitalization", "ambulatory", "virtual"],
            "statuses": ["active", "suspended", "inactive"],
            "selected_uf_id": uf_id,
            "selected_mode": mode,
            "selected_status": status
        }
    )

@router.get("/api/uh", response_model=List[UniteHebergement])
async def list_unites_hebergement_api(
    session: Session = Depends(get_session),
    uf_id: Optional[int] = None,
):
    query = select(UniteHebergement)
    if uf_id:
        query = query.where(UniteHebergement.unite_fonctionnelle_id == uf_id)
    uhs = session.exec(query).all()
    if apply_scheduled_status(uhs):
        session.commit()
    return uhs

@router.get("/uh/new", response_class=HTMLResponse)
async def new_unite_hebergement_form(
    request: Request,
    session: Session = Depends(get_session)
):
    ufs = session.exec(select(UniteFonctionnelle)).all()
    return templates.TemplateResponse(
        "structure/uh_form.html",
        {
            "request": request,
            "unites_fonctionnelles": ufs,
            "modes": ["instance", "hospitalization", "ambulatory", "virtual"],
            "statuses": ["active", "suspended", "inactive"],
            "activation_date_value": None,
            "deactivation_date_value": None,
        }
    )

@router.get("/uh/{uh_id}", response_class=HTMLResponse)
async def view_unite_hebergement(
    request: Request,
    uh_id: int,
    session: Session = Depends(get_session)
):
    """Vue détaillée d'une UH avec ses chambres"""
    uh = session.get(UniteHebergement, uh_id)
    if not uh:
        raise HTTPException(status_code=404, detail="Unité d'hébergement non trouvée")
    changed = apply_scheduled_status([uh])

    # Charger les chambres liées à cette UH avec leurs lits
    chambres = session.exec(select(Chambre).where(Chambre.unite_hebergement_id == uh_id)).all()
    # Eager-load lits for each chambre so template can access them
    for chambre in chambres:
        lits = session.exec(select(Lit).where(Lit.chambre_id == chambre.id)).all()
        if apply_scheduled_status(lits):
            changed = True
        # attach lits to the chambre instance for template rendering
        setattr(chambre, "lits", lits)
    if apply_scheduled_status(chambres):
        changed = True
    if changed:
        session.commit()
    
    return templates.TemplateResponse(
        "structure/uh_detail.html",
        {
            "request": request,
            "uh": uh,
            "chambres": chambres
        }
    )

@router.get("/uh/{uh_id}/edit", response_class=HTMLResponse)
async def edit_unite_hebergement_form(
    request: Request,
    uh_id: int,
    session: Session = Depends(get_session)
):
    uh = session.get(UniteHebergement, uh_id)
    if not uh:
        raise HTTPException(status_code=404, detail="Unité d'hébergement non trouvée")
    changed = apply_scheduled_status([uh])

    ufs = session.exec(select(UniteFonctionnelle)).all()
    if apply_scheduled_status(ufs):
        changed = True
    if changed:
        session.commit()
    return templates.TemplateResponse(
        "structure/uh_form.html",
        {
            "request": request,
            "uh": uh,
            "unites_fonctionnelles": ufs,
            "modes": ["instance", "hospitalization", "ambulatory", "virtual"],
            "statuses": ["active", "suspended", "inactive"],
            "activation_date_value": hl7_to_form_datetime(getattr(uh, "activation_date", None)),
            "deactivation_date_value": hl7_to_form_datetime(getattr(uh, "deactivation_date", None)),
        }
    )

@router.post("/uh", response_model=UniteHebergement)
async def create_unite_hebergement(
    request: Request,
    session: Session = Depends(get_session)
):
    form = await request.form()
    mode_value = form.get("mode") or LocationMode.INSTANCE
    status_value = form.get("status") or LocationStatus.ACTIVE
    physical_value = form.get("physical_type") or LocationPhysicalType.RO
    uh = UniteHebergement(
        name=form["name"],
        identifier=form["identifier"],
        unite_fonctionnelle_id=int(form["unite_fonctionnelle_id"]),
        mode=LocationMode(mode_value),
        status=LocationStatus(status_value),
        physical_type=LocationPhysicalType(physical_value),
    )
    uh.activation_date = form_datetime_to_hl7(form.get("activation_date"))
    uh.deactivation_date = form_datetime_to_hl7(form.get("deactivation_date"))
    apply_scheduled_status([uh])
    session.add(uh)
    session.commit()
    session.refresh(uh)
    return RedirectResponse(url="/structure/uh", status_code=303)

@router.post("/uh/{uh_id}", response_model=UniteHebergement)
async def update_unite_hebergement(
    request: Request,
    uh_id: int,
    session: Session = Depends(get_session)
):
    uh = session.get(UniteHebergement, uh_id)
    if not uh:
        raise HTTPException(status_code=404, detail="Unité d'hébergement non trouvée")
    
    form = await request.form()
    uh.name = form["name"]
    uh.identifier = form.get("identifier", uh.identifier)
    uh.unite_fonctionnelle_id = int(form["unite_fonctionnelle_id"])
    uh.mode = LocationMode(form.get("mode", uh.mode))
    uh.status = LocationStatus(form.get("status", uh.status))
    physical_value = form.get("physical_type") or uh.physical_type
    uh.physical_type = LocationPhysicalType(physical_value)
    uh.activation_date = form_datetime_to_hl7(form.get("activation_date"))
    uh.deactivation_date = form_datetime_to_hl7(form.get("deactivation_date"))
    apply_scheduled_status([uh])
    
    session.add(uh)
    session.commit()
    return RedirectResponse(url="/structure/uh", status_code=303)

# --- Suppression UH ---
@router.post("/uh/{uh_id}/delete")
async def delete_unite_hebergement(
    uh_id: int,
    session: Session = Depends(get_session)
):
    """Supprime une unité d'hébergement et redirige vers la liste"""
    uh = session.get(UniteHebergement, uh_id)
    if not uh:
        raise HTTPException(status_code=404, detail="Unité d'hébergement non trouvée")
    
    # On vérifie d'abord qu'il n'y a plus de chambres actives
    chambres = session.exec(
        select(Chambre)
        .where(Chambre.unite_hebergement_id == uh_id)
        .where(Chambre.status == "active")
    ).all()
    
    if chambres:
        raise HTTPException(
            status_code=400,
            detail="Impossible de supprimer l'UH : des chambres actives y sont rattachées"
        )

    # Delete all inactive chambres and their lits first
    inactive_chambres = session.exec(
        select(Chambre)
        .where(Chambre.unite_hebergement_id == uh_id)
        .where(Chambre.status != "active")
    ).all()

    for chambre in inactive_chambres:
        # Delete all lits in the chambre
        lits = session.exec(
            select(Lit).where(Lit.chambre_id == chambre.id)
        ).all()
        for lit in lits:
            session.delete(lit)
        # Then delete the chambre
        session.delete(chambre)

    session.commit()
    session.delete(uh)
    session.commit()
    return RedirectResponse(url="/structure/uh", status_code=303)

# --- Chambres ---
@router.get("/chambres", response_class=HTMLResponse)
async def list_chambres(
    request: Request,
    session: Session = Depends(get_session),
    uh_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None, alias="q"),
):
    query = select(Chambre)
    if uh_id:
        query = query.where(Chambre.unite_hebergement_id == uh_id)
    if q:
        like = f"%{q}%"
        query = query.where(
            (Chambre.name.ilike(like))
            | (Chambre.identifier.ilike(like))
        )
    
    chambres = session.exec(query.order_by(Chambre.name)).all()
    if apply_scheduled_status(chambres):
        session.commit()
    
    uhs = session.exec(select(UniteHebergement).order_by(UniteHebergement.name)).all()
    uh_map = {uh.id: uh.name for uh in uhs}
    
    return templates.TemplateResponse(
        "structure/chambres_list.html",
        {
            "request": request,
            "chambres": chambres,
            "unites_hebergement": uhs,
            "uh_map": uh_map,
            "selected_uh_id": uh_id,
            "search_term": q,
        },
    )

@router.get("/chambres/new", response_class=HTMLResponse)
async def new_chambre_form(
    request: Request,
    uh_id: int,
    session: Session = Depends(get_session)
):
    """Formulaire de création d'une chambre"""
    uh = session.get(UniteHebergement, uh_id)
    if not uh:
        raise HTTPException(status_code=404, detail="Unité d'hébergement non trouvée")
    if apply_scheduled_status([uh]):
        session.commit()

    return templates.TemplateResponse(
        "structure/chambre_form.html",
        {
            "request": request,
            "unite_hebergement": uh,
            "physical_types": [type.value for type in LocationPhysicalType],
            "statuses": ["active", "suspended", "inactive"],
            "activation_date_value": None,
            "deactivation_date_value": None,
        }
    )

@router.post("/chambres/{chambre_id}/delete")
async def delete_chambre(
    chambre_id: int,
    session: Session = Depends(get_session)
):
    """Supprime une chambre et redirige vers l'UH parente"""
    chambre = session.get(Chambre, chambre_id)
    if not chambre:
        raise HTTPException(status_code=404, detail="Chambre non trouvée")
    
    # On vérifie d'abord qu'il n'y a plus de lits actifs
    lits = session.exec(
        select(Lit)
        .where(Lit.chambre_id == chambre_id)
        .where(Lit.status == "active")
    ).all()
    
    if lits:
        raise HTTPException(
            status_code=400,
            detail="Impossible de supprimer la chambre : des lits actifs y sont rattachés"
        )

    # Delete all lits first (active or not)
    all_lits = session.exec(
        select(Lit).where(Lit.chambre_id == chambre_id)
    ).all()
    for lit in all_lits:
        session.delete(lit)
    session.commit()

    uh_id = chambre.unite_hebergement_id
    session.delete(chambre)
    session.commit()
    return RedirectResponse(url=f"/structure/uh/{uh_id}", status_code=303)

@router.get("/chambres", response_model=List[Chambre])
async def list_chambres(
    session: Session = Depends(get_session),
    uh_id: Optional[int] = None,
    status: Optional[LocationStatus] = None
):
    query = select(Chambre)
    if uh_id:
        query = query.where(Chambre.unite_hebergement_id == uh_id)
    if status:
        query = query.where(Chambre.status == status)
    chambres = session.exec(query).all()
    if apply_scheduled_status(chambres):
        session.commit()
    return chambres

@router.post("/chambres", response_model=Chambre)
async def create_chambre(
    request: Request,
    session: Session = Depends(get_session)
):
    form = await request.form()
    status_value = form.get("status") or LocationStatus.ACTIVE
    chambre = Chambre(
        name=form["name"],
        identifier=form["identifier"],
        unite_hebergement_id=int(form["unite_hebergement_id"]),
        physical_type=LocationPhysicalType(form.get("physical_type", LocationPhysicalType.RO)),
        mode=LocationMode(form.get("mode", LocationMode.INSTANCE)),
        status=LocationStatus(status_value),
        type_chambre=form.get("type_chambre"),
        gender_usage=form.get("gender_usage")
    )
    chambre.activation_date = form_datetime_to_hl7(form.get("activation_date"))
    chambre.deactivation_date = form_datetime_to_hl7(form.get("deactivation_date"))
    apply_scheduled_status([chambre])
    session.add(chambre)
    session.commit()
    session.refresh(chambre)
    
    # Rediriger vers la vue de l'UH parente
    return RedirectResponse(
        url=f"/structure/uh/{chambre.unite_hebergement_id}",
        status_code=303
    )

# --- Lits ---
@router.get("/lits", response_class=HTMLResponse)
async def list_lits(
    request: Request,
    session: Session = Depends(get_session),
    chambre_id: Optional[int] = Query(None),
    status: Optional[LocationStatus] = Query(None),
    q: Optional[str] = Query(None, alias="q"),
):
    query = select(Lit)
    if chambre_id:
        query = query.where(Lit.chambre_id == chambre_id)
    if status:
        query = query.where(Lit.status == status)
    if q:
        like = f"%{q}%"
        query = query.where(
            (Lit.name.ilike(like))
            | (Lit.identifier.ilike(like))
        )
    
    lits = session.exec(query.order_by(Lit.name)).all()
    if apply_scheduled_status(lits):
        session.commit()
    
    chambres = session.exec(select(Chambre).order_by(Chambre.name)).all()
    chambre_map = {chambre.id: chambre.name for chambre in chambres}
    
    return templates.TemplateResponse(
        "structure/lits_list.html",
        {
            "request": request,
            "lits": lits,
            "chambres": chambres,
            "chambre_map": chambre_map,
            "statuses": LocationStatus,
            "selected_chambre_id": chambre_id,
            "selected_status": status.value if status else None,
            "search_term": q,
        },
    )

@router.get("/api/lits", response_model=List[Lit])
async def list_lits_api(
    session: Session = Depends(get_session),
    chambre_id: Optional[int] = None,
    status: Optional[LocationStatus] = None
):
    query = select(Lit)
    if chambre_id:
        query = query.where(Lit.chambre_id == chambre_id)
    if status:
        query = query.where(Lit.status == status)
    lits = session.exec(query).all()
    if apply_scheduled_status(lits):
        session.commit()
    return lits

@router.post("/lits", response_model=Lit)
async def create_lit(
    lit: Lit,
    session: Session = Depends(get_session)
):
    apply_scheduled_status([lit])
    session.add(lit)
    session.commit()
    session.refresh(lit)
    return lit


@router.get("/search", response_class=HTMLResponse)
async def structure_search(
    request: Request,
    session: Session = Depends(get_session),
    service_type: Optional[LocationServiceType] = Query(None),
    uf_id: Optional[int] = Query(None),
):
    services = session.exec(select(Service).order_by(Service.name)).all()
    if apply_scheduled_status(services):
        session.commit()

    service_ids = [svc.id for svc in services if not service_type or svc.service_type == service_type]
    available_ufs_query = select(UniteFonctionnelle).order_by(UniteFonctionnelle.name)
    if service_type:
        if service_ids:
            available_ufs_query = available_ufs_query.where(UniteFonctionnelle.service_id.in_(service_ids))
        else:
            available_ufs_query = available_ufs_query.where(False)
    ufs = session.exec(available_ufs_query).all()
    if apply_scheduled_status(ufs):
        session.commit()

    results = []
    if service_type or uf_id:
        lits = _fetch_available_lits(session, service_type=service_type, uf_id=uf_id)
        for lit in lits:
            chambre = lit.chambre
            uh = chambre.unite_hebergement if chambre else None
            uf = uh.unite_fonctionnelle if uh else None
            service = uf.service if uf else None
            pole = service.pole if service else None
            eg = pole.entite_geo if pole else None
            results.append(
                {
                    "lit": lit,
                    "chambre": chambre,
                    "uh": uh,
                    "uf": uf,
                    "service": service,
                    "pole": pole,
                    "entite_geo": eg,
                }
            )

    return templates.TemplateResponse(
        "structure/search.html",
        {
            "request": request,
            "service_types": [stype for stype in LocationServiceType],
            "services": services,
            "unites_fonctionnelles": ufs,
            "selected_service_type": service_type.value if service_type else None,
            "selected_uf_id": uf_id,
            "results": results,
        },
    )

# --- Utilitaires de recherche ---
def _fetch_available_lits(
    session: Session,
    service_type: Optional[LocationServiceType] = None,
    uf_id: Optional[int] = None,
):
    """Return lits libres en tenant compte des programmations."""
    query = (
        select(Lit)
        .options(
            selectinload(Lit.chambre)
            .selectinload(Chambre.unite_hebergement)
            .selectinload(UniteHebergement.unite_fonctionnelle)
            .selectinload(UniteFonctionnelle.service)
            .selectinload(Service.pole)
            .selectinload(Pole.entite_geo)
        )
        .join(Chambre)
        .join(UniteHebergement)
        .join(UniteFonctionnelle)
        .join(Service)
        .where(Lit.operationalStatus == "libre")
    )
    if service_type:
        query = query.where(Service.service_type == service_type)
    if uf_id:
        query = query.where(UniteFonctionnelle.id == uf_id)

    lits = session.exec(query).scalars().all()
    changed = apply_scheduled_status(lits)
    for lit in lits:
        if lit.chambre and apply_scheduled_status([lit.chambre]):
            changed = True
        uh = getattr(lit.chambre, "unite_hebergement", None)
        if uh and apply_scheduled_status([uh]):
            changed = True
        uf = getattr(uh, "unite_fonctionnelle", None) if uh else None
        if uf and apply_scheduled_status([uf]):
            changed = True
        service = getattr(uf, "service", None) if uf else None
        if service and apply_scheduled_status([service]):
            changed = True
        pole = getattr(service, "pole", None) if service else None
        if pole and apply_scheduled_status([pole]):
            changed = True
        eg = getattr(pole, "entite_geo", None) if pole else None
        if eg and apply_scheduled_status([eg]):
            changed = True
    if changed:
        session.commit()
    # Filtrer les lits actifs après application
    return [lit for lit in lits if lit.status == LocationStatus.ACTIVE]


@router.get("/search/lits-disponibles")
async def search_lits_disponibles(
    session: Session = Depends(get_session),
    service_type: Optional[LocationServiceType] = None,
    uf_id: Optional[int] = None,
):
    """Recherche les lits disponibles avec filtres (JSON)."""
    return _fetch_available_lits(session, service_type=service_type, uf_id=uf_id)


@router.get("/{type}/{id}/map", response_class=HTMLResponse)
async def view_structure_map(
    type: str,
    id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    """
    Affiche une carte/plan de l'entité de structure.
    Cette fonctionnalité est en cours de développement.
    """
    # Mapping des types vers les modèles
    model_map = {
        "eg": EntiteGeographique,
        "pole": Pole,
        "service": Service,
        "uf": UniteFonctionnelle,
        "uh": UniteHebergement,
        "chambre": Chambre,
        "lit": Lit
    }
    
    model = model_map.get(type)
    if not model:
        raise HTTPException(status_code=404, detail=f"Type de structure '{type}' non reconnu")
    
    # Récupérer l'entité
    entity = session.get(model, id)
    if not entity:
        raise HTTPException(status_code=404, detail=f"{type.upper()} #{id} non trouvé")
    
    # Pour l'instant, retourner une page simple indiquant que cette fonctionnalité arrive bientôt
    return templates.TemplateResponse("structure_map_placeholder.html", {
        "request": request,
        "entity": entity,
        "type": type,
        "type_label": {
            "eg": "Entité Géographique",
            "pole": "Pôle",
            "service": "Service",
            "uf": "Unité Fonctionnelle",
            "uh": "Unité d'Hébergement",
            "chambre": "Chambre",
            "lit": "Lit"
        }.get(type, type.upper())
    })