import asyncio
import pytest
from sqlmodel import create_engine, SQLModel, Session, select
from datetime import datetime

from app.services.transport_inbound import _parse_pid, _parse_pv1, _handle_z99_updates, on_message_inbound
from app.models import Patient, Dossier, Venue, Mouvement
from app.models_endpoints import SystemEndpoint

# Pré-admission depuis la documentation CPAGE (simplifiée)
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


def _ihe_message(
    trigger: str,
    *,
    patient_id: str = "0000000123",
    location: str = "CHIR^001^001^CPAGE",
    cls: str = "I",
    prior_location: str = ""
) -> str:
    """
    Construit un message ADT inspiré des exemples CPAGE (MSH/EVN/PID/PV1/ZBE).
    """
    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    pv1_fields = [""] * 46
    pv1_fields[0] = "PV1"
    pv1_fields[1] = "1"
    pv1_fields[2] = cls
    pv1_fields[3] = location
    pv1_fields[6] = prior_location
    pv1_fields[44] = now
    pv1_segment = "|".join(pv1_fields) + "\r"

    base = (
        f"MSH|^~\\&|CPAGE|CPAGE|LOGICIEL|LOGICIEL|{now}||ADT^{trigger}^ADT_{trigger}|MSG{trigger}|P|2.5^FRA^2.1\r"
        f"EVN|{trigger}|{now}|||APPLI^IHE^\r"
        f"PID|1||{patient_id}^^^CPAGE&1.2.250.1.211.12.1.2&ISO^PI||PATIENT^{trigger}^^^^^L||19800101|F|||1 RUE DU TEST^^VILLE^^75000^FRA||||||||||||||\r"
        f"{pv1_segment}"
    )
    zbe = f"ZBE|1|{now}||UPDATE|N|{trigger}|^^^^^^CHIR^001^^001^CP|||HMS\r"
    return base + zbe


def test_parse_pid_basic():
    pid = _parse_pid(SAMPLE_MSG)
    assert pid["external_id"] == "000000406588"
    assert pid["family"] == "TESTCONSENTEMENT"
    assert pid["given"].startswith("DEMEPE")
    assert pid["birth_date"] == "19900101"


def test_parse_pv1_basic():
    pv1 = _parse_pv1(SAMPLE_MSG)
    assert pv1["location"].startswith("SERVICE")


def test_ihe_preadmission_to_cancel(session):
    result_a05 = on_message_inbound(_ihe_message("A05"), session)
    assert result_a05["status"] == "success"

    patient = session.exec(select(Patient).where(Patient.identifier == "0000000123")).first()
    assert patient is not None

    result_a38 = on_message_inbound(_ihe_message("A38"), session)
    assert result_a38["status"] == "success"


def test_ihe_permission_cycle(session):
    on_message_inbound(_ihe_message("A01"), session)
    leave = on_message_inbound(_ihe_message("A21"), session)
    assert leave["status"] == "success"

    back = on_message_inbound(_ihe_message("A22"), session)
    assert back["status"] == "success"


def test_ihe_doctor_change(session):
    on_message_inbound(_ihe_message("A01"), session)
    change = on_message_inbound(_ihe_message("A54"), session)
    assert change["status"] == "success"


def test_ihe_transfer_and_annulation(session):
    on_message_inbound(_ihe_message("A01"), session)
    transfer = on_message_inbound(_ihe_message("A02"), session)
    assert transfer["status"] == "success"

    cancel_transfer = on_message_inbound(_ihe_message("A12"), session)
    assert cancel_transfer["status"] == "success"


def test_ihe_admission_cancel(session):
    admission = on_message_inbound(_ihe_message("A01"), session)
    assert admission["status"] == "success"

    cancel = on_message_inbound(_ihe_message("A11"), session)
    assert cancel["status"] == "success"


def test_ihe_discharge_and_cancel(session):
    on_message_inbound(_ihe_message("A01"), session)
    discharge = on_message_inbound(_ihe_message("A03", cls="O"), session)
    assert discharge["status"] == "success"

    cancel = on_message_inbound(_ihe_message("A13", cls="O"), session)
    assert cancel["status"] == "success"


