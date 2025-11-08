import os
from datetime import datetime
from sqlmodel import Session
from app.db import engine, init_db
from app.models import Patient, Dossier, Venue, Mouvement, DossierType
from app.services.hl7_generator import generate_admission_message, generate_update_message


def _build_entities(session: Session):
    """Crée et persiste un patient/dossier/venue/mouvement minimal pour tests."""
    patient = Patient(family="STRICT", given="Mode", birth_date="1980-01-01", gender="male")
    session.add(patient)
    session.commit(); session.refresh(patient)

    dossier = Dossier(dossier_seq=9999, patient_id=patient.id, uf_responsabilite="UF-STRICT", admit_time=datetime.utcnow(), dossier_type=DossierType.HOSPITALISE)
    session.add(dossier); session.commit(); session.refresh(dossier)

    venue = Venue(venue_seq=9999, dossier_id=dossier.id, uf_responsabilite="UF-STRICT", start_time=datetime.utcnow(), code="STRICT-LOC", label="Strict Location")
    session.add(venue); session.commit(); session.refresh(venue)

    mouvement = Mouvement(mouvement_seq=9999, venue_id=venue.id, when=datetime.utcnow(), location="STRICT-LOC/BOX", trigger_event="A01")
    session.add(mouvement); session.commit(); session.refresh(mouvement)
    return patient, dossier, venue, mouvement


def test_admission_always_allowed():
    init_db()
    os.environ.pop("STRICT_PAM_FR", None)
    with Session(engine) as session:
        patient, dossier, venue, mouvement = _build_entities(session)
        msg = generate_admission_message(patient, dossier, venue)
        assert "ADT^A01" in msg


def test_update_allowed_without_strict():
    init_db()
    os.environ.pop("STRICT_PAM_FR", None)
    with Session(engine) as session:
        patient, dossier, venue, mouvement = _build_entities(session)
        msg = generate_update_message(patient=patient, dossier=dossier, venue=venue)
        assert "ADT^A08" in msg


def test_update_blocked_in_strict_mode():
    init_db()
    os.environ["STRICT_PAM_FR"] = "1"
    with Session(engine) as session:
        patient, dossier, venue, mouvement = _build_entities(session)
        blocked = False
        try:
            generate_update_message(patient=patient, dossier=dossier, venue=venue)
        except Exception as e:
            blocked = True
            assert "A08" in str(e)
        finally:
            os.environ.pop("STRICT_PAM_FR", None)
        assert blocked, "A08 should be blocked in strict mode"
