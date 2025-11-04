"""
Tests pour la fusion de patients (A40 - Merge Patient).
"""
from datetime import datetime

import pytest
from sqlmodel import Session, select

from app.db import engine, get_next_sequence
from app.models import Patient, Dossier, Venue
from app.models_identifiers import Identifier, IdentifierType
from app.services.patient_merge import handle_merge_patient, _parse_mrg_segment, _find_patient_by_identifiers
from app.services.mllp import build_ack


@pytest.fixture
def session():
    """Provide a clean database session for each test"""
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
        s.rollback()


def test_parse_mrg_segment():
    """Test parsing du segment MRG"""
    message = (
        "MSH|^~\\&|SENDER|SENDFAC|RECV|RECVFAC|20250103120000||ADT^A40|12345|P|2.5\r"
        "PID|||123456^^^HOSPITAL^PI||DOE^JOHN^||19800101|M\r"
        "MRG|654321^^^HOSPITAL^PI~999888^^^OLDHOSP^PI||ACC123||||||DUPONT^JEAN^\r"
    )
    
    mrg_data = _parse_mrg_segment(message)
    
    assert mrg_data is not None
    assert len(mrg_data["identifiers"]) == 2
    assert "654321^^^HOSPITAL^PI" in mrg_data["identifiers"]
    assert "999888^^^OLDHOSP^PI" in mrg_data["identifiers"]
    assert mrg_data["account_number"] == "ACC123"
    assert mrg_data["name"] and "DUPONT^JEAN^" in mrg_data["name"]


def test_find_patient_by_identifiers(session: Session):
    """Test recherche de patient par identifiants CX"""
    # Créer un patient avec identifiant
    patient = Patient(
        patient_seq=get_next_sequence(session, "patient"),
        identifier="TEST001",
        external_id="EXT001",
        family="Test",
        given="Patient",
        gender="M",
        birth_date="19900101"
    )
    session.add(patient)
    session.flush()
    
    # Ajouter un identifiant dans la table Identifier
    ident = Identifier(
        value="EXT001",
        system="urn:oid:1.2.3.4.5",
        type=IdentifierType.PI,
        status="active",
        patient_id=patient.id
    )
    session.add(ident)
    session.flush()
    
    # Test recherche
    cx_list = ["EXT001^^^HOSPITAL^PI", "OTHER123^^^HOSPITAL^PI"]
    found = _find_patient_by_identifiers(session, cx_list)
    
    assert found is not None
    assert found.id == patient.id


@pytest.mark.asyncio
async def test_merge_patient_basic(session: Session):
    """Test fusion basique de deux patients"""
    # Créer patient source
    source_patient = Patient(
        patient_seq=get_next_sequence(session, "patient"),
        identifier="SOURCE001",
        external_id="SRC001",
        family="Dupont",
        given="Jean",
        gender="M",
        birth_date="19850615"
    )
    session.add(source_patient)
    session.flush()
    
    # Créer patient survivant
    surviving_patient = Patient(
        patient_seq=get_next_sequence(session, "patient"),
        identifier="SURV001",
        external_id="SURV001",
        family="Dupont",
        given="Jean",
        gender="M",
        birth_date="19850615"
    )
    session.add(surviving_patient)
    session.flush()
    
    # Ajouter des identifiants
    source_ident = Identifier(
        value="SRC001",
        system="urn:oid:1.2.3.4.5",
        type=IdentifierType.PI,
        status="active",
        patient_id=source_patient.id
    )
    session.add(source_ident)
    
    surv_ident = Identifier(
        value="SURV001",
        system="urn:oid:1.2.3.4.5",
        type=IdentifierType.PI,
        status="active",
        patient_id=surviving_patient.id
    )
    session.add(surv_ident)
    session.flush()
    
    # Créer des dossiers pour le patient source
    dossier1 = Dossier(
        dossier_seq=get_next_sequence(session, "dossier"),
        patient_id=source_patient.id,
        uf_responsabilite="UF-TEST",
        admit_time=datetime.utcnow()
    )
    dossier2 = Dossier(
        dossier_seq=get_next_sequence(session, "dossier"),
        patient_id=source_patient.id,
        uf_responsabilite="UF-TEST2",
        admit_time=datetime.utcnow()
    )
    session.add_all([dossier1, dossier2])
    session.flush()
    
    # Construire message A40
    message = (
        f"MSH|^~\\&|SENDER|SENDFAC|RECV|RECVFAC|20250103120000||ADT^A40|12345|P|2.5\r"
        f"PID|||SURV001^^^HOSPITAL^PI||DUPONT^JEAN^||19850615|M\r"
        f"MRG|SRC001^^^HOSPITAL^PI||||||DUPONT^JEAN^\r"
    )
    
    pid_data = {
        "identifiers": [("SURV001^^^HOSPITAL^PI", "PI")],
        "external_id": "SURV001",
        "family": "Dupont",
        "given": "Jean",
        "gender": "M",
        "birth_date": "19850615"
    }
    
    pv1_data = {}
    
    # Exécuter la fusion
    success, error = await handle_merge_patient(session, "A40", pid_data, pv1_data, message)
    
    # Vérifications
    assert success is True
    assert error is None
    
    # Vérifier que les dossiers ont été ré-attribués
    dossiers = session.exec(
        select(Dossier).where(Dossier.patient_id == surviving_patient.id)
    ).all()
    assert len(dossiers) == 2
    
    # Vérifier qu'aucun dossier n'est resté sur le patient source
    source_dossiers = session.exec(
        select(Dossier).where(Dossier.patient_id == source_patient.id)
    ).all()
    assert len(source_dossiers) == 0
    
    # Vérifier que l'identifiant source est marqué "old"
    source_ident_after = session.get(Identifier, source_ident.id)
    assert source_ident_after.status == "old"
    assert source_ident_after.patient_id == surviving_patient.id
    
    # Vérifier que le patient source est archivé
    source_after = session.get(Patient, source_patient.id)
    assert "[MERGED]" in source_after.family
    assert "ARCHIVED-" in source_after.identifier


