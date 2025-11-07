from sqlmodel import Session, select
from app.services.transport_inbound import on_message_inbound
from app.models import Dossier, Patient, Venue

def _get_dossier_for_identifier(session: Session, pid: str) -> Dossier:
    patient = session.exec(select(Patient).where(Patient.identifier == pid)).first()
    assert patient, f"Patient {pid} should exist"
    dossier = session.exec(select(Dossier).where(Dossier.patient_id == patient.id)).first()
    assert dossier, "Dossier should exist"
    return dossier


def test_zbe9_three_separate_responsibilities(session: Session):
    """
    Test that ZBE-9 nature determines which of the 3 separate responsibilities change.
    - For A01 (hospitalization, class I): uf_medicale AND uf_hebergement should be set
    - For A04 (outpatient, class O): only uf_medicale should be set
    - ZBE-9 nature 'M' affects uf_medicale
    - ZBE-9 nature 'H' affects uf_hebergement
    - ZBE-9 nature 'S' affects uf_soins
    """
    # Case 1: A01 with class I (hospitalization) and nature M -> both uf_medicale and uf_hebergement
    msg1 = """MSH|^~\&|SEND|FAC|RECV|FAC|20251103120000||ADT^A01^ADT_A01|MSG001|P|2.5\nEVN|A01|20251103120000\nPID|1||PZBE001^^^FAC^PI||Test^ZBE9||19800101|M\nPV1|1|I|UF_HEB^H001^001|||||||||||||||V111111|||||||||||||||||||||20251103120000\nZBE|1|20251103120000||CREATE|N|A01|^^^^^^MED^UF_MED^^001^CP|||M"""
    r1 = on_message_inbound(msg1, session)
    assert r1["status"] == "success", r1
    dossier = _get_dossier_for_identifier(session, "PZBE001")
    assert dossier.uf_medicale == "UF_MED", f"A01 should set uf_medicale from ZBE-7, got {dossier.uf_medicale}"
    assert dossier.uf_hebergement == "UF_HEB", f"A01 should set uf_hebergement from PV1-3-1, got {dossier.uf_hebergement}"

    # Case 2: A04 with class O (outpatient) -> only uf_medicale
    msg2 = """MSH|^~\&|SEND|FAC|RECV|FAC|20251103120010||ADT^A04^ADT_A01|MSG002|P|2.5\nEVN|A04|20251103120010\nPID|1||PZBE002^^^FAC^PI||Test^ZBE9||19800101|M\nPV1|1|O|CONS^C002^002|||||||||||||||V222222|||||||||||||||||||||20251103120010\nZBE|1|20251103120010||CREATE|N|A04|^^^^^^CONS^UF_CONS^^001^CP|||M"""
    r2 = on_message_inbound(msg2, session)
    assert r2["status"] == "success", r2
    dossier2 = _get_dossier_for_identifier(session, "PZBE002")
    assert dossier2.uf_medicale == "UF_CONS", f"A04 (outpatient) should set uf_medicale, got {dossier2.uf_medicale}"
    assert dossier2.uf_hebergement is None, f"A04 (outpatient) should NOT set uf_hebergement, got {dossier2.uf_hebergement}"

    # Case 3: A01 with nature S -> affects uf_soins independently
    msg3 = """MSH|^~\&|SEND|FAC|RECV|FAC|20251103120020||ADT^A01^ADT_A01|MSG003|P|2.5\nEVN|A01|20251103120020\nPID|1||PZBE003^^^FAC^PI||Test^ZBE9||19800101|M\nPV1|1|I|UF_HEB2^C003^003|||||||||||||||V333333|||||||||||||||||||||20251103120020\nZBE|1|20251103120020||CREATE|N|A01|^^^^^^SOINS^UF_SOINS^^001^CP|||S"""
    r3 = on_message_inbound(msg3, session)
    assert r3["status"] == "success", r3
    dossier3 = _get_dossier_for_identifier(session, "PZBE003")
    assert dossier3.uf_soins == "UF_SOINS", f"Nature S should set uf_soins, got {dossier3.uf_soins}"
    assert dossier3.uf_hebergement == "UF_HEB2", f"A01 should set uf_hebergement from PV1-3-1, got {dossier3.uf_hebergement}"


def test_zbe9_no_change_for_L_and_D(session: Session):
    """
    ZBE-9 'L' (localisation) and 'D' (date) do not change any responsibilities.
    """
    # Start with an admission that sets both uf_medicale and uf_hebergement
    msg_a01 = """MSH|^~\&|SEND|FAC|RECV|FAC|20251103121000||ADT^A01^ADT_A01|MSG010|P|2.5\nEVN|A01|20251103121000\nPID|1||PZBE004^^^FAC^PI||Test^ZBE9||19800101|M\nPV1|1|I|UF_HEB_INIT^C001^001|||||||||||||||V444444|||||||||||||||||||||20251103121000\nZBE|1|20251103121000||CREATE|N|A01|^^^^^^MED^UF_MED_INIT^^001^CP|||M"""
    r_a01 = on_message_inbound(msg_a01, session)
    assert r_a01["status"] == "success", r_a01
    dossier = _get_dossier_for_identifier(session, "PZBE004")
    assert dossier.uf_medicale == "UF_MED_INIT"
    assert dossier.uf_hebergement == "UF_HEB_INIT"

    # Send an update with 'L' (localisation), should not change any UF
    msg_upd = """MSH|^~\&|SEND|FAC|RECV|FAC|20251103121010||ADT^A02^ADT_A02|MSG011|P|2.5\nEVN|A02|20251103121010\nPID|1||PZBE004^^^FAC^PI||Test^ZBE9||19800101|M\nPV1|1|I|NEWLOC^N001^001|||||||||||||||V444444|||||||||||||||||||||20251103121010\nZBE|1|20251103121010||UPDATE|N|A02|^^^^^^MED^NEW_UF^^001^CP|||L"""
    r_upd = on_message_inbound(msg_upd, session)
    assert r_upd["status"] == "success", r_upd
    dossier2 = _get_dossier_for_identifier(session, "PZBE004")
    assert dossier2.uf_medicale == "UF_MED_INIT", f"uf_medicale should remain unchanged on 'L', got {dossier2.uf_medicale}"
    assert dossier2.uf_hebergement == "UF_HEB_INIT", f"uf_hebergement should remain unchanged on 'L', got {dossier2.uf_hebergement}"
