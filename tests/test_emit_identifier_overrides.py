import re
from sqlmodel import Session
from app.models import Patient, Dossier
from app.services.emit_on_create import generate_pam_hl7, generate_fhir


def test_hl7_pid3_override(session: Session):
    # create patient
    patient = Patient(family="TEST", given="TOTO", patient_seq=777, birth_date="19800101", gender="M")
    session.add(patient)
    session.commit()
    session.refresh(patient)

    # generate with forced OID
    hl7 = generate_pam_hl7(patient, "patient", session, forced_identifier_system=None, forced_identifier_oid="1.2.250.1.71.1.2.2")
    # Find PID line
    pid_line = next((l for l in hl7.splitlines() if l.startswith("PID")), "")
    assert pid_line, "PID segment missing"
    # Expect CX value like 777^^^HOSP&1.2.250.1.71.1.2.2&ISO^PI (with assigning authority)
    assert re.search(rf"{patient.patient_seq}\^\^\^[^&]+&1\.2\.250\.1\.71\.1\.2\.2&ISO\^PI", pid_line)


def test_fhir_identifier_override(session: Session):
    patient = Patient(family="DUPONT", given="JEAN", patient_seq=888)
    session.add(patient)
    session.commit()
    session.refresh(patient)

    fhir = generate_fhir(patient, "patient", session, forced_identifier_system="urn:oid:1.2.250.1.71.1.2.2", forced_identifier_oid="1.2.250.1.71.1.2.2")
    # fhir is a Patient resource dict
    ids = fhir.get("identifier", [])
    assert ids, "No identifiers generated"
    # All identifiers should have the forced system applied
    for iid in ids:
        assert iid.get("system") == "urn:oid:1.2.250.1.71.1.2.2"
    # Check assigner structure when OID provided
    assert any("assigner" in iid and iid["assigner"]["identifier"]["value"] == "1.2.250.1.71.1.2.2" for iid in ids)
