"""Service de mapping bidirectionnel FHIR Location <-> Entités de structure.

Ce module implémente la conversion entre les ressources FHIR Location et les entités 
de structure hiérarchique (EntiteGeographique, Pole, Service, UniteFonctionnelle, 
UniteHebergement, Chambre, Lit).

Fonctionnalités principales :
- Conversion FHIR → entité avec résolution du type d'entité (via extensions fr-uf-type, 
  physicalType, type)
- Conversion entité → FHIR Location avec profils spécifiques (fr-location, fr-organization-eg)
- Gestion des relations parent-child via Location.partOf
- Support des extensions FHIR personnalisées (responsables, typologie, dates d'ouverture/fermeture)
- Mapping des identifiants FINESS pour les entités géographiques

Point d'entrée pour l'API : via routers/fhir_structure.py (POST /fhir/Location, GET /fhir/Location/{id})
"""
import logging
from typing import Optional, Dict, Any, List, Tuple
from sqlmodel import Session, select
from datetime import datetime
from app.models_structure import (
    EntiteGeographique, Pole, Service, UniteFonctionnelle,
    UniteHebergement, Chambre, Lit,
    LocationStatus, LocationMode, LocationPhysicalType, LocationServiceType
)

logger = logging.getLogger(__name__)


def _iso_to_hl7(date_value: str) -> Optional[str]:
    """Convertit une date ISO (YYYY-MM-DD[THH:MM:SS]) en format HL7 (YYYYMMDDHHmmss).
    
    Args:
        date_value: Date au format ISO 8601 (ex: 2024-01-15 ou 2024-01-15T10:30:00)
    
    Returns:
        Date au format HL7 (ex: 20240115 ou 20240115103000), None si invalide
    """
    if not date_value:
        return None
    try:
        dt = datetime.fromisoformat(date_value)
    except Exception:
        return date_value.replace("-", "").replace(":", "").replace("T", "").replace(".", "")
    if dt.hour or dt.minute or dt.second:
        return dt.strftime("%Y%m%d%H%M%S")
    return dt.strftime("%Y%m%d")


def _hl7_to_iso(date_value: Optional[str]) -> Optional[str]:
    """Convertit une date HL7 (YYYYMMDDHHmmss) en isoformat pour FHIR.
    
    Supporte les formats : YYYYMMDDHHmmss (14 car), YYYYMMDDHHmm (12 car), YYYYMMDD (8 car).
    
    Args:
        date_value: Date au format HL7 (ex: 20240115 ou 20240115103000)
    
    Returns:
        Date ISO 8601 (ex: 2024-01-15T10:30:00), None si non parsable
    """
    if not date_value:
        return None
    value = date_value.strip()
    for fmt, length in (("%Y%m%d%H%M%S", 14), ("%Y%m%d%H%M", 12), ("%Y%m%d", 8)):
        try:
            dt = datetime.strptime(value[:length], fmt)
            return dt.isoformat()
        except Exception:
            continue
    return None


def _physical_from_code(code: Optional[str], default: LocationPhysicalType) -> LocationPhysicalType:
    """Mappe un code de type physique en enum LocationPhysicalType, avec défaut en cas d'inconnu.
    
    Args:
        code: Code du physicalType (ex: 'area', 'wi', 'ro', 'bd')
        default: Valeur par défaut si code est None ou invalide
    
    Returns:
        Enum LocationPhysicalType correspondant
    """
    if not code:
        return default
    try:
        return LocationPhysicalType(code)
    except ValueError:
        return default

