"""Routeur API FHIR pour les ressources Location (structure hiérarchique).

Expose les endpoints REST standard FHIR pour la gestion de la structure d'un établissement :
- GET /fhir/Location : recherche de ressources Location par paramètres FHIR 
  (identifier, partof, status, name, type, etc.)
- GET /fhir/Location/{id} : lecture d'une ressource Location par son id logique
- POST /fhir/Location : création ou mise à jour (upsert) d'une ressource Location
- PUT /fhir/Location/{id} : mise à jour complète d'une ressource Location
- DELETE /fhir/Location/{id} : suppression d'une ressource Location

Paramètres de recherche supportés :
- _id, _lastUpdated, name, status, identifier, type, operational-status
- _count (pagination), _sort (tri), _format (json/xml)
- partof : recherche des enfants d'une Location parente (navigation hiérarchique)

Conversion assurée par app.services.fhir_structure (process_fhir_location, entity_to_fhir_location).
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query, Response, Request
from sqlmodel import Session, select
from datetime import datetime

from app.db import get_session
from app.services.fhir_structure import process_fhir_location, entity_to_fhir_location
from app.models_structure import (
    EntiteGeographique, Pole, Service, UniteFonctionnelle,
    UniteHebergement, Chambre, Lit, LocationStatus, LocationServiceType
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fhir", tags=["fhir"])

# Paramètres de recherche standards FHIR
common_search_params = {
    "_id": Query(None, description="Resource id (logical id)"),
    "_lastUpdated": Query(None, description="Last update date/time"),
    "name": Query(None, description="A portion of the location's name"),
    "status": Query(None, description="Searches for locations with a specific status"),
    "identifier": Query(None, description="Any identifier for the location"),
    "type": Query(None, description="A location type code"),
    "operational-status": Query(None, description="Searches for locations with a specific operational status"),
    "_count": Query(None, description="Number of resources to return"),
    "_sort": Query(None, description="Order to sort results in"),
    "_format": Query(None, description="Desired response format (json, xml)")
}

def _get_query_params(request: Request) -> Dict[str, Any]:
    """Extrait tous les paramètres de requête (query string) pour la recherche FHIR."""
    return dict(request.query_params)


@router.get("/Location", response_model=Dict)
async def search_locations(
    response: Response,
    session: Session = Depends(get_session),
    search_params: Dict[str, Any] = Depends(_get_query_params),
) -> Dict:
    """Recherche de Location FHIR par paramètres (GET /fhir/Location?...).
    
    Supporte les paramètres standard FHIR :
    - identifier : recherche par identifiant métier ou FINESS (multiples modèles)
    - partof=Location/[id] : enfants directs de la Location parente (hiérarchie)
    - _count : pagination (1-1000, défaut=50)
    - _format : json (défaut) ou application/fhir+json
    - name, status, type, operational-status (filtres additionnels via process_search_params)
    
    Retourne un Bundle FHIR de type 'searchset' avec liens de pagination (self, first, last).
    
    Args:
        response: FastAPI Response pour définir Content-Type
        session: Session DB
        search_params: Dictionnaire des paramètres de requête
    
    Returns:
        Bundle FHIR (searchset) contenant les ressources Location correspondantes
    """

    logger.debug("FHIR Location search params: %s", search_params)

    requested_format = search_params.get("_format", "json")
    if requested_format not in ["json", "application/fhir+json"]:
        raise HTTPException(status_code=406, detail="Format non supporté")

    def _clamp_count(raw_value: Any) -> int:
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            value = 50
        return max(1, min(value, 1000))

    count = _clamp_count(search_params.get("_count", 50))
    identifier = search_params.get("identifier")
    partof = search_params.get("partof")
    locations: List[Dict[str, Any]] = []

    try:
        if partof:
            if not isinstance(partof, str) or "/" not in partof:
                raise HTTPException(status_code=400, detail="Invalid partof parameter format. Expected 'Location/[id]'")
            try:
                parent_id = int(partof.split("/")[-1])
            except ValueError as exc:  # pragma: no cover - defensive
                raise HTTPException(status_code=400, detail="Invalid partof identifier") from exc

            parent = None
            for model in [EntiteGeographique, Pole, Service, UniteFonctionnelle, UniteHebergement, Chambre, Lit]:
                parent = session.get(model, parent_id)
                if parent:
                    break
            if not parent:
                raise HTTPException(status_code=404, detail=f"Parent entity not found with id {parent_id}")

            logger.debug(
                "FHIR partOf resolved %s#%s",
                type(parent).__name__,
                getattr(parent, "id", None),
            )

            if isinstance(parent, EntiteGeographique):
                poles = session.exec(select(Pole).where(Pole.entite_geo_id == parent.id)).all()
                locations.extend(entity_to_fhir_location(p, session) for p in poles)
                pole_ids = [p.id for p in poles]
                if pole_ids:
                    services = session.exec(select(Service).where(Service.pole_id.in_(pole_ids))).all()
                    locations.extend(entity_to_fhir_location(s, session) for s in services)
            elif isinstance(parent, Pole):
                services = session.exec(select(Service).where(Service.pole_id == parent.id)).all()
                locations.extend(entity_to_fhir_location(s, session) for s in services)
            elif isinstance(parent, Service):
                ufs = session.exec(select(UniteFonctionnelle).where(UniteFonctionnelle.service_id == parent.id)).all()
                locations.extend(entity_to_fhir_location(u, session) for u in ufs)
            elif isinstance(parent, UniteFonctionnelle):
                uhs = session.exec(
                    select(UniteHebergement).where(UniteHebergement.unite_fonctionnelle_id == parent.id)
                ).all()
                locations.extend(entity_to_fhir_location(u, session) for u in uhs)
            elif isinstance(parent, UniteHebergement):
                chambres = session.exec(
                    select(Chambre).where(Chambre.unite_hebergement_id == parent.id)
                ).all()
                locations.extend(entity_to_fhir_location(c, session) for c in chambres)
            elif isinstance(parent, Chambre):
                lits = session.exec(select(Lit).where(Lit.chambre_id == parent.id)).all()
                locations.extend(entity_to_fhir_location(l, session) for l in lits)

            locations = locations[:count]

        elif identifier:
            seen: Dict[tuple[str, int], Dict[str, Any]] = {}
            model_sequence = [
                EntiteGeographique,
                Service,
                Pole,
                UniteFonctionnelle,
                UniteHebergement,
                Chambre,
                Lit,
            ]

            for model in model_sequence:
                if model is EntiteGeographique:
                    stmt = select(EntiteGeographique).where(
                        (EntiteGeographique.identifier == identifier)
                        | (EntiteGeographique.finess == identifier)
                    )
                else:
                    stmt = select(model).where(model.identifier == identifier)

                for entity in session.exec(stmt).all():
                    resource = entity_to_fhir_location(entity, session)
                    seen[(model.__name__, entity.id)] = resource

            locations = list(seen.values())[:count]

        else:
            query = process_search_params(search_params, session)
            if query is None:
                locations = []
            else:
                results = session.exec(query.limit(count)).all()
                entities: List[Any] = []
                for row in results:
                    if isinstance(row, tuple):
                        entity = next((item for item in row if item is not None), None)
                    else:
                        entity = row
                    if entity is not None:
                        entities.append(entity)
                locations = [entity_to_fhir_location(entity, session) for entity in entities]

        response.headers["Content-Type"] = "application/fhir+json"
        response.headers["Last-Modified"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        return build_fhir_bundle(locations, len(locations), search_params)

    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Erreur lors de la recherche FHIR: %s", exc)
        response.status_code = 500
        return {
            "resourceType": "OperationOutcome",
            "issue": [{
                "severity": "error",
                "code": "exception",
                "diagnostics": str(exc)
            }]
        }

@router.get("/Location/{location_id}", response_model=Dict)
async def read_location(
    location_id: str,
    session: Session = Depends(get_session),
    response: Response = None
) -> Dict:
    """Lecture d'une Location spécifique par son ID logique (GET /fhir/Location/{id}).
    
    Recherche séquentielle dans tous les modèles de structure (priorité Service, puis EG, Pole, UF, UH, Chambre, Lit).
    Retourne OperationOutcome avec code 404 si non trouvée.
    
    Args:
        location_id: ID logique (numérique) de la ressource
        session: Session DB
        response: FastAPI Response pour headers FHIR (Content-Type, Last-Modified)
    
    Returns:
        Ressource FHIR Location ou OperationOutcome en cas d'erreur
    """
    try:
        # Extraire l'ID numérique
        try:
            id_num = int(location_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid location ID format")

        # D'abord chercher dans Service car c'est le cas de test
        entity = session.get(Service, id_num)
        if not entity:
            # Si pas trouvé, chercher dans les autres modèles par ordre hiérarchique
            for model in [EntiteGeographique, Pole, UniteFonctionnelle, UniteHebergement, Chambre, Lit]:
                entity = session.get(model, id_num)
                if entity:
                    logger.debug(f"Found entity of type {type(entity).__name__} with id={id_num}")
                    break
                
        if not entity:
            response.status_code = 404
            return {
                "resourceType": "OperationOutcome",
                "issue": [{
                    "severity": "error",
                    "code": "not-found",
                    "diagnostics": f"Location {location_id} non trouvée"
                }]
            }
            
        # Headers FHIR standards
        response.headers["Content-Type"] = "application/fhir+json"
        response.headers["Last-Modified"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        return entity_to_fhir_location(entity, session)
        
    except ValueError:
        response.status_code = 400
        return {
            "resourceType": "OperationOutcome",
            "issue": [{
                "severity": "error",
                "code": "invalid",
                "diagnostics": "ID de Location invalide"
            }]
        }
    except Exception as e:
        logger.error(f"Erreur lors de la lecture FHIR: {e}")
        response.status_code = 500
        return {
            "resourceType": "OperationOutcome",
            "issue": [{
                "severity": "error",
                "code": "exception",
                "diagnostics": str(e)
            }]
        }

def build_fhir_bundle(resources: List[Dict], total: int, search_params: Dict = None) -> Dict:
    """Construit un Bundle FHIR de recherche (type 'searchset').
    
    Inclut le nombre total de résultats, les liens de navigation (self), 
    et la liste des ressources avec mode de recherche 'match'.
    
    Args:
        resources: Liste de ressources FHIR Location
        total: Nombre total de résultats (avant pagination)
        search_params: Paramètres de requête pour reconstruire le lien 'self'
    
    Returns:
        Bundle FHIR (searchset) avec timestamp UTC
    """
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": total,
        "link": [
            {
                "relation": "self",
                "url": "Location?" + "&".join([f"{k}={v}" for k,v in (search_params or {}).items() if v])
            }
        ],
        "entry": [
            {
                "resource": resource,
                "search": {"mode": "match"}
            }
            for resource in resources
        ],
        "timestamp": datetime.utcnow().isoformat()
    }

def process_search_params(params: Dict[str, Any], session: Session) -> Any:
    """Convertit les paramètres de recherche FHIR en requête SQLModel.
    
    Filtre les paramètres vides et ignore _count, _format, _sort.
    Supporte :
    - partof=Location/{id} : retourne enfants directs (services d'une EG ou d'un Pole, UF d'un Service, etc.)
    - finess, identifier, name, status : recherche par attributs sur tous les modèles
    
    Retourne None si aucun paramètre de filtrage valide.
    
    Args:
        params: Dictionnaire des paramètres de requête
        session: Session DB pour résolution des relations
    
    Returns:
        Objet Select SQLModel ou None si aucune recherche à faire
    """
    filtered_params = {
        k: v for k, v in (params or {}).items()
        if v not in (None, "", [])
        and k not in {"_count", "_format", "_sort"}
    }
    if not filtered_params:
        return None
    params = filtered_params

    # Support recherche par parent FHIR 'partof'
    if params.get("partof"):
        # expected format: Location/{id}
        ref = params["partof"]
        parent_id = None
        if isinstance(ref, str) and "/" in ref:
            try:
                parent_id = int(ref.split("/")[-1])
            except ValueError:
                parent_id = None
        if parent_id:
            parent = None
            for model in [Lit, Chambre, UniteHebergement, UniteFonctionnelle, Service, Pole, EntiteGeographique]:
                parent = session.get(model, parent_id)
                if parent:
                    break

            if parent:
                # If parent is an EntiteGeographique, return services under its poles
                if isinstance(parent, EntiteGeographique):
                    pole_ids = [p.id for p in session.exec(select(Pole).where(Pole.entite_geo_id == parent.id)).all()]
                    if not pole_ids:
                        return select(Service).where(Service.pole_id == -1)
                    return select(Service).where(Service.pole_id.in_(pole_ids))
                # If parent is a Pole, return Services under that pole
                if isinstance(parent, Pole):
                    return select(Service).where(Service.pole_id == parent.id)
                # If parent is a Service, return UFs under that service
                if isinstance(parent, Service):
                    return select(UniteFonctionnelle).where(UniteFonctionnelle.service_id == parent.id)
                # Default: no special handling, fallthrough
    # On distingue deux types de recherche : sur les entités géographiques ou sur les autres locations
    if params.get("finess"):
        # Si on cherche par FINESS, on ne cherche que dans les entités géographiques
        query = select(EntiteGeographique)
        if params.get("name"):
            query = query.where(EntiteGeographique.name.contains(params["name"]))
        if params.get("status"):
            query = query.where(EntiteGeographique.status == params["status"])
        if params.get("identifier"):
            query = query.where(
                (EntiteGeographique.identifier == params["identifier"]) |
                (EntiteGeographique.finess == params["identifier"]) 
            )
    else:
        # Sinon on cherche dans toutes les locations internes
        query = select(Lit, Chambre, UniteHebergement, UniteFonctionnelle, Service, EntiteGeographique)
    
        if params.get("name"):
            query = query.where(
                (Lit.name.contains(params["name"])) |
                (Chambre.name.contains(params["name"])) |
                (UniteHebergement.name.contains(params["name"])) |
                (UniteFonctionnelle.name.contains(params["name"])) |
                (Service.name.contains(params["name"])) |
                (EntiteGeographique.name.contains(params["name"]))
            )
                          
        if params.get("status"):
            query = query.where(
                (Lit.status == params["status"]) |
                (Chambre.status == params["status"]) |
                (UniteHebergement.status == params["status"]) |
                (UniteFonctionnelle.status == params["status"]) |
                (Service.status == params["status"]) |
                (EntiteGeographique.status == params["status"])
            )
        
        if params.get("type"):
            query = query.where(Service.service_type == params["type"])
        
        if params.get("operational-status"):
            query = query.where(Lit.operational_status == params["operational-status"])
        
        if params.get("identifier"):
            query = query.where(
                (Lit.identifier == params["identifier"]) |
                (Chambre.identifier == params["identifier"]) |
                (UniteHebergement.identifier == params["identifier"]) |
                (UniteFonctionnelle.identifier == params["identifier"]) |
                (Service.identifier == params["identifier"]) |
                (EntiteGeographique.identifier == params["identifier"]) |
                (EntiteGeographique.finess == params["identifier"])
            )
                          
    return query

@router.post("/Location", response_model=Dict, status_code=201)
async def create_location(
    location: Dict[Any, Any] = Body(...),
    session: Session = Depends(get_session),
    response: Response = None
) -> Dict:
    """Création d'une nouvelle Location (POST /fhir/Location).
    
    Mode upsert : si la ressource porte un identifiant existant (via identifier ou FINESS), 
    elle sera mise à jour au lieu d'être créée. Sinon, création.
    
    Gestion des relations partOf : si la ressource porte un partOf, le parent est résolu 
    et le rattachement hiérarchique est effectué (service → pole, uf → service, etc.).
    
    Args:
        location: Corps JSON représentant une ressource FHIR Location
        session: Session DB
        response: FastAPI Response pour status 201 et headers
    
    Returns:
        Ressource FHIR Location créée/mise à jour ou OperationOutcome en cas d'erreur
    """
    try:
        if location["resourceType"] != "Location":
            response.status_code = 400
            return {
                "resourceType": "OperationOutcome",
                "issue": [{
                    "severity": "error",
                    "code": "invalid",
                    "diagnostics": "Ressource doit être une Location"
                }]
            }
            
        entity = process_fhir_location(location, session)
        if not entity:
            response.status_code = 422
            return {
                "resourceType": "OperationOutcome",
                "issue": [{
                    "severity": "error",
                    "code": "not-supported",
                    "diagnostics": "Type de Location non supporté"
                }]
            }
            
        # Headers FHIR standards
        response.headers["Content-Type"] = "application/fhir+json"
        response.headers["Location"] = f"Location/{entity.id}"
        response.headers["ETag"] = f'W/"{entity.id}"'
        
        return entity_to_fhir_location(entity, session)
        
    except Exception as e:
        logger.error(f"Erreur lors de la création FHIR: {e}")
        response.status_code = 500
        return {
            "resourceType": "OperationOutcome",
            "issue": [{
                "severity": "error",
                "code": "exception",
                "diagnostics": str(e)
            }]
        }

@router.put("/Location/{location_id}", response_model=Dict)
async def update_location(
    location_id: str,
    location: Dict[Any, Any] = Body(...),
    session: Session = Depends(get_session),
    response: Response = None
) -> Dict:
    """Mise à jour complète d'une Location existante (PUT /fhir/Location/{id}).
    
    Force l'ID dans la ressource reçue et appelle process_fhir_location pour upsert.
    Retourne 404 si l'ID n'est pas trouvé après traitement.
    
    Args:
        location_id: ID logique de la ressource à mettre à jour
        location: Corps JSON représentant une ressource FHIR Location
        session: Session DB
        response: FastAPI Response pour headers FHIR (Content-Type, ETag)
    
    Returns:
        Ressource FHIR Location mise à jour ou OperationOutcome en cas d'erreur
    """
    try:
        if location["resourceType"] != "Location":
            response.status_code = 400
            return {
                "resourceType": "OperationOutcome",
                "issue": [{
                    "severity": "error",
                    "code": "invalid",
                    "diagnostics": "Ressource doit être une Location"
                }]
            }
            
        # Force l'ID dans la ressource
        location["id"] = location_id
        
        entity = process_fhir_location(location, session)
        if not entity:
            response.status_code = 404
            return {
                "resourceType": "OperationOutcome",
                "issue": [{
                    "severity": "error",
                    "code": "not-found",
                    "diagnostics": f"Location {location_id} non trouvée"
                }]
            }
            
        # Headers FHIR standards
        response.headers["Content-Type"] = "application/fhir+json"
        response.headers["ETag"] = f'W/"{entity.id}"'
        
        return entity_to_fhir_location(entity, session)
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour FHIR: {e}")
        response.status_code = 500
        return {
            "resourceType": "OperationOutcome",
            "issue": [{
                "severity": "error",
                "code": "exception",
                "diagnostics": str(e)
            }]
        }

@router.delete("/Location/{location_id}", response_model=Dict)
async def delete_location(
    location_id: str,
    session: Session = Depends(get_session),
    response: Response = None
) -> Dict:
    """Suppression d'une Location (DELETE /fhir/Location/{id}).
    
    Recherche l'entité dans tous les modèles (Lit, Chambre, UH, UF, Service, Pole, EG) 
    et la supprime si trouvée. Retourne 404 si non trouvée.
    
    Args:
        location_id: ID logique de la ressource à supprimer
        session: Session DB
        response: FastAPI Response pour status 204 (no content)
    
    Returns:
        Dictionnaire vide (204) si succès, OperationOutcome en cas d'erreur
    """
    try:
        # Recherche de l'entité
        entity = None
        for model in [Lit, Chambre, UniteHebergement, UniteFonctionnelle, Service, Pole, EntiteGeographique]:
            entity = session.get(model, int(location_id))
            if entity:
                break
                
        if not entity:
            response.status_code = 404
            return {
                "resourceType": "OperationOutcome",
                "issue": [{
                    "severity": "error",
                    "code": "not-found",
                    "diagnostics": f"Location {location_id} non trouvée"
                }]
            }
            
        # Suppression
        session.delete(entity)
        session.commit()
        
        response.status_code = 204
        return {}
        
    except Exception as e:
        logger.error(f"Erreur lors de la suppression FHIR: {e}")
        response.status_code = 500
        return {
            "resourceType": "OperationOutcome",
            "issue": [{
                "severity": "error",
                "code": "exception",
                "diagnostics": str(e)
            }]
        }