@pytest.mark.asyncio
async def test_merge_patient_with_venues_and_mouvements(session: Session):
    """Test fusion avec venues et mouvements"""
    # Créer patients
    source = Patient(
        patient_seq=get_next_sequence(session, "patient"),
        identifier="SRC002",
        external_id="SRC002",
        family="Martin",
        given="Pierre",
        gender="M",
        birth_date="19750410"
    )
    surviving = Patient(
        patient_seq=get_next_sequence(session, "patient"),
        identifier="SURV002",
        external_id="SURV002",
        family="Martin",
        given="Pierre",
        gender="M",
        birth_date="19750410"
    )
    session.add_all([source, surviving])
    session.flush()
    
    # Identifiants
    session.add_all([
        Identifier(value="SRC002", system="urn:oid:1.2.3", type=IdentifierType.PI, status="active", patient_id=source.id),
        Identifier(value="SURV002", system="urn:oid:1.2.3", type=IdentifierType.PI, status="active", patient_id=surviving.id),
    ])
    session.flush()
    
    # Dossier + venue pour le patient source
    dossier = Dossier(
        dossier_seq=get_next_sequence(session, "dossier"),
        patient_id=source.id,
        uf_responsabilite="UF-CARDIO",
        admit_time=datetime.utcnow()
    )
    session.add(dossier)
    session.flush()
    
    venue = Venue(
        venue_seq=get_next_sequence(session, "venue"),
        dossier_id=dossier.id,
        uf_responsabilite="UF-CARDIO",
        start_time=datetime.utcnow(),
        code="CARD-01",
        label="Hospitalisation Cardiologie"
    )
    session.add(venue)
    session.flush()
    
    # Message A40
    message = (
        f"MSH|^~\\&|SENDER|SENDFAC|RECV|RECVFAC|20250103120000||ADT^A40|67890|P|2.5\r"
        f"PID|||SURV002^^^HOSPITAL^PI||MARTIN^PIERRE^||19750410|M\r"
        f"MRG|SRC002^^^HOSPITAL^PI||||||MARTIN^PIERRE^\r"
    )
    
    pid_data = {
        "identifiers": [("SURV002^^^HOSPITAL^PI", "PI")],
        "external_id": "SURV002",
        "family": "Martin",
        "given": "Pierre",
        "gender": "M",
        "birth_date": "19750410"
    }
    
    # Fusion
    success, error = await handle_merge_patient(session, "A40", pid_data, {}, message)
    
    assert success is True
    
    # Vérifier le dossier est maintenant lié au patient survivant
    dossier_after = session.get(Dossier, dossier.id)
    assert dossier_after.patient_id == surviving.id
    
    # Vérifier que la venue est toujours liée au dossier (indirect via patient)
    venue_after = session.get(Venue, venue.id)
    assert venue_after.dossier_id == dossier.id
    assert venue_after.dossier.patient_id == surviving.id


@pytest.mark.asyncio
async def test_merge_patient_missing_mrg(session: Session):
    """Test échec si le segment MRG est manquant"""
    message = (
        "MSH|^~\\&|SENDER|SENDFAC|RECV|RECVFAC|20250103120000||ADT^A40|12345|P|2.5\r"
        "PID|||123456^^^HOSPITAL^PI||DOE^JOHN^||19800101|M\r"
    )
    
    pid_data = {"identifiers": [("123456^^^HOSPITAL^PI", "PI")]}
    pv1_data = {}
    
    success, error = await handle_merge_patient(session, "A40", pid_data, pv1_data, message)
    
    assert success is False
    assert "MRG" in error


@pytest.mark.asyncio
async def test_merge_patient_source_not_found(session: Session):
    """Test échec si le patient source n'existe pas"""
    # Créer uniquement le patient survivant
    surviving = Patient(
        patient_seq=get_next_sequence(session, "patient"),
        identifier="SURV003",
        external_id="SURV003",
        family="Doe",
        given="Jane",
        gender="F",
        birth_date="19920305"
    )
    session.add(surviving)
    session.flush()
    
    session.add(Identifier(
        value="SURV003",
        system="urn:oid:1.2.3",
        type=IdentifierType.PI,
        status="active",
        patient_id=surviving.id
    ))
    session.flush()
    
    message = (
        "MSH|^~\\&|SENDER|SENDFAC|RECV|RECVFAC|20250103120000||ADT^A40|12345|P|2.5\r"
        "PID|||SURV003^^^HOSPITAL^PI||DOE^JANE^||19920305|F\r"
        "MRG|UNKNOWN999^^^HOSPITAL^PI||||||DOE^JANE^\r"
    )
    
    pid_data = {"identifiers": [("SURV003^^^HOSPITAL^PI", "PI")]}
    pv1_data = {}
    
    success, error = await handle_merge_patient(session, "A40", pid_data, pv1_data, message)
    
    assert success is False
    assert "introuvable" in error.lower()
