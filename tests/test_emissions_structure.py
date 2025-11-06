import asyncio
import pytest
from sqlmodel import Session, select
from sqlalchemy import func, text

from app.db import engine
from app.models_structure_fhir import EntiteGeographique
from app.models_structure import Pole, Service, UniteFonctionnelle, UniteHebergement, Chambre, Lit, LocationStatus, LocationMode, LocationPhysicalType
from app.models_shared import MessageLog, SystemEndpoint
from app.services.entity_events_structure import register_structure_entity_events


@pytest.fixture(autouse=True)
def _ensure_sender_endpoints():
    """Create minimal disabled/invalid sender endpoints so structure emit logs entries.
    Structure emitter only logs when endpoints exist; create one FHIR and one MLLP sender
    with missing host/port to force error logs (but still create MessageLog).
    """
    with Session(engine) as s:
        # ensure one MLLP sender
        ep_mllp = s.exec(select(SystemEndpoint).where(SystemEndpoint.name == "TEST-MLLP-SENDER")).first()
        if not ep_mllp:
            ep_mllp = SystemEndpoint(name="TEST-MLLP-SENDER", kind="MLLP", role="sender", is_enabled=True)
        ep_mllp.host = None
        ep_mllp.port = None
        s.add(ep_mllp)

        # ensure one FHIR sender
        ep_fhir = s.exec(select(SystemEndpoint).where(SystemEndpoint.name == "TEST-FHIR-SENDER")).first()
        if not ep_fhir:
            ep_fhir = SystemEndpoint(name="TEST-FHIR-SENDER", kind="FHIR", role="sender", is_enabled=True)
        ep_fhir.base_url = None
        s.add(ep_fhir)
        s.commit()
    yield


@pytest.fixture(scope="session", autouse=True)
def _register_structure_listeners():
    """Ensure SQLAlchemy event listeners for structure entities are registered."""
    register_structure_entity_events()
    yield


async def _wait_bg():
    await asyncio.sleep(0.2)


def _count_logs(session: Session):
    return session.exec(select(func.count()).select_from(MessageLog)).one()


@pytest.mark.asyncio
async def test_structure_insert_update_delete_emit_logs():
    with Session(engine) as s:
        # cleanup logs
        s.exec(text("DELETE FROM messagelog"))
        s.commit()
        before = _count_logs(s)

        # Create EntiteGeographique
        eg = EntiteGeographique(identifier="EG-TST-1", name="EG Test", finess="999999999")
        s.add(eg)
        s.commit()
        await _wait_bg()

        # Create Pole under EG
        pole = Pole(identifier="POLE-TST-1", name="Pole Test", status=LocationStatus.ACTIVE, mode=LocationMode.INSTANCE, physical_type=LocationPhysicalType.SI, entite_geo_id=eg.id)
        s.add(pole)
        s.commit()
        await _wait_bg()

        # Update Pole name
        pole.name = "Pole Test Updated"
        s.add(pole)
        s.commit()
        await _wait_bg()

        # Create Service under Pole
        srv = Service(identifier="SRV-TST-1", name="Service Test", status=LocationStatus.ACTIVE, mode=LocationMode.INSTANCE, physical_type=LocationPhysicalType.SI, service_type="mco", pole_id=pole.id)
        s.add(srv)
        s.commit()
        await _wait_bg()

        # Create UF under Service
        uf = UniteFonctionnelle(identifier="UF-TST-1", name="UF Test", status=LocationStatus.ACTIVE, mode=LocationMode.INSTANCE, physical_type=LocationPhysicalType.FL, service_id=srv.id)
        s.add(uf)
        s.commit()
        await _wait_bg()

        # Create UH under UF
        uh = UniteHebergement(identifier="UH-TST-1", name="UH Test", status=LocationStatus.ACTIVE, mode=LocationMode.INSTANCE, physical_type=LocationPhysicalType.WI, unite_fonctionnelle_id=uf.id)
        s.add(uh)
        s.commit()
        await _wait_bg()

        # Create Chambre under UH
        ch = Chambre(identifier="CH-TST-1", name="Chambre Test", status=LocationStatus.ACTIVE, mode=LocationMode.INSTANCE, physical_type=LocationPhysicalType.RO, unite_hebergement_id=uh.id)
        s.add(ch)
        s.commit()
        await _wait_bg()

        # Create Lit under Chambre
        lit = Lit(identifier="LIT-TST-1", name="Lit Test", status=LocationStatus.ACTIVE, mode=LocationMode.INSTANCE, physical_type=LocationPhysicalType.BD, chambre_id=ch.id)
        s.add(lit)
        s.commit()
        await _wait_bg()

        # Update one leaf entity
        lit.name = "Lit Test Updated"
        s.add(lit)
        s.commit()
        await _wait_bg()

        # Now delete the leaf entity (should emit delete)
        s.delete(lit)
        s.commit()
        await _wait_bg()

        after = _count_logs(s)
        assert after - before >= 8, f"Expected at least 8 logs across operations, got {after - before}"
