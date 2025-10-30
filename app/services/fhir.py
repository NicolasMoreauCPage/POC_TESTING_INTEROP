from app.models import Dossier

def generate_fhir_bundle_for_dossier(dossier: Dossier) -> dict:
    # Construit un petit Bundle FHIR (Patient + Encounter).
    p = dossier.patient
    patient_res = {
        "resourceType": "Patient",
        "id": f"pat-{p.id}",
        "identifier": [{"system": "urn:extid", "value": p.external_id}],
        "name": [{"family": p.family, "given": [p.given]}],
        "gender": p.gender,
        "birthDate": p.birth_date,
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
