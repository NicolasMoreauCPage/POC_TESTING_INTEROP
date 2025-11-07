import pytest
from datetime import datetime
from sqlmodel import Session, select

from app.db import get_next_sequence
from app.models import Patient, Dossier, Venue, Mouvement
from app.services.transport_inbound import on_message_inbound_async


def _now_ts():
    return datetime.now().strftime("%Y%m%d%H%M%S")


@pytest.mark.asyncio
async def test_a06_insert_rejected_if_not_admitted(session: Session):
    """A06 with ZBE-4=INSERT after A13 (discharge) must be rejected."""
    # Arrange: patient with venue, last movement A13 (discharge cancel? actually A13 cancels A03 => previous context not admitted)
    # We'll simulate last event A13 explicitly.
    pat_seq = get_next_sequence(session, "patient")
    p = Patient(patient_seq=pat_seq, identifier=str(pat_seq), family="RULES", given="A06-INSERT")
    session.add(p); session.flush()

    d = Dossier(dossier_seq=get_next_sequence(session, "dossier"), patient_id=p.id, uf_medicale="TEST",
 uf_hebergement="TEST", admit_time=datetime.now())
    session.add(d); session.flush()

    v = Venue(venue_seq=get_next_sequence(session, "venue"), dossier_id=d.id, uf_medicale="TEST",
 uf_hebergement="TEST", start_time=datetime.now(), code="HOSP", label="Hosp")
    session.add(v); session.flush()

    # Last movement A13
    m = Mouvement(venue_id=v.id, mouvement_seq=get_next_sequence(session, "mouvement"), when=datetime.now(), location="MED-101", trigger_event="A13")
    session.add(m); session.commit()

    now = _now_ts()
    msg = f"""MSH|^~\&|SEND|FAC|RECV|FAC|{now}||ADT^A06^ADT_A06|MSG006|P|2.5\n"""
    msg += f"EVN|A06|{now}\n"
    msg += f"PID|1||{p.patient_seq}^^^IPP||Rules^Insert||19800101|M\n"
    msg += f"PV1|1|I|MED-101||||||||||||||||{v.venue_seq}\n"
    # ZBE: ...|ZBE-4=INSERT|ZBE-5=Y|ZBE-6=A06
    msg += "ZBE||" + now + "||INSERT|Y|A06||||\n"

    ack = await on_message_inbound_async(msg, session, None)

    assert "MSA|AE" in ack, ack
    assert "A06" in ack and ("INSERT" in ack or "non admis" in ack)


@pytest.mark.asyncio
async def test_a01_allowed_after_a03(session: Session):
    """A01 after A03 (discharge) must be accepted as a new admission context."""
    pat_seq = get_next_sequence(session, "patient")
    p = Patient(patient_seq=pat_seq, identifier=str(pat_seq), family="RULES", given="A01-after-A03")
    session.add(p); session.flush()

    d = Dossier(dossier_seq=get_next_sequence(session, "dossier"), patient_id=p.id, uf_medicale="TEST",
 uf_hebergement="TEST", admit_time=datetime.now())
    session.add(d); session.flush()

    v = Venue(venue_seq=get_next_sequence(session, "venue"), dossier_id=d.id, uf_medicale="TEST",
 uf_hebergement="TEST", start_time=datetime.now(), code="HOSP", label="Hosp")
    session.add(v); session.flush()

    # Last movement A03 (discharge)
    m = Mouvement(venue_id=v.id, mouvement_seq=get_next_sequence(session, "mouvement"), when=datetime.now(), location="MED-101", trigger_event="A03")
    session.add(m); session.commit()

    now = _now_ts()
    msg = f"""MSH|^~\&|SEND|FAC|RECV|FAC|{now}||ADT^A01^ADT_A01|MSG007|P|2.5\n"""
    msg += f"EVN|A01|{now}\n"
    msg += f"PID|1||{p.patient_seq}^^^IPP||Rules^A01||19800101|M\n"
    msg += f"PV1|1|I|MED-101||||||||||||||||{v.venue_seq}\n"
    msg += "ZBE||" + now + "||INSERT|N|A01||||\n"

    ack = await on_message_inbound_async(msg, session, None)

    assert "MSA|AA" in ack, ack