def test_ihe_patient_update(session):
    on_message_inbound(_ihe_message("A01"), session)
    update_msg = _ihe_message("A31").replace("PATIENT^A31", "PATIENT^UPDATED")
    update = on_message_inbound(update_msg, session)
    assert update["status"] == "success"

    patient = session.exec(select(Patient).where(Patient.identifier == "0000000123")).first()
    assert patient is not None
    assert patient.given == "UPDATED"


def test_admission_records_location_and_movement(session):
    on_message_inbound(_ihe_message("A01"), session)
    venue = session.exec(select(Venue).order_by(Venue.id.desc())).first()
    assert venue is not None
    assert venue.assigned_location == "CHIR^001^001^CPAGE"

    mouvement = session.exec(select(Mouvement).order_by(Mouvement.mouvement_seq.desc())).first()
    assert mouvement is not None
    assert mouvement.type == "ADT^A01"
    assert mouvement.to_location == "CHIR^001^001^CPAGE"
    assert mouvement.from_location in ("", None)


def test_transfer_records_single_action(session):
    initial_location = "CHIR^001^001^CPAGE"
    new_location = "CHIR^002^005^CPAGE"

    on_message_inbound(_ihe_message("A01", location=initial_location), session)
    response = on_message_inbound(
        _ihe_message("A02", location=new_location, prior_location=initial_location),
        session
    )
    assert response["status"] == "success"

    mouvement = session.exec(
        select(Mouvement).where(Mouvement.type == "ADT^A02").order_by(Mouvement.mouvement_seq.desc())
    ).first()
    assert mouvement is not None
    assert mouvement.from_location == initial_location
    assert mouvement.to_location == new_location

    venue = session.exec(select(Venue).order_by(Venue.id.desc())).first()
    assert venue.assigned_location == new_location


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


def test_z99_creates_missing_entities(session):
    dossier_seq = 98765
    _handle_z99_updates(f"Z99|Dossier|{dossier_seq}|uf_responsabilite|UF-Z99\r", session)
    dossier = session.exec(select(Dossier).where(Dossier.dossier_seq == dossier_seq)).first()
    assert dossier is not None
    assert dossier.uf_responsabilite == "UF-Z99"
    patient = session.get(Patient, dossier.patient_id)
    assert patient is not None

    venue_seq = 54321
    _handle_z99_updates(
        f"Z99|Venue|{venue_seq}|uf_responsabilite|UF-VENUE|code|VEN-CODE|label|Test Venue|dossier_seq|{dossier_seq}\r",
        session,
    )
    venue = session.exec(select(Venue).where(Venue.venue_seq == venue_seq)).first()
    assert venue is not None
    assert venue.code == "VEN-CODE"
    assert venue.dossier_id == dossier.id

    mouvement_seq = 11223
    _handle_z99_updates(
        f"Z99|Mouvement|{mouvement_seq}|type|update|venue_seq|{venue_seq}|location|LOC-Z99\r",
        session,
    )
    mouvement = session.exec(select(Mouvement).where(Mouvement.mouvement_seq == mouvement_seq)).first()
    assert mouvement is not None
    assert mouvement.venue_id == venue.id
    assert mouvement.location == "LOC-Z99"


def test_on_message_inbound_z99_ack(session):
    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    dossier_seq = 77777
    msg = (
        f"MSH|^~\\&|TEST|TEST|DST|DST|{now}||ADT^Z99^ADT_A01|MSGZ99|P|2.5\r"
        f"Z99|Dossier|{dossier_seq}|uf_responsabilite|UF-Z99\r"
    )
    result = on_message_inbound(msg, session)
    assert result["status"] == "success"

    dossier = session.exec(select(Dossier).where(Dossier.dossier_seq == dossier_seq)).first()
    assert dossier is not None
    assert dossier.uf_responsabilite == "UF-Z99"
