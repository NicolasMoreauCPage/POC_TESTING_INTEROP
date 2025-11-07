from sqlmodel import Session, select
from app.services.transport_inbound import on_message_inbound
from app.models import Dossier, Patient, Venue

def _get_dossier_for_identifier(session: Session, pid: str) -> Dossier:
    patient = session.exec(select(Patient).where(Patient.identifier == pid)).first()
    assert patient, f"Patient {pid} should exist"
    dossier = session.exec(select(Dossier).where(Dossier.patient_id == patient.id)).first()
    assert dossier, "Dossier should exist"
    return dossier


def test_zbe9_priority_M_over_H_over_S(session: Session):
    """
    ZBE-9 priority: M > H > S
    - When 'HMS', UF responsibility should take ZBE-7 (medical) over PV1-3 (hebergement)
    - When 'H' only, take PV1-3 (hebergement)
    - When 'S' only, take ZBE-7 (soins)
    """
    # Case 1: HMS -> pick M from ZBE-7
    msg1 = """MSH|^~\&|SEND|FAC|RECV|FAC|20251103120000||ADT^A01^ADT_A01|MSG001|P|2.5\nEVN|A01|20251103120000\nPID|1||PZBE001^^^FAC^PI||Test^ZBE9||19800101|M\nPV1|1|I|HOSPH^H001^001|||||||||||||||V111111|||||||||||||||||||||20251103120000\nZBE|1|20251103120000||CREATE|N|A01|^^^^^^MED^001^^001^CP|||HMS"""
    r1 = on_message_inbound(msg1, session)
    assert r1["status"] == "success", r1
    dossier = _get_dossier_for_identifier(session, "PZBE001")
    assert dossier.uf_medicale == "001", f"Expected UF from ZBE-7 (M), got {dossier.uf_medicale}"

    # Case 2: H -> pick H (PV1-3-1)
    msg2 = """MSH|^~\&|SEND|FAC|RECV|FAC|20251103120010||ADT^A01^ADT_A01|MSG002|P|2.5\nEVN|A01|20251103120010\nPID|1||PZBE002^^^FAC^PI||Test^ZBE9||19800101|M\nPV1|1|I|HEBERG^H002^002|||||||||||||||V222222|||||||||||||||||||||20251103120010\nZBE|1|20251103120010||CREATE|N|A01|^^^^^^MED^001^^001^CP|||H"""
    r2 = on_message_inbound(msg2, session)
    assert r2["status"] == "success", r2
    dossier2 = _get_dossier_for_identifier(session, "PZBE002")
    assert dossier2.uf_medicale == "HEBERG", f"Expected UF from PV1-3-1 (H), got {dossier2.uf_medicale}"

    # Case 3: S -> pick ZBE-7 (soins)
    msg3 = """MSH|^~\&|SEND|FAC|RECV|FAC|20251103120020||ADT^A01^ADT_A01|MSG003|P|2.5\nEVN|A01|20251103120020\nPID|1||PZBE003^^^FAC^PI||Test^ZBE9||19800101|M\nPV1|1|O|CONS^C003^003|||||||||||||||V333333|||||||||||||||||||||20251103120020\nZBE|1|20251103120020||CREATE|N|A01|^^^^^^SOINS^001^^001^CP|||S"""
    r3 = on_message_inbound(msg3, session)
    assert r3["status"] == "success", r3
    dossier3 = _get_dossier_for_identifier(session, "PZBE003")
    assert dossier3.uf_medicale == "001", f"Expected UF from ZBE-7 (S), got {dossier3.uf_medicale}"


def test_zbe9_no_change_for_L_and_D(session: Session):
    """
    ZBE-9 'L' (localisation) and 'D' (date) do not change responsibility.
    """
    # Start with an admission that sets UF to 001
    msg_a01 = """MSH|^~\&|SEND|FAC|RECV|FAC|20251103121000||ADT^A01^ADT_A01|MSG010|P|2.5\nEVN|A01|20251103121000\nPID|1||PZBE004^^^FAC^PI||Test^ZBE9||19800101|M\nPV1|1|I|CHIR^C001^001|||||||||||||||V444444|||||||||||||||||||||20251103121000\nZBE|1|20251103121000||CREATE|N|A01|^^^^^^MED^001^^001^CP|||M"""
    r_a01 = on_message_inbound(msg_a01, session)
    assert r_a01["status"] == "success", r_a01
    dossier = _get_dossier_for_identifier(session, "PZBE004")
    assert dossier.uf_medicale == "001"

    # Send an update with 'L' (localisation), should not change UF
    msg_upd = """MSH|^~\&|SEND|FAC|RECV|FAC|20251103121010||ADT^A06^ADT_A06|MSG011|P|2.5\nEVN|A06|20251103121010\nPID|1||PZBE004^^^FAC^PI||Test^ZBE9||19800101|M\nPV1|1|I|NEWLOC^N001^001|||||||||||||||V444444|||||||||||||||||||||20251103121010\nZBE|1|20251103121010||UPDATE|N|A06|^^^^^^MED^001^^001^CP|||L"""
    r_upd = on_message_inbound(msg_upd, session)
    assert r_upd["status"] == "success", r_upd
    dossier2 = _get_dossier_for_identifier(session, "PZBE004")
    assert dossier2.uf_medicale == "001", f"UF should remain unchanged on 'L', got {dossier2.uf_medicale}"
