import os
from datetime import datetime
from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Patient, Dossier, Venue, Mouvement, DossierType
from app.models_structure_fhir import GHTContext, EntiteJuridique
from app.models_shared import SystemEndpoint
from app.services.hl7_generator import generate_update_message


def _build_core_entities(session: Session):
    patient = Patient(family="EJ", given="Strict", birth_date="1985-02-02", gender="male")
    session.add(patient); session.commit(); session.refresh(patient)
    dossier = Dossier(dossier_seq=701, patient_id=patient.id, uf_responsabilite="UF-EJ", admit_time=datetime.utcnow(), dossier_type=DossierType.HOSPITALISE)
    session.add(dossier); session.commit(); session.refresh(dossier)
    venue = Venue(venue_seq=701, dossier_id=dossier.id, uf_responsabilite="UF-EJ", start_time=datetime.utcnow(), code="LOC-EJ", label="Loc EJ")
    session.add(venue); session.commit(); session.refresh(venue)
    mouvement = Mouvement(mouvement_seq=701, venue_id=venue.id, when=datetime.utcnow(), location="LOC-EJ/BOX", trigger_event="A01")
    session.add(mouvement); session.commit(); session.refresh(mouvement)
    return patient, dossier, venue, mouvement


def test_a08_blocked_for_strict_ej():
    init_db()
    with Session(engine) as session:
        # Contexte + EJ strict (défaut True)
        ght = GHTContext(name="GHT Demo", code="GHT-DEMO")
        session.add(ght); session.commit(); session.refresh(ght)
        ej_strict = EntiteJuridique(name="EJ Strict", finess_ej="123456789", ght_context_id=ght.id)
        session.add(ej_strict); session.commit(); session.refresh(ej_strict)
        endpoint = SystemEndpoint(name="EP Strict", kind="MLLP", entite_juridique_id=ej_strict.id)
        session.add(endpoint); session.commit(); session.refresh(endpoint)

        patient, dossier, venue, mouvement = _build_core_entities(session)

        blocked = False
        try:
            generate_update_message(endpoint=endpoint, patient=patient, dossier=dossier, venue=venue, movement=mouvement)
        except Exception as e:
            blocked = True
            assert "A08" in str(e)
        assert blocked, "A08 doit être bloqué pour une EJ strict_pam_fr=True"


def test_a08_allowed_for_non_strict_ej():
    init_db()
    os.environ.pop("STRICT_PAM_FR", None)  # Assurer que l'env n'impose pas strict
    with Session(engine) as session:
        ght = GHTContext(name="GHT Demo2", code="GHT-DEMO2")
        session.add(ght); session.commit(); session.refresh(ght)
        ej_open = EntiteJuridique(name="EJ Open", finess_ej="987654321", ght_context_id=ght.id, strict_pam_fr=False)
        session.add(ej_open); session.commit(); session.refresh(ej_open)
        endpoint = SystemEndpoint(name="EP Open", kind="MLLP", entite_juridique_id=ej_open.id)
        session.add(endpoint); session.commit(); session.refresh(endpoint)

        patient, dossier, venue, mouvement = _build_core_entities(session)
        msg = generate_update_message(endpoint=endpoint, patient=patient, dossier=dossier, venue=venue, movement=mouvement)
        assert "ADT^A08" in msg, "A08 devrait être autorisé pour EJ strict_pam_fr=False"
