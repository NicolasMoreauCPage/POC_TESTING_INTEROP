import asyncio
from datetime import datetime
import pytest
from sqlmodel import Session, select
from sqlalchemy import func
from sqlalchemy import text

from app.db import engine
from app.models import Patient, Dossier, Venue, Mouvement
from app.models_shared import MessageLog, SystemEndpoint
from app.services.entity_events import register_entity_events


@pytest.fixture(autouse=True)
def _disable_sender_endpoints():
    """Ensure no active sender endpoints so identity emitter logs 'generated' MLLP+FHIR.
    This avoids sending attempts and makes assertions stable.
    """
    with Session(engine) as s:
        eps = s.exec(select(SystemEndpoint)).all()
        for ep in eps:
            if ep.role in ("sender", "both"):
                ep.is_enabled = False
                # also clear host/ports to be safe
                ep.host = None
                ep.port = None
                s.add(ep)
        s.commit()
    yield


@pytest.fixture(scope="session", autouse=True)
def _register_identity_listeners():
    """Ensure SQLAlchemy event listeners for identity/movements are registered."""
    register_entity_events()
    yield


async def _wait_bg():
    # allow background after_commit tasks to run
    await asyncio.sleep(0.15)


def _count_logs(session: Session):
    return session.exec(select(func.count()).select_from(MessageLog)).one()


def _new_patient() -> Patient:
    return Patient(
        family="Doe",
        given="John",
        birth_date="19800101",
        gender="M",
        patient_seq=0,
        external_id="TEST-PAT-001",
    )


@pytest.mark.asyncio
async def test_patient_insert_update_emits_hl7_and_fhir():
    with Session(engine) as s:
        # cleanup logs
        s.exec(text("DELETE FROM messagelog"))
        s.commit()
        before = _count_logs(s)

        p = _new_patient()
        s.add(p)
        s.commit()
        await _wait_bg()

        mid = _count_logs(s)
        assert mid >= before + 2, "Expected at least 2 logs (MLLP + FHIR) on patient insert"

        # update
        p.given = "Johnny"
        s.add(p)
        s.commit()
        await _wait_bg()

        after = _count_logs(s)
        assert after >= mid + 2, "Expected at least 2 logs (MLLP + FHIR) on patient update"


@pytest.mark.asyncio
async def test_dossier_venue_mouvement_emissions_on_insert_update():
    with Session(engine) as s:
        s.exec(text("DELETE FROM messagelog"))
        s.commit()
        before = _count_logs(s)

        # create patient+dossier
        p = _new_patient()
        s.add(p)
        s.commit()
        # wait for patient logs
        await _wait_bg()
        d = Dossier(dossier_seq=0, patient_id=p.id, uf_medicale="UF1",
 uf_hebergement="UF1", admit_time=datetime.utcnow())
        s.add(d)
        s.commit()
        await _wait_bg()

        # Create a Venue (admission)
        v = Venue(venue_seq=0, code="VENUE-TST-1", label="Test Venue", uf_medicale="UF1",
 uf_hebergement="UF1", start_time=datetime.utcnow())
        v.dossier_id = d.id
        s.add(v)
        s.commit()
        await _wait_bg()

        # Update venue label
        v.label = "Test Venue Updated"
        s.add(v)
        s.commit()
        await _wait_bg()

        # Create a Mouvement
        m = Mouvement(mouvement_seq=0, venue_id=v.id, type="ADT^A01", when=datetime.utcnow())
        s.add(m)
        s.commit()
        await _wait_bg()

        # Update mouvement type
        m.type = "ADT^A08"
        s.add(m)
        s.commit()
        await _wait_bg()

        after = _count_logs(s)
        # patient + dossier + venue (create/update) + mouvement (create/update)
        # Each insert/update should produce at least 2 logs (MLLP+FHIR) under our setup
        assert after - before >= 8, f"Expected >=8 logs, got {after - before}"