def fhir_location_to_entity(location: Dict[Any, Any], session: Session) -> tuple[Optional[Any], Optional[str]]:
    """Convertit une ressource FHIR Location en entité de structure appropriée.
    
    Logique de dispatching :
    - Présence d'un identifiant FINESS → EntiteGeographique
    - physicalType='area' sans .type + extension fr-uf-type → UniteFonctionnelle
    - physicalType='area' sans .type ni extension fr-uf-type → Pole
    - Location.type présent (coding fr-service-type ou HL7 service-type) → Service
    - physicalType='wi' → UniteHebergement
    - physicalType='ro' → Chambre
    - physicalType='bd' → Lit
    
    Gestion des relations :
    - partOf (Location.partOf.reference) → parent_ref (id de l'entité parente)
    - Pour Service sans pôle existant : création automatique d'un Pole associé à l'EG parent
    
    Args:
        location: Dictionnaire représentant une ressource FHIR Location
        session: Session SQLModel pour requêtes et insertions
    
    Returns:
        Tuple (entité créée ou None, parent_ref ou None)
    """
    
    # Détermine le type d'entité basé sur les tags et le type physique
    extensions_raw = location.get("extension") or []
    if isinstance(extensions_raw, dict):
        extensions = [extensions_raw]
    else:
        extensions = list(extensions_raw)

    def _get_extension(url: str) -> Optional[Dict]:
        return next((ext for ext in extensions if isinstance(ext, dict) and ext.get("url") == url), None)

    physical_type = next((ext.get("valueCode") for ext in extensions
                         if isinstance(ext, dict) and ext.get("url") == "http://hl7.org/fhir/StructureDefinition/location-physical-type"), None)
    if not physical_type:
        physical_type = next(
            (coding.get("code") for coding in location.get("physicalType", {}).get("coding", []) if coding.get("code")),
            None
        )
    
    # Cherchons d'abord un identifiant FINESS, s'il n'existe pas on prend le premier identifiant disponible
    finess = next((id["value"] for id in location.get("identifier", [])
                  if id.get("system") == "http://finess.sante.gouv.fr"), None)
    
    identifier = finess  # On utilise le FINESS comme identifiant métier pour une EG

    if not identifier:
        # Si pas de FINESS, prend n'importe quel identifiant disponible
        identifier = next((id["value"] for id in location.get("identifier", [])), None)
    if not identifier:
        identifier = location.get("id") or location.get("name") or ""
    
    # Récupère le FINESS séparément pour le champ spécifique
    finess = next((id["value"] for id in location.get("identifier", [])
                  if id.get("system") == "http://finess.sante.gouv.fr"), None)
    
    # Mapping commun
    common_data = {
        "name": location.get("name"),
        "description": location.get("description"),
        "status": LocationStatus(location.get("status", "active")),
        "mode": LocationMode(location.get("mode", "instance")),
        "identifier": identifier,
    }
    
    # Dates communes
    for date_field, fhir_url in [
        ("opening_date", "http://example.org/fhir/StructureDefinition/opening-date"),
        ("activation_date", "http://example.org/fhir/StructureDefinition/activation-date"),
        ("closing_date", "http://example.org/fhir/StructureDefinition/closing-date"),
        ("deactivation_date", "http://example.org/fhir/StructureDefinition/deactivation-date")
    ]:
        value = next((ext["valueDateTime"] for ext in location.get("extension", [])
                     if ext["url"] == fhir_url), None)
        if value:
            common_data[date_field] = _iso_to_hl7(value)
    
    # Typologie spécifique (extension custom)
    location_type_ext = next(
        (ext.get("valueString") for ext in location.get("extension", [])
         if ext.get("url") == "https://medbridge.com/StructureFhir/location-type"),
        None
    )

    manager_ext = next(
        (ext for ext in location.get("extension", [])
         if ext.get("url") == "https://medbridge.com/StructureFhir/location-manager"),
        None
    )
    manager_data: Dict[str, Optional[str]] = {}
    if manager_ext:
        def _m_ext(url: str) -> Optional[str]:
            return next(
                (sub_ext.get("valueString") for sub_ext in manager_ext.get("extension", [])
                 if sub_ext.get("url") == url),
                None,
            )

        manager_data = {
            "responsible_id": _m_ext("id"),
            "responsible_name": _m_ext("name"),
            "responsible_firstname": _m_ext("firstname"),
            "responsible_rpps": _m_ext("rpps"),
            "responsible_adeli": _m_ext("adeli"),
            "responsible_specialty": _m_ext("specialty"),
        }
    
    # Référence parent éventuelle (partOf) — doit être calculée avant de retourner
    parent_ref = None
    part_of = location.get("partOf")
    if isinstance(part_of, dict):
        ref = part_of.get("reference")
        if isinstance(ref, str):
            # Format attendu: "Location/[id]"
            try:
                parent_ref = int(ref.split("/")[1]) if "/" in ref else None
            except (ValueError, IndexError):
                logger.warning(f"Invalid partOf reference format: {ref}")
                parent_ref = None

    # Gestion par type
    if finess:  # C'est une entité géographique
        entity = EntiteGeographique(
            **common_data,
            finess=finess,
            address_text=location.get("address", {}).get("text"),
            address_line1=location.get("address", {}).get("line", [""])[0] if location.get("address", {}).get("line") else None,
            address_city=location.get("address", {}).get("city"),
            address_postalcode=location.get("address", {}).get("postalCode"),
            address_country=location.get("address", {}).get("country", "FR"),
            latitude=location.get("position", {}).get("latitude"),
            longitude=location.get("position", {}).get("longitude"),
            type=location_type_ext,
            **manager_data,
        )
        logger.debug(f"Created EntiteGeographique: id={entity.id}, name={entity.name}, parent_ref={parent_ref}")
        return entity, parent_ref
    
    if physical_type == "area" and "type" not in location:  # Pôle
        return (
            Pole(**common_data, physical_type=_physical_from_code(physical_type, LocationPhysicalType.AREA)),
            parent_ref,
        )
        
    elif location.get("type") is not None:  # Service
        type_component = location.get("type")
        if isinstance(type_component, list):
            coding_candidates = type_component[0].get("coding", []) if type_component else []
        elif isinstance(type_component, dict):
            coding_candidates = type_component.get("coding", [])
        else:
            coding_candidates = []
        # Accept service type codings from either the French code system or the HL7 terminology
        service_type = next((coding.get("code") for coding in coding_candidates
                           if coding.get("system") in (
                               "http://interop-sante.fr/fhir/CodeSystem/fr-service-type",
                               "http://terminology.hl7.org/CodeSystem/service-type",
                           )), None)
        logger.debug(f"Processing service with type={service_type}, parent_ref={parent_ref}")
        
        if not service_type:
            return (None, parent_ref)
        # Normalize to expected enum value (lowercase)
        service_type = service_type.lower()
            
        # Si on a un parent_ref, trouver le pôle parent
        pole = None
        if parent_ref:
            parent = session.get(EntiteGeographique, parent_ref)
            if parent:
                # Créer ou récupérer un pôle pour ce parent
                poles = session.exec(select(Pole).where(Pole.entite_geo_id == parent.id)).all()
                if poles:
                    pole = poles[0]
                else:
                    pole = Pole(
                        name=f"Pôle {parent.name}",
                        entite_geo_id=parent.id,
                        identifier=f"POLE_{parent.id}",
                        status="active",
                        mode="instance",
                        physical_type=LocationPhysicalType.AREA
                    )
                    session.add(pole)
                    session.flush()
                    logger.debug(f"Created new Pole: id={pole.id}, name={pole.name}")
            
        service_data = {
            **common_data,
            "physical_type": _physical_from_code(physical_type, LocationPhysicalType.SI),
            "service_type": LocationServiceType(service_type),
            "pole_id": pole.id if pole else None
        }
        logger.debug(f"Service data: {service_data}")
        
        # Typologie
        service_data["typology"] = next(
            (ext.get("valueString") for ext in extensions if isinstance(ext, dict)
             and ext.get("url") == "http://example.org/fhir/StructureDefinition/service-typology"),
            None)

        # Chercher l'extension du responsable 
        responsible = _get_extension("http://example.org/fhir/StructureDefinition/service-responsible")

        if responsible:
            # Helper pour extraire les sous-extensions
            def get_ext(exts, url):
                return next((e["valueString"] for e in exts if e["url"] == url), None)
                
            service_data.update({
                "responsible_id": get_ext(responsible["extension"], "id"),
                "responsible_name": get_ext(responsible["extension"], "name"),
                "responsible_firstname": get_ext(responsible["extension"], "firstname"),
                "responsible_rpps": get_ext(responsible["extension"], "rpps"),
                "responsible_adeli": get_ext(responsible["extension"], "adeli"),
                "responsible_specialty": get_ext(responsible["extension"], "specialty")
            })
            
        return (
            Service(**service_data),
            parent_ref,
        )
            
    elif physical_type == "area" and _get_extension("http://interop-sante.fr/fhir/StructureDefinition/fr-uf-type"):  # UF
        uf_ext = _get_extension("http://interop-sante.fr/fhir/StructureDefinition/fr-uf-type")
        uf_type = uf_ext.get("valueCode") if uf_ext else None
        if uf_type:
            return (
                UniteFonctionnelle(
                **common_data,
                physical_type=_physical_from_code(physical_type, LocationPhysicalType.AREA),
                uf_type=uf_type,
                ),
                parent_ref,
            )

    elif physical_type == "wi":  # Unité d'hébergement
        return (
            UniteHebergement(
            **common_data,
            physical_type=_physical_from_code(physical_type, LocationPhysicalType.WI),
            etage=next((ext.get("valueString") for ext in extensions
                       if ext.get("url") == "http://example.org/fhir/StructureDefinition/floor"), None),
            aile=next((ext.get("valueString") for ext in extensions
                      if ext.get("url") == "http://example.org/fhir/StructureDefinition/wing"), None),
            ),
            parent_ref,
        )

    elif physical_type == "ro":  # Chambre
        return (
            Chambre(
            **common_data,
            physical_type=_physical_from_code(physical_type, LocationPhysicalType.RO),
            type_chambre=next((ext.get("valueCode") for ext in extensions
                             if ext.get("url") == "http://example.org/fhir/StructureDefinition/room-type"), "simple"),
            gender_usage=location.get("physicalType", {}).get("text"),
            ),
            parent_ref,
        )
        
    elif physical_type == "bd":  # Lit
        return (
            Lit(
            **common_data,
            physical_type=_physical_from_code(physical_type, LocationPhysicalType.BD),
            operational_status=location.get("operationalStatus", {}).get("coding", [{}])[0].get("code", "libre")
            ),
            parent_ref,
        )

    return (None, parent_ref)

