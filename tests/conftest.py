"""Test fixtures"""
import pytest
from sqlmodel import SQLModel, Session, create_engine
import os
import sys
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Indicate to the app that we're running tests
os.environ.setdefault("TESTING", "1")

# Ensure repository root is on sys.path so `import app` works when running pytest from VS Code or terminals
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import models so SQLModel.metadata includes all tables
import app.models as _
import app.models_identifiers as _
import app.models_transport as _
import app.models_structure as _
import app.models_structure_fhir as _
import app.models_endpoints as _
import app.models_context as _

# Import the FastAPI app utilities
from app.db import engine, get_session
from app.app import lifespan

# Create a test application
app = FastAPI(lifespan=lifespan)

def override_get_session():
    with Session(engine) as session:
        yield session

# Set up the test application with required routes
from app.routers import structure
app.include_router(structure.router)

# Override the get_session dependency with our test session
app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(name="session")
def session_fixture():
    """Provide a DB session for tests. The DB schema is created by the autouse fixture."""
    with Session(engine) as session:
        # Some tests expect session.refresh(obj) to return the object
        _orig_refresh = session.refresh

        def _refresh_and_return(obj):
            _orig_refresh(obj)
            return obj

        session.refresh = _refresh_and_return
        yield session


@pytest.fixture(name="test_endpoints")
def test_endpoints_fixture(session: Session):
    """Create a pair of test SystemEndpoint records (MLLP + FHIR)."""
    from app.models_endpoints import SystemEndpoint

    mllp_endpoint = SystemEndpoint(
        name="Test MLLP",
        kind="MLLP",
        role="sender",
        host="localhost",
        port=2575,
        sending_app="TEST_APP",
        sending_facility="TEST_FAC",
        receiving_app="REC_APP",
        receiving_facility="REC_FAC",
        is_enabled=True,
    )
    fhir_endpoint = SystemEndpoint(
        name="Test FHIR",
        kind="FHIR",
        role="sender",
        host="http://localhost",
        port=8080,
        is_enabled=True,
    )

    session.add(mllp_endpoint)
    session.add(fhir_endpoint)
    session.commit()
    session.refresh(mllp_endpoint)
    session.refresh(fhir_endpoint)

    return {"mllp": mllp_endpoint, "fhir": fhir_endpoint}


@pytest.fixture(autouse=True)
def setup_database():
    """Autouse fixture: create schema and initialize minimal reference data for tests."""
    # Create tables
    SQLModel.metadata.create_all(engine)

    # Initialize vocabularies / minimal reference data if available
    with Session(engine) as session:
        try:
            from app.vocabulary_init import init_vocabularies

            init_vocabularies(session)
        except Exception:
            # If init_vocabularies is not present or fails for tests,
            # ignore and continue — tests can create needed rows explicitly.
            pass

        # Ensure there's at least one GHTContext to avoid queries failing
        try:
            from app.models_context import GHTContext
            from sqlmodel import select

            existing = session.exec(select(GHTContext)).first()
            if not existing:
                ctx = GHTContext(name="Test GHT", code="TEST_GHT", description="Auto init", is_active=True)
                session.add(ctx)
                session.commit()
        except Exception:
            # If the model/table isn't present or the query fails, continue.
            pass

        # Seed a minimal hospital structure with one UF used by PAM tests (identifier '001')
        try:
            from sqlmodel import select as _select
            from app.models_structure import (
                EntiteGeographique,
                Pole,
                Service,
                UniteFonctionnelle,
                LocationStatus,
                LocationMode,
                LocationPhysicalType,
                LocationServiceType,
            )

            eg = session.exec(_select(EntiteGeographique).where(EntiteGeographique.identifier == "EG-TEST")).first()
            if not eg:
                eg = EntiteGeographique(
                    identifier="EG-TEST",
                    name="Etablissement Test",
                    status=LocationStatus.ACTIVE,
                    mode=LocationMode.INSTANCE,
                    physical_type=LocationPhysicalType.SI,
                )
                session.add(eg)
                session.flush()

            pole = session.exec(_select(Pole).where(Pole.identifier == "POLE-TEST")).first()
            if not pole:
                pole = Pole(
                    identifier="POLE-TEST",
                    name="Pôle Test",
                    status=LocationStatus.ACTIVE,
                    mode=LocationMode.INSTANCE,
                    physical_type=LocationPhysicalType.AREA,
                    entite_geo_id=eg.id,
                )
                session.add(pole)
                session.flush()

            srv = session.exec(_select(Service).where(Service.identifier == "SRV-TEST")).first()
            if not srv:
                srv = Service(
                    identifier="SRV-TEST",
                    name="Service Test",
                    status=LocationStatus.ACTIVE,
                    mode=LocationMode.INSTANCE,
                    physical_type=LocationPhysicalType.AREA,
                    service_type=LocationServiceType.MCO,
                    pole_id=pole.id,
                )
                session.add(srv)
                session.flush()

            uf = session.exec(_select(UniteFonctionnelle).where(UniteFonctionnelle.identifier == "001")).first()
            if not uf:
                uf = UniteFonctionnelle(
                    identifier="001",
                    name="UF 001",
                    status=LocationStatus.ACTIVE,
                    mode=LocationMode.INSTANCE,
                    physical_type=LocationPhysicalType.FL,
                    service_id=srv.id,
                )
                session.add(uf)
                session.flush()

            session.commit()
        except Exception:
            # If structure models are absent or something goes wrong, don't block tests.
            pass

    yield

    # Drop tables after each test to keep isolation
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    # Lazy import app factory so DB is initialized first
    from app.app import create_app
    from app.db import get_session

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    app.root_path = ""
    app.base_url = "http://testserver"

    with TestClient(app, base_url="http://testserver") as c:
        # Auto-select a GHT context for routes protected by require_ght_context
        try:
            from app.models_structure_fhir import GHTContext
            from sqlmodel import select as _select
            with Session(engine) as s:
                ctx = s.exec(_select(GHTContext)).first()
                if not ctx:
                    ctx = GHTContext(name="Test GHT", code="TEST_GHT", is_active=True)
                    s.add(ctx)
                    s.commit()
                    s.refresh(ctx)
            c.get(f"/admin/ght/{ctx.id}", follow_redirects=True)
        except Exception:
            pass
        yield c


