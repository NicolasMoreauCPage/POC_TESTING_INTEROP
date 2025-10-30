from app.models import Patient, Dossier, Venue, Mouvement
from app.models_endpoints import SystemEndpoint, MessageLog
from app.services.fhir import generate_fhir_bundle_for_dossier
from app.services.mllp import frame_hl7
from app.services.fhir_transport import send_fhir
from app.services.mllp import send_mllp
from sqlmodel import Session
from typing import Literal

def generate_pam_hl7(entity, entity_type: Literal["patient","dossier","venue","mouvement"], session: Session) -> str:
    # POC: use existing generate_pam_message if available, else build a minimal HL7 string
    # For real use, map fields per IHE PAM spec
    if entity_type == "patient":
        # Minimal ADT^A04
        return f"MSH|^~\\&|POC|HOSP|EXT|HOSP|{entity.birth_date or ''}||ADT^A04|{entity.id}|P|2.5\nPID|||{entity.patient_seq}||{entity.family}^{entity.given}||{entity.birth_date}||{entity.gender}"
    if entity_type == "dossier":
        # Minimal ADT^A01
        return f"MSH|^~\\&|POC|HOSP|EXT|HOSP|{entity.admit_time or ''}||ADT^A01|{entity.id}|P|2.5\nPID|||{entity.patient_id}|||||\nPV1|||{entity.uf_responsabilite}||{entity.admit_time}"
    if entity_type == "venue":
        # Minimal Z99 event
        return f"MSH|^~\\&|POC|HOSP|EXT|HOSP|{entity.start_time or ''}||Z99^Z99|{entity.id}|P|2.5\nZ99|VENUE|{entity.venue_seq}|{entity.code}|{entity.label}"
    if entity_type == "mouvement":
        # Minimal ADT^A02
        return f"MSH|^~\\&|POC|HOSP|EXT|HOSP|{entity.when or ''}||ADT^A02|{entity.id}|P|2.5\nPV1|||{entity.location}||{entity.when}"
    return ""

def generate_fhir(entity, entity_type: Literal["patient","dossier","venue","mouvement"], session: Session):
    # Use existing generator for Dossier, else minimal Patient resource
    if entity_type == "dossier":
        return generate_fhir_bundle_for_dossier(entity)
    if entity_type == "patient":
        identifiers = [{"value": str(entity.patient_seq)}]
        if getattr(entity, "ssn", None):
            identifiers.append({"system": "urn:ssn", "value": entity.ssn})
        name = {"family": entity.family, "given": [entity.given]}
        if getattr(entity, "middle", None):
            name["given"].append(entity.middle)
        if getattr(entity, "prefix", None):
            name["prefix"] = [entity.prefix]
        if getattr(entity, "suffix", None):
            name["suffix"] = [entity.suffix]
        patient_res = {
            "resourceType": "Patient",
            "id": str(entity.id),
            "identifier": identifiers,
            "name": [name],
            "gender": entity.gender,
            "birthDate": entity.birth_date,
        }
        if getattr(entity, "phone", None):
            patient_res.setdefault("telecom", []).append({"system": "phone", "value": entity.phone})
        if getattr(entity, "address", None) or getattr(entity, "city", None):
            patient_res.setdefault("address", []).append({
                "line": [getattr(entity, "address", None)] if getattr(entity, "address", None) else [],
                "city": getattr(entity, "city", None),
                "state": getattr(entity, "state", None),
                "postalCode": getattr(entity, "postal_code", None),
            })
        if getattr(entity, "primary_care_provider", None):
            patient_res.setdefault("extension", []).append({"url": "http://example.org/fhir/StructureDefinition/primary-care-provider", "valueString": entity.primary_care_provider})
        return patient_res
    # For venue/mouvement, just wrap as Observation for POC
    return {
        "resourceType": "Observation",
        "id": str(entity.id),
        "status": "final",
        "code": {"text": entity_type},
        "valueString": str(entity),
    }

def emit_to_senders(entity, entity_type: Literal["patient","dossier","venue","mouvement"], session: Session):
    # Find all endpoints with role=sender
    from sqlmodel import select
    eps = session.exec(select(SystemEndpoint).where(SystemEndpoint.role == "sender")).all()
    hl7_msg = generate_pam_hl7(entity, entity_type, session)
    fhir_msg = generate_fhir(entity, entity_type, session)
    sent_any = False
    # HL7 MLLP
    for ep in eps:
        if ep.kind == "MLLP":
            try:
                send_mllp(ep.host, ep.port, frame_hl7(hl7_msg))
                status = "sent"
            except Exception as e:
                print(f"[emit_to_senders] MLLP send failed: {e}")
                status = "error"
            log = MessageLog(direction="out", kind="MLLP", endpoint_id=ep.id, payload=hl7_msg, ack_payload="", status=status)
            session.add(log)
            sent_any = True
    # FHIR REST
    for ep in eps:
        if ep.kind == "FHIR":
            try:
                send_fhir(ep, fhir_msg)
                status = "sent"
            except Exception as e:
                print(f"[emit_to_senders] FHIR send failed: {e}")
                status = "error"
            log = MessageLog(direction="out", kind="FHIR", endpoint_id=ep.id, payload=str(fhir_msg), ack_payload="", status=status)
            session.add(log)
            sent_any = True
    # Si aucun sender, log quand même les messages générés (endpoint_id=None)
    if not sent_any:
        log1 = MessageLog(direction="out", kind="MLLP", endpoint_id=None, payload=hl7_msg, ack_payload="", status="generated")
        log2 = MessageLog(direction="out", kind="FHIR", endpoint_id=None, payload=str(fhir_msg), ack_payload="", status="generated")
        session.add(log1)
        session.add(log2)
    session.commit()