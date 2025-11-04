import pytest
from datetime import datetime
from sqlmodel import select

from app.services.transport_inbound import on_message_inbound
from app.models_identifiers import Identifier, IdentifierType


def _build_message(pid_fields, pv1_fields):
    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    msh = f"MSH|^~\\&|TEST|TEST|DST|DST|{now}||ADT^A01|MSG001|P|2.5\r"
    pid = "|".join(pid_fields) + "\r"
    pv1 = "|".join(pv1_fields) + "\r"
    return "".join([msh, pid, pv1])


def test_pid18_and_pv119_simple_values(session):
    # PID-3 = patient identifier, PID-18 = account number (simple), PV1-19 = visit number (simple)
    pid_fields = [
        "PID",
        "1",
        "",
        "PATID123^^^HOSP^PI",
        "",
        "DOE^JOHN",
        "",
        "19800101",
        "M",
        "",
        "",
        "ADDR^^CITY^^ZIP^FRA",
        "",
        "",
        "",
        "",
        "",
    ]

    # Ensure PID fields length so PID-18 is at index 18
    while len(pid_fields) < 19:
        pid_fields.append("")
    pid_fields[18] = "ACC-12345"

    # PV1 needs at least 20 fields so PV1-19 is at index 19
    pv1_fields = ["PV1"] + [""] * 18 + ["VST-98765"]

    msg = _build_message(pid_fields, pv1_fields)

    res = on_message_inbound(msg, session)
    assert res["status"] == "success"

    # Assert dossier identifier (AN) created
    ident_acc = session.exec(select(Identifier).where(Identifier.value == "ACC-12345")).first()
    assert ident_acc is not None
    assert ident_acc.type == IdentifierType.AN
    assert ident_acc.dossier_id is not None

    # Assert venue identifier (VN) created
    ident_visit = session.exec(select(Identifier).where(Identifier.value == "VST-98765")).first()
    assert ident_visit is not None
    assert ident_visit.type == IdentifierType.VN
    assert ident_visit.venue_id is not None


def test_pid18_and_pv119_cx_form(session):
    # PID-18 and PV1-19 provided in CX form with explicit types AN and VN
    pid18_cx = "ACC-CTX^^^HOSP^AN"
    pv119_cx = "VST-CTX^^^HOSP^VN"

    pid_fields = [
        "PID",
        "1",
        "",
        "PATIDCX^^^HOSP^PI",
        "",
        "SMITH^ALICE",
        "",
        "19950505",
        "F",
    ]
    # pad until index 18
    while len(pid_fields) < 18:
        pid_fields.append("")
    pid_fields.append(pid18_cx)

    pv1_fields = ["PV1"] + [""] * 18 + [pv119_cx]

    msg = _build_message(pid_fields, pv1_fields)

    res = on_message_inbound(msg, session)
    assert res["status"] == "success"

    ident_acc = session.exec(select(Identifier).where(Identifier.value == "ACC-CTX")).first()
    assert ident_acc is not None
    assert ident_acc.type == IdentifierType.AN

    ident_visit = session.exec(select(Identifier).where(Identifier.value == "VST-CTX")).first()
    assert ident_visit is not None
    assert ident_visit.type == IdentifierType.VN
