import asyncio
import pytest
from sqlmodel import create_engine, SQLModel, Session, select

from app.services.transport_inbound import _parse_pid, _parse_pv1, _handle_z99_updates, on_message_inbound
from app.models import Patient, Dossier, Venue, Mouvement
from app.models_endpoints import SystemEndpoint

SAMPLE_MSG = (
    "MSH|^~\\&|CPAGE|CPAGE|ANTARES|ANTARES|20250513081608||ADT^A28^ADT_A05|1000467197|P|2.5^FRA^2.4|||||FRA|8859/1\r"
    "EVN||20250513081608|||int^ADMIN^ADM INTER^^^^^^CPAGE&1.2.250.1.154&ISO|20250513081608\r"
    "PID|||000000406588^^^CPAGE&1.2.250.1.211.10.200.2&ISO^PI~2500022^^^CPAGE^MR||TESTCONSENTEMENT^DEMEPE^^^M.^^L||19900101|M|||Rue Test^^DIJON^^21000^FRA^H|||||S||||||||N||||||N||PROV\r"
    "PV1||N|SERVICE^ROOM^BED||...|||||||||||20250513081608||||||||||||||||||||||||||\r"
)

@pytest.fixture()
def engine():
    e = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(e)
    return e

@pytest.fixture()
def session(engine):
    with Session(engine) as s:
        yield s


def test_parse_pid_basic():
    pid = _parse_pid(SAMPLE_MSG)
    assert pid["external_id"] == "000000406588"
    assert pid["family"] == "TESTCONSENTEMENT"
    assert pid["given"].startswith("DEMEPE")
    assert pid["birth_date"] == "19900101"


def test_parse_pv1_basic():
    pv1 = _parse_pv1(SAMPLE_MSG)
    assert pv1["location"].startswith("SERVICE")


@pytest.mark.asyncio
async def test_integration_create_entities(session):
    # create an endpoint in DB
    ep = SystemEndpoint(name="EP", kind="MLLP", role="receiver")
    session.add(ep)
    session.commit()
    session.refresh(ep)

    ack = await on_message_inbound(SAMPLE_MSG, session, ep)
    assert "MSA|AA" in ack or "MSA|" in ack

    # patient created
    p = session.exec(select(Patient).where(Patient.external_id == "000000406588")).first()
    assert p is not None

    # dossier created for patient
    d = session.exec(select(Dossier).where(Dossier.patient_id == p.id)).first()
    assert d is not None

    # venue created for dossier
    v = session.exec(select(Venue).where(Venue.dossier_id == d.id)).first()
    assert v is not None

    # mouvement created (A28 is not in movement triggers by default, but our logic may still add none) -- we check MessageLog
    logs = session.exec(select(__import__('app').services.transport_inbound.MessageLog)).all()
    assert len(logs) >= 1


def test_z99_updates(session):
    # create a dossier and commit
    d = Dossier(dossier_seq=12345, patient_id=1, uf_responsabilite="OLD", admit_time="2025-05-13T08:16:08")
    session.add(d)
    session.commit()
    session.refresh(d)

    msg = "Z99|Dossier|12345|uf_responsabilite|NEW_UF\r"
    _handle_z99_updates(msg, session)
    d2 = session.exec(select(Dossier).where(Dossier.dossier_seq == 12345)).first()
    assert d2.uf_responsabilite == "NEW_UF"
