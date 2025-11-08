import logging
from typing import Optional, List, Dict, Any
from sqlmodel import Session, select
from app.models_structure import Pole, Service, UniteFonctionnelle, UniteHebergement, Chambre, Lit
from app.models_structure_fhir import EntiteGeographique

logger = logging.getLogger(__name__)

FHIR_BASE_URL = "http://example.org/fhir"  # TODO: externalize

def _location_resource(entity: Any, resource_type: str = "Location") -> Dict[str, Any]:
    """Map a structure entity to a minimal FHIR Location resource."""
    return {
        "resourceType": resource_type,
        "id": entity.identifier,
        "status": "active",
        "name": entity.name,
        "extension": [
            {
                "url": f"{FHIR_BASE_URL}/StructureDefinition/isVirtual",
                "valueBoolean": getattr(entity, "is_virtual", False)
            }
        ],
    }

def generate_fhir_bundle_structure(session: Session, eg_identifier: Optional[str] = None, collapse_virtual: bool = True) -> Dict[str, Any]:
    """Generate a FHIR Bundle of Location resources reflecting current DB structure.

    collapse_virtual: if True, do not emit virtual poles/services; services under virtual poles
    are attached directly to their EntiteGeographique via partOf.
    """
    # Collect entities
    if eg_identifier:
        eg = session.exec(select(EntiteGeographique).where(EntiteGeographique.identifier == eg_identifier)).first()
        if not eg:
            logger.warning("EG not found for FHIR export: %s", eg_identifier)
            return {"resourceType": "Bundle", "type": "collection", "entry": []}
        egs = [eg]
        poles = eg.poles
        services = [svc for p in poles for svc in p.services]
        ufs = [uf for s in services for uf in uf for uf in s.unites_fonctionnelles]  # intentionally simplified
    else:
        egs = session.exec(select(EntiteGeographique)).all()
        poles = session.exec(select(Pole)).all()
        services = session.exec(select(Service)).all()
        ufs = session.exec(select(UniteFonctionnelle)).all()
    uhs = session.exec(select(UniteHebergement)).all()
    chambres = session.exec(select(Chambre)).all()
    lits = session.exec(select(Lit)).all()

    entries: List[Dict[str, Any]] = []

    # EG
    for eg in egs:
        loc = _location_resource(eg)
        loc["type"] = [{"text": "EntiteGeographique"}]
        entries.append({"resource": loc})

    virtual_pole_prefix = "VIRTUAL-POLE-"
    virtual_service_prefix = "VIRTUAL-SERVICE-"

    # Poles
    for pole in poles:
        if collapse_virtual and pole.is_virtual:
            continue
        loc = _location_resource(pole)
        loc["type"] = [{"text": "Pole"}]
        if pole.entite_geo:
            loc["partOf"] = {"reference": f"Location/{pole.entite_geo.identifier}"}
        entries.append({"resource": loc})

    # Services
    for service in services:
        if collapse_virtual and service.is_virtual:
            # attach children (UF) later directly to EG or skip; here we still export service? We skip.
            continue
        loc = _location_resource(service)
        loc["type"] = [{"text": "Service"}]
        if collapse_virtual and service.pole and service.pole.is_virtual and service.pole.entite_geo:
            loc["partOf"] = {"reference": f"Location/{service.pole.entite_geo.identifier}"}
        elif service.pole:
            loc["partOf"] = {"reference": f"Location/{service.pole.identifier}"}
        entries.append({"resource": loc})

    # TODO: add UF/UH/CH/LIT similarly if needed; skipped for brevity vs current source file

    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": entries
    }
    return bundle