# Example HL7 message fixture
@pytest.fixture(name="hl7_adt_a01")
def hl7_adt_a01_fixture():
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    return (
        f"MSH|^~\\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|{now}||ADT^A01|MSG00001|P|2.5.1|\n"
        f"EVN|A01|{now}||||\n"
        f"PID|1||12345^^^HOPITAL^PI||DUPONT^JEAN^^^^^L||19800101|M|||1 RUE DU TEST^^VILLE^^75001^FRA||0123456789^^^test@email.com|||||\n"
        f"PV1|1|I|CARDIO^101^1^HOPITAL||||12345^DOC^JOHN^^^^^||||||||||ADM|A0|||||||||||||||||||||||||{now}|"
    )


# -----------------------
# Multi-venue test data
# -----------------------
@pytest.fixture(name="dossier_chemo_with_sessions")
def dossier_chemo_with_sessions_fixture(session: Session):
    """
    Crée un dossier avec plusieurs venues (ex. séances de chimiothérapie en HDJ).

    Retourne un dict avec: patient, dossier, venues (list[Venue])
    """
    from app.models import Patient, Dossier, Venue
    from app.db import get_next_sequence

    # Patient minimal avec identifiant simple
    pat_seq = get_next_sequence(session, "patient")
    patient = Patient(
        patient_seq=pat_seq,
        identifier=str(pat_seq),
        family="CHEMO",
        given="Test",
        gender="other",
    )
    session.add(patient)
    session.flush()

    # Dossier parent
    dossier = Dossier(
        dossier_seq=get_next_sequence(session, "dossier"),
        patient_id=patient.id,
        uf_medicale="HDJ-ONCO",
        admit_time=datetime.now(),
    )
    session.add(dossier)
    session.flush()

    # Trois venues successives (ex. 3 séances)
    venues = []
    for i in range(1, 4):
        v = Venue(
            venue_seq=get_next_sequence(session, "venue"),
            dossier_id=dossier.id,
            uf_medicale="HDJ-ONCO",
            start_time=datetime.now(),
            code="HDJ-ONCO",
            label=f"Chimiothérapie - Séance {i}",
        )
        session.add(v)
        session.flush()
        session.refresh(v)
        venues.append(v)

    session.commit()
    session.refresh(patient)
    session.refresh(dossier)
    return {"patient": patient, "dossier": dossier, "venues": venues}