@pytest.mark.asyncio
async def test_a01_rejected_if_not_start_nor_after_a05_a03(session: Session):
    """A01 after A11 should be rejected by the new constraint."""
    pat_seq = get_next_sequence(session, "patient")
    p = Patient(patient_seq=pat_seq, identifier=str(pat_seq), family="RULES", given="A01-constraint")
    session.add(p); session.flush()

    d = Dossier(dossier_seq=get_next_sequence(session, "dossier"), patient_id=p.id, uf_medicale="TEST",
 uf_hebergement="TEST", admit_time=datetime.now())
    session.add(d); session.flush()

    v = Venue(venue_seq=get_next_sequence(session, "venue"), dossier_id=d.id, uf_medicale="TEST",
 uf_hebergement="TEST", start_time=datetime.now(), code="HOSP", label="Hosp")
    session.add(v); session.flush()

    # Last movement A11
    m = Mouvement(venue_id=v.id, mouvement_seq=get_next_sequence(session, "mouvement"), when=datetime.now(), location="MED-101", trigger_event="A11")
    session.add(m); session.commit()

    now = _now_ts()
    msg = f"""MSH|^~\&|SEND|FAC|RECV|FAC|{now}||ADT^A01^ADT_A01|MSG008|P|2.5\n"""
    msg += f"EVN|A01|{now}\n"
    msg += f"PID|1||{p.patient_seq}^^^IPP||Rules^A01||19800101|M\n"
    msg += f"PV1|1|I|MED-101||||||||||||||||{v.venue_seq}\n"
    msg += "ZBE||" + now + "||INSERT|N|A01||||\n"

    ack = await on_message_inbound_async(msg, session, None)

    assert "MSA|AE" in ack, ack
    assert "autorisé uniquement en début" in ack or "A01" in ack


@pytest.mark.asyncio
async def test_a06_insert_accepted_if_admitted(session: Session):
    """A06 with ZBE-4=INSERT after A01 (admission active) must be accepted."""
    pat_seq = get_next_sequence(session, "patient")
    p = Patient(patient_seq=pat_seq, identifier=str(pat_seq), family="RULES", given="A06-accepted")
    session.add(p); session.flush()

    d = Dossier(dossier_seq=get_next_sequence(session, "dossier"), patient_id=p.id, uf_medicale="TEST",
 uf_hebergement="TEST", admit_time=datetime.now())
    session.add(d); session.flush()

    v = Venue(venue_seq=get_next_sequence(session, "venue"), dossier_id=d.id, uf_medicale="TEST",
 uf_hebergement="TEST", start_time=datetime.now(), code="HOSP", label="Hosp")
    session.add(v); session.flush()

    # Last movement A01 (admission)
    m = Mouvement(venue_id=v.id, mouvement_seq=get_next_sequence(session, "mouvement"), when=datetime.now(), location="MED-101", trigger_event="A01")
    session.add(m); session.commit()

    now = _now_ts()
    msg = f"""MSH|^~\&|SEND|FAC|RECV|FAC|{now}||ADT^A06^ADT_A06|MSG009|P|2.5\n"""
    msg += f"EVN|A06|{now}\n"
    msg += f"PID|1||{p.patient_seq}^^^IPP||Rules^A06||19800101|M\n"
    msg += f"PV1|1|I|MED-201||||||||||||||||{v.venue_seq}\n"
    msg += "ZBE||" + now + "||INSERT|N|A06||||\n"

    ack = await on_message_inbound_async(msg, session, None)

    assert "MSA|AA" in ack, ack


@pytest.mark.asyncio
async def test_a07_insert_accepted_if_admitted(session: Session):
    """A07 with ZBE-4=INSERT after A01 must be accepted."""
    pat_seq = get_next_sequence(session, "patient")
    p = Patient(patient_seq=pat_seq, identifier=str(pat_seq), family="RULES", given="A07-accepted")
    session.add(p); session.flush()

    d = Dossier(dossier_seq=get_next_sequence(session, "dossier"), patient_id=p.id, uf_medicale="TEST",
 uf_hebergement="TEST", admit_time=datetime.now())
    session.add(d); session.flush()

    v = Venue(venue_seq=get_next_sequence(session, "venue"), dossier_id=d.id, uf_medicale="TEST",
 uf_hebergement="TEST", start_time=datetime.now(), code="HOSP", label="Hosp")
    session.add(v); session.flush()

    # Last movement A01 (admission)
    m = Mouvement(venue_id=v.id, mouvement_seq=get_next_sequence(session, "mouvement"), when=datetime.now(), location="MED-101", trigger_event="A01")
    session.add(m); session.commit()

    now = _now_ts()
    msg = f"""MSH|^~\&|SEND|FAC|RECV|FAC|{now}||ADT^A07^ADT_A07|MSG010|P|2.5\n"""
    msg += f"EVN|A07|{now}\n"
    msg += f"PID|1||{p.patient_seq}^^^IPP||Rules^A07||19800101|M\n"
    msg += f"PV1|1|I|MED-202||||||||||||||||{v.venue_seq}\n"
    msg += "ZBE||" + now + "||INSERT|N|A07||||\n"

    ack = await on_message_inbound_async(msg, session, None)

    assert "MSA|AA" in ack, ack