def entity_to_fhir_location(entity: Any, session: Session) -> Dict[Any, Any]:
    """Convertit une entité de structure en ressource FHIR Location.
    
    Génère une Location conforme au profil fr-location avec :
    - Attributs communs : id, name, status, mode, identifier (OID 1.2.250.1.71.4.2.2)
    - Extensions de dates : opening-date, activation-date, closing-date, deactivation-date
    - Spécificités par type :
      - EntiteGeographique : FINESS identifier, adresse, position GPS, manager extension
      - Pole : physicalType=area
      - Service : type avec fr-service-type, responsable extension
      - UniteFonctionnelle : physicalType=area + fr-uf-type extension
      - UniteHebergement : physicalType=wi + floor/wing extensions
      - Chambre : physicalType=ro + room-type extension
      - Lit : physicalType=bd + operationalStatus
    - partOf : référence l'entité parente (EG pour Pole, Pole pour Service, etc.)
    
    Args:
        entity: Instance de EntiteGeographique, Pole, Service, UniteFonctionnelle, 
                UniteHebergement, Chambre ou Lit
        session: Session SQLModel pour requêtes de parentalité
    
    Returns:
        Dictionnaire représentant une ressource FHIR Location
    """
    
    # Base commune
    location = {
        "resourceType": "Location",
        "id": str(entity.id),
        "meta": {
            "profile": ["http://interop-sante.fr/fhir/StructureDefinition/fr-location"]
        },
        "name": entity.name,
        "status": entity.status,
        "mode": entity.mode,
        "identifier": [{
            "system": "urn:oid:1.2.250.1.71.4.2.2",
            "value": entity.identifier
        }]
    }
    
    # Dates (commune à tous les types)
    if entity.opening_date:
        iso = _hl7_to_iso(entity.opening_date)
        if iso:
            location.setdefault("extension", []).append({
                "url": "http://example.org/fhir/StructureDefinition/opening-date",
                "valueDateTime": iso
            })
    if entity.activation_date:
        iso = _hl7_to_iso(entity.activation_date)
        if iso:
            location.setdefault("extension", []).append({
                "url": "http://example.org/fhir/StructureDefinition/activation-date",
                "valueDateTime": iso
            }) 
    if entity.closing_date:
        iso = _hl7_to_iso(entity.closing_date)
        if iso:
            location.setdefault("extension", []).append({
                "url": "http://example.org/fhir/StructureDefinition/closing-date", 
                "valueDateTime": iso
            })
    if entity.deactivation_date:
        iso = _hl7_to_iso(entity.deactivation_date)
        if iso:
            location.setdefault("extension", []).append({
                "url": "http://example.org/fhir/StructureDefinition/deactivation-date",
                "valueDateTime": iso
            })
    
    if entity.description:
        location["description"] = entity.description
        
    # Spécificités par type
    if isinstance(entity, EntiteGeographique):
        location["meta"]["profile"].append("http://interop-sante.fr/fhir/StructureDefinition/fr-organization-eg")
        location["identifier"].append({
            "system": "http://finess.sante.gouv.fr",
            "value": entity.finess
        })
        if entity.address_text or entity.address_line1:
            location["address"] = {
                "text": entity.address_text,
                "line": [entity.address_line1] if entity.address_line1 else [],
                "city": entity.address_city,
                "postalCode": entity.address_postalcode,
                "country": entity.address_country or "FR"
            }
        if entity.latitude and entity.longitude:
            location["position"] = {
                "latitude": entity.latitude,
                "longitude": entity.longitude
            }
        if entity.type:
            location.setdefault("extension", []).append({
                "url": "https://medbridge.com/StructureFhir/location-type",
                "valueString": entity.type
            })
        if any([entity.responsible_id, entity.responsible_name, entity.responsible_firstname,
                entity.responsible_rpps, entity.responsible_adeli, entity.responsible_specialty]):
            manager_ext = {
                "url": "https://medbridge.com/StructureFhir/location-manager",
                "extension": []
            }
            if entity.responsible_id:
                manager_ext["extension"].append({"url": "id", "valueString": entity.responsible_id})
            if entity.responsible_name:
                manager_ext["extension"].append({"url": "name", "valueString": entity.responsible_name})
            if entity.responsible_firstname:
                manager_ext["extension"].append({"url": "firstname", "valueString": entity.responsible_firstname})
            if entity.responsible_rpps:
                manager_ext["extension"].append({"url": "rpps", "valueString": entity.responsible_rpps})
            if entity.responsible_adeli:
                manager_ext["extension"].append({"url": "adeli", "valueString": entity.responsible_adeli})
            if entity.responsible_specialty:
                manager_ext["extension"].append({"url": "specialty", "valueString": entity.responsible_specialty})
            location.setdefault("extension", []).append(manager_ext)
            
    elif isinstance(entity, Pole):
        location["physicalType"] = {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/location-physical-type",
                "code": "area"
            }]
        }
        
    elif isinstance(entity, Service):
        location["type"] = [{
            "coding": [{
                "system": "http://interop-sante.fr/fhir/CodeSystem/fr-service-type",
                "code": entity.service_type
            }]
        }]
        
        # Responsable du service
        if entity.responsible_id:
            responsible = {
                "url": "http://example.org/fhir/StructureDefinition/service-responsible",
                "extension": [
                    {
                        "url": "id",
                        "valueString": entity.responsible_id
                    },
                    {
                        "url": "name",
                        "valueString": entity.responsible_name
                    }
                ]
            }
            if entity.responsible_firstname:
                responsible["extension"].append({
                    "url": "firstname",
                    "valueString": entity.responsible_firstname
                })
            if entity.responsible_rpps:
                responsible["extension"].append({
                    "url": "rpps",
                    "valueString": entity.responsible_rpps  
                })
            if entity.responsible_adeli:
                responsible["extension"].append({
                    "url": "adeli",
                    "valueString": entity.responsible_adeli
                })
            if entity.responsible_specialty:
                responsible["extension"].append({
                    "url": "specialty",
                    "valueString": entity.responsible_specialty
                })
            location.setdefault("extension", []).append(responsible)
            
        # Typologie du service
        if entity.typology:
            location.setdefault("extension", []).append({
                "url": "http://example.org/fhir/StructureDefinition/service-typology",
                "valueString": entity.typology
            })
        
    elif isinstance(entity, UniteFonctionnelle):
        location["meta"]["profile"].append("http://interop-sante.fr/fhir/StructureDefinition/fr-location-uf")
        # Support multi-activité: répéter l'extension fr-uf-type pour chaque activité
        uf_extensions = []
        try:
            # Relation many-to-many (si présente)
            for act in getattr(entity, "activities", []) or []:
                code = getattr(act, "code", None)
                if code:
                    uf_extensions.append({
                        "url": "http://interop-sante.fr/fhir/StructureDefinition/fr-uf-type",
                        "valueCode": code
                    })
        except Exception:
            pass

        # Fallback sur l'ancien champ simple uf_type si aucune activité liée
        if not uf_extensions and getattr(entity, "uf_type", None):
            uf_extensions.append({
                "url": "http://interop-sante.fr/fhir/StructureDefinition/fr-uf-type",
                "valueCode": entity.uf_type
            })

        if uf_extensions:
            location.setdefault("extension", []).extend(uf_extensions)
        
    elif isinstance(entity, UniteHebergement):
        location["physicalType"] = {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/location-physical-type",
                "code": "wi"
            }]
        }
        if entity.etage:
            location.setdefault("extension", []).append({
                "url": "http://example.org/fhir/StructureDefinition/floor",
                "valueString": entity.etage
            })
        if entity.aile:
            location.setdefault("extension", []).append({
                "url": "http://example.org/fhir/StructureDefinition/wing",
                "valueString": entity.aile
            })
            
    elif isinstance(entity, Chambre):
        location["physicalType"] = {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/location-physical-type",
                "code": "ro"
            }]
        }
        location.setdefault("extension", []).append({
            "url": "http://example.org/fhir/StructureDefinition/room-type",
            "valueCode": entity.type_chambre
        })
        if entity.gender_usage:
            location["physicalType"]["text"] = entity.gender_usage
            
    elif isinstance(entity, Lit):
        location["physicalType"] = {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/location-physical-type",
                "code": "bd"
            }]
        }
        if getattr(entity, "operational_status", None):
            location["operationalStatus"] = {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0116",
                    "code": entity.operational_status
                }]
            }
            
    return location