@pytest.fixture(name="dossier_psy_day_hospital_multi")
def dossier_psy_day_hospital_multi_fixture(session: Session):
    """
    Crée un dossier avec venues multiples en hospitalisation de jour (psychiatrie).

    Retourne un dict avec: patient, dossier, venues (list[Venue])
    """
    from app.models import Patient, Dossier, Venue
    from app.db import get_next_sequence

    pat_seq = get_next_sequence(session, "patient")
    patient = Patient(
        patient_seq=pat_seq,
        identifier=str(pat_seq),
        family="PSY",
        given="HDJ",
        gender="female",
    )
    session.add(patient)
    session.flush()

    dossier = Dossier(
        dossier_seq=get_next_sequence(session, "dossier"),
        patient_id=patient.id,
        uf_medicale="HDJ-PSY",
        admit_time=datetime.now(),
    )
    session.add(dossier)
    session.flush()

    venues = []
    labels = [
        "HDJ Psychiatrie - Evaluation",
        "HDJ Psychiatrie - Thérapie de groupe",
        "HDJ Psychiatrie - Suivi",
    ]
    for i, label in enumerate(labels, start=1):
        v = Venue(
            venue_seq=get_next_sequence(session, "venue"),
            dossier_id=dossier.id,
            uf_medicale="HDJ-PSY",
            start_time=datetime.now(),
            code="HDJ-PSY",
            label=label,
        )
        session.add(v)
        session.flush()
        session.refresh(v)
        venues.append(v)

    session.commit()
    session.refresh(patient)
    session.refresh(dossier)
    return {"patient": patient, "dossier": dossier, "venues": venues}


# -----------------------
# Multi-venue with movements (A01 + A03), PV1-2 = R (recurring)
# -----------------------
@pytest.fixture(name="dossier_chemo_with_sessions_recurring")
def dossier_chemo_with_sessions_recurring_fixture(session: Session, dossier_chemo_with_sessions):
    """
    Étend dossier_chemo_with_sessions en ajoutant pour chaque venue deux mouvements:
    - A01 (admission)
    - A03 (sortie)

    Semantique: hospitalisation récidivante (PV1-2 = R) — représentée par des venues distinctes
    avec ouverture/fermeture via A01/A03.
    """
    from app.models import Mouvement
    from app.db import get_next_sequence
    from datetime import timedelta

    data = dossier_chemo_with_sessions
    venues = data["venues"]

    base_time = datetime.now()
    for idx, v in enumerate(venues):
        # Admission A01
        m_admit = Mouvement(
            mouvement_seq=get_next_sequence(session, "mouvement"),
            venue_id=v.id,
            type="ADT^A01",
            when=base_time + timedelta(minutes=idx * 10),
            location=f"HDJ-ONCO-{idx+1:02d}",
            movement_type="admission",
            trigger_event="A01",
        )
        session.add(m_admit)

        # Discharge A03
        m_discharge = Mouvement(
            mouvement_seq=get_next_sequence(session, "mouvement"),
            venue_id=v.id,
            type="ADT^A03",
            when=base_time + timedelta(minutes=idx * 10 + 5),
            location=f"HDJ-ONCO-{idx+1:02d}",
            movement_type="discharge",
            trigger_event="A03",
        )
        session.add(m_discharge)

    session.commit()
    return data


@pytest.fixture(name="dossier_psy_day_hospital_recurring")
def dossier_psy_day_hospital_recurring_fixture(session: Session, dossier_psy_day_hospital_multi):
    """
    Étend dossier_psy_day_hospital_multi en ajoutant A01 + A03 pour chaque venue (PV1-2 = R).
    """
    from app.models import Mouvement
    from app.db import get_next_sequence
    from datetime import timedelta

    data = dossier_psy_day_hospital_multi
    venues = data["venues"]

    base_time = datetime.now()
    for idx, v in enumerate(venues):
        m_admit = Mouvement(
            mouvement_seq=get_next_sequence(session, "mouvement"),
            venue_id=v.id,
            type="ADT^A01",
            when=base_time + timedelta(minutes=idx * 15),
            location=f"HDJ-PSY-{idx+1:02d}",
            movement_type="admission",
            trigger_event="A01",
        )
        session.add(m_admit)

        m_discharge = Mouvement(
            mouvement_seq=get_next_sequence(session, "mouvement"),
            venue_id=v.id,
            type="ADT^A03",
            when=base_time + timedelta(minutes=idx * 15 + 10),
            location=f"HDJ-PSY-{idx+1:02d}",
            movement_type="discharge",
            trigger_event="A03",
        )
        session.add(m_discharge)

    session.commit()
    return data
