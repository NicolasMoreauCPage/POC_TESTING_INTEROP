from app.models import Dossier

def generate_fhir_bundle_for_dossier(dossier: Dossier) -> dict:
    # Construit un petit Bundle FHIR (Patient + Encounter).
    p = dossier.patient
    identifiers = []
    if getattr(p, "external_id", None):
        identifiers.append({"system": "urn:extid", "value": p.external_id})
    if getattr(p, "ssn", None):
        identifiers.append({"system": "urn:ssn", "value": p.ssn})

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

    encounter_res = {
        "resourceType": "Encounter",
        "id": f"enc-{dossier.id}",
        "subject": {"reference": f"Patient/pat-{p.id}"},
        "status": "finished" if dossier.discharge_time else "in-progress",
        "period": {
            "start": dossier.admit_time.isoformat() if dossier.admit_time else None,
            "end": dossier.discharge_time.isoformat() if dossier.discharge_time else None,
        },
    }

    bundle = {"resourceType": "Bundle", "type": "collection", "entry": [{"resource": patient_res}, {"resource": encounter_res}]}
    return bundle
