"""Génération d'un Bundle FHIR (Patient + Encounter) pour un dossier.

Cette implémentation POC s'appuie sur des identifiants simples (OID FR
fictifs) et mappe un sous-ensemble des champs Patient/Dossier.
"""

from app.models import Dossier

from datetime import datetime
from typing import Dict, List, Optional
from sqlmodel import Session

def generate_fhir_bundle_for_dossier(dossier: Dossier, session: Optional[Session] = None) -> dict:
    """Génère un Bundle FHIR contenant Patient + Encounter + Location pour un dossier.
    
    Args:
        dossier: Le dossier à convertir
        session: Session SQLModel optionnelle pour charger des données liées
        
    Returns:
        Un dictionnaire représentant le Bundle FHIR
    """
    p = dossier.patient
    
    # Identifiants avec systèmes standardisés
    identifiers = []
    if getattr(p, "external_id", None):
        identifiers.append({
            "system": "urn:oid:1.2.250.1.71.4.2.1", 
            "type": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                    "code": "PI"
                }]
            },
            "value": p.external_id
        })
    if getattr(p, "ssn", None):
        identifiers.append({
            "system": "http://hl7.org/fhir/sid/us-ssn",
            "type": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0203", 
                    "code": "SS"
                }]
            },
            "value": p.ssn
        })

    patient_res = {
        "resourceType": "Patient",
        "id": f"pat-{p.id}",
        "identifier": identifiers,
        "name": [{
            "family": p.family,
            "given": [x for x in [p.given, getattr(p, "middle", None)] if x],
            "prefix": [p.prefix] if getattr(p, "prefix", None) else [],
            "suffix": [p.suffix] if getattr(p, "suffix", None) else [],
        }],
        "telecom": [{"system": "phone", "value": p.phone}] if getattr(p, "phone", None) else [],
        "address": [{
            "line": [p.address] if getattr(p, "address", None) else [],
            "city": getattr(p, "city", None),
            "state": getattr(p, "state", None),
            "postalCode": getattr(p, "postal_code", None),
        }] if getattr(p, "address", None) or getattr(p, "city", None) else [],
        "gender": p.gender,
        "birthDate": p.birth_date,
        "maritalStatus": {"text": p.marital_status} if getattr(p, "marital_status", None) else None,
        "extension": [{"url": "http://example.org/fhir/StructureDefinition/primary-care-provider", "valueString": p.primary_care_provider}] if getattr(p, "primary_care_provider", None) else [],
    }

    # Encounter avec plus de détails
    encounter_res = {
        "resourceType": "Encounter",
        "id": f"enc-{dossier.id}",
        "meta": {
            "profile": ["http://interop-sante.fr/fhir/StructureDefinition/fr-encounter"]
        },
        "identifier": [{
            "system": "urn:oid:1.2.250.1.71.4.2.2",
            "value": str(dossier.id)
        }],
        "status": "finished" if dossier.discharge_time else "in-progress",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "IMP",
            "display": "inpatient encounter"
        },
        "subject": {"reference": f"Patient/pat-{p.id}"},
        "period": {
            "start": dossier.admit_time.isoformat() if dossier.admit_time else None,
            "end": dossier.discharge_time.isoformat() if dossier.discharge_time else None
        }
    }

    # Ajouter les mouvements comme locations
    if hasattr(dossier, "venues") and dossier.venues:
        encounter_res["location"] = []
        for venue in dossier.venues:
            if venue.mouvements:
                for mvt in venue.mouvements:
                    encounter_res["location"].append({
                        "location": {"reference": f"Location/{mvt.location}" if mvt.location else None},
                        "status": "completed" if mvt.when and mvt.when < datetime.utcnow() else "active",
                        "period": {
                            "start": mvt.when.isoformat() if mvt.when else None
                        }
                    })

    # Bundle avec identifiant unique
    bundle = {
        "resourceType": "Bundle",
        "id": f"bundle-{dossier.id}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
        "type": "collection",
        "timestamp": datetime.utcnow().isoformat(),
        "entry": [
            {"resource": patient_res, "fullUrl": f"urn:uuid:pat-{p.id}"},
            {"resource": encounter_res, "fullUrl": f"urn:uuid:enc-{dossier.id}"}
        ]
    }
    
    return bundle