def process_fhir_location(location: Dict[Any, Any], session: Session) -> Optional[Any]:
    """Traite une ressource FHIR Location reçue : conversion + persistance + gestion des relations parent.
    
    Pipeline :
    1. Conversion FHIR → entité via fhir_location_to_entity()
    2. Recherche entité existante (par id FHIR, puis par identifier métier ou FINESS)
    3. Si existe : mise à jour des champs ; sinon : préparation pour création
    4. Résolution de la référence parent (partOf) et rattachement selon la hiérarchie :
       - Service → Pole (création automatique si parent=EG)
       - UniteFonctionnelle → Service
       - UniteHebergement → UniteFonctionnelle
       - Chambre → UniteHebergement
       - Lit → Chambre
    5. Persistance (commit) si nouvel objet
    
    Args:
        location: Dictionnaire représentant une ressource FHIR Location
        session: Session SQLModel pour requêtes et commits
    
    Returns:
        Entité créée ou mise à jour, None si la conversion a échoué
    """
    
    entity, parent_ref = fhir_location_to_entity(location, session)
    if entity:
        # Si l'entité a un identifiant métier, on cherche si elle existe déjà
        existing = None
        persisted = False
        # 1. On tente d'abord une résolution directe par identifiant logique (id)
        resource_id = location.get("id")
        if resource_id:
            try:
                existing = session.get(type(entity), int(resource_id))
            except (TypeError, ValueError):
                existing = None

        if entity.identifier:
            if isinstance(entity, EntiteGeographique):
                # Priorité à la recherche par id ; si non trouvé, recherche par FINESS
                if existing is None:
                    existing = session.exec(
                        select(EntiteGeographique).where(
                            (EntiteGeographique.finess == entity.finess) |
                            (EntiteGeographique.identifier == entity.identifier)
                        )
                    ).first()
            else:
                # Cherche par type et identifiant (si pas déjà trouvé via id)
                if existing is None:
                    entity_type = type(entity)
                    existing = session.exec(
                        select(entity_type).where(entity_type.identifier == entity.identifier)
                    ).first()

        if existing:
            # Mise à jour des champs, en excluant les champs spéciaux
            for key, value in entity.__dict__.items():
                if key not in ("id", "identifier", "__class__", "_sa_instance_state") and value is not None:
                    setattr(existing, key, value)
            session.add(existing)
            session.commit()
            session.refresh(existing)
            entity = existing
            persisted = True
        else:
            # Nouveau: on retarde la persistance jusqu'à avoir lié le parent
            persisted = False

        # Gestion des relations partOf (accepte int ou reference FHIR)
        if parent_ref:
            parent_id = None
            if isinstance(parent_ref, str) and parent_ref.startswith("Location/"):
                try:
                    parent_id = int(parent_ref.split("/")[-1])
                except ValueError:
                    parent_id = None
            elif isinstance(parent_ref, int):
                parent_id = parent_ref

            if parent_id:
                parent = None
                # Recherche du parent potentiel (ordre décroissant de granularité)
                for model in [Lit, Chambre, UniteHebergement, UniteFonctionnelle, Service, Pole, EntiteGeographique]:
                    parent = session.get(model, parent_id)
                    if parent:
                        break
                if parent:
                    # Service parent mapping: prefer Pole. If parent is an EntiteGeographique,
                    # create or reuse a Pole under that Entite and attach the Service to it.
                    if isinstance(entity, Service):
                        if isinstance(parent, Pole):
                            entity.pole_id = parent.id
                        elif isinstance(parent, EntiteGeographique):
                            # Try to reuse an existing Pole for this EntiteGeographique
                            existing_pole = session.exec(
                                select(Pole).where(Pole.entite_geo_id == parent.id)
                            ).first()
                            if existing_pole:
                                entity.pole_id = existing_pole.id
                            else:
                                # Create a default pole representing the parent EG
                                pole_identifier = f"{parent.identifier}-POLE" if getattr(parent, 'identifier', None) else f"POLE-{parent.id}"
                                pole = Pole(
                                    identifier=pole_identifier,
                                    name=f"Pôle de {parent.name}",
                                    physical_type=LocationPhysicalType.AREA,
                                    entite_geo_id=parent.id,
                                    status=parent.status,
                                    mode=parent.mode,
                                )
                                session.add(pole)
                                session.commit()
                                session.refresh(pole)
                                entity.pole_id = pole.id
                    elif isinstance(entity, UniteFonctionnelle) and isinstance(parent, Service):
                        entity.service_id = parent.id
                    elif isinstance(entity, UniteHebergement) and isinstance(parent, UniteFonctionnelle):
                        entity.unite_fonctionnelle_id = parent.id
                    elif isinstance(entity, Chambre) and isinstance(parent, UniteHebergement):
                        entity.unite_hebergement_id = parent.id
                    elif isinstance(entity, Lit) and isinstance(parent, Chambre):
                        entity.chambre_id = parent.id

        # Persister l'entité si elle n'existait pas
        if not persisted:
            logger.debug(f'Persisting new entity {type(entity).__name__} identifier={getattr(entity, "identifier", None)} pole_id={getattr(entity, "pole_id", None)}')
            session.add(entity)
            session.commit()
            session.refresh(entity)
            logger.debug(f'Persisted entity id={entity.id} pole_id={getattr(entity, "pole_id", None)}')

        return entity

    return None