@pytest.mark.asyncio
async def test_a04_allowed_after_a05(session: Session):
    """A04 must be accepted after A05 (préadmission)."""
    pat_seq = get_next_sequence(session, "patient")
    p = Patient(patient_seq=pat_seq, identifier=str(pat_seq), family="RULES", given="A04-accepted-after-A05")
    session.add(p); session.flush()

    d = Dossier(dossier_seq=get_next_sequence(session, "dossier"), patient_id=p.id, uf_medicale="TEST",
 uf_hebergement="TEST", admit_time=datetime.now())
    session.add(d); session.flush()

    v = Venue(venue_seq=get_next_sequence(session, "venue"), dossier_id=d.id, uf_medicale="TEST",
 uf_hebergement="TEST", start_time=datetime.now(), code="HOSP", label="Hosp")
    session.add(v); session.flush()

    # Last movement A05 (préadmission)
    m = Mouvement(venue_id=v.id, mouvement_seq=get_next_sequence(session, "mouvement"), when=datetime.now(), location="MED-101", trigger_event="A05")
    session.add(m); session.commit()

    now = _now_ts()
    msg = f"""MSH|^~\&|SEND|FAC|RECV|FAC|{now}||ADT^A04^ADT_A04|MSG011|P|2.5\n"""
    msg += f"EVN|A04|{now}\n"
    msg += f"PID|1||{p.patient_seq}^^^IPP||Rules^A04||19800101|M\n"
    msg += f"PV1|1|E|CONS-001||||||||||||||||{v.venue_seq}\n"
    msg += "ZBE||" + now + "||INSERT|N|A04||||\n"

    ack = await on_message_inbound_async(msg, session, None)

    assert "MSA|AA" in ack, ack


@pytest.mark.asyncio
async def test_a04_rejected_if_not_start_nor_after_a05_a03(session: Session):
    """A04 after A11 must be rejected (not start nor A05/A03)."""
    pat_seq = get_next_sequence(session, "patient")
    p = Patient(patient_seq=pat_seq, identifier=str(pat_seq), family="RULES", given="A04-rejected")
    session.add(p); session.flush()

    d = Dossier(dossier_seq=get_next_sequence(session, "dossier"), patient_id=p.id, uf_medicale="TEST",
 uf_hebergement="TEST", admit_time=datetime.now())
    session.add(d); session.flush()

    v = Venue(venue_seq=get_next_sequence(session, "venue"), dossier_id=d.id, uf_medicale="TEST",
 uf_hebergement="TEST", start_time=datetime.now(), code="HOSP", label="Hosp")
    session.add(v); session.flush()

    # Last movement A11 (cancel admission)
    m = Mouvement(venue_id=v.id, mouvement_seq=get_next_sequence(session, "mouvement"), when=datetime.now(), location="MED-101", trigger_event="A11")
    session.add(m); session.commit()

    now = _now_ts()
    msg = f"""MSH|^~\&|SEND|FAC|RECV|FAC|{now}||ADT^A04^ADT_A04|MSG012|P|2.5\n"""
    msg += f"EVN|A04|{now}\n"
    msg += f"PID|1||{p.patient_seq}^^^IPP||Rules^A04||19800101|M\n"
    msg += f"PV1|1|E|CONS-002||||||||||||||||{v.venue_seq}\n"
    msg += "ZBE||" + now + "||INSERT|N|A04||||\n"

    ack = await on_message_inbound_async(msg, session, None)

    assert "MSA|AE" in ack, ack
    assert "autorisé uniquement en début" in ack or "A04" in ack
