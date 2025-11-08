"""Test de la validation ZBE-9='C' dans le workflow.

Ce test vérifie que :
1. ZBE-9='C' est accepté uniquement dans les messages Z99 sur A01/A04/A05
2. ZBE-9='C' est rejeté si la venue n'est pas en état "planned" ou "active"
3. ZBE-9='C' est rejeté dans les messages non-Z99
"""

from datetime import datetime
from sqlmodel import Session, create_engine, select
from app.models import Patient, Dossier, Venue, Mouvement
from app.services.transport_inbound import on_message_inbound
from app.db import get_next_sequence

# Configuration de test
engine = create_engine("sqlite:///:memory:")


def _create_test_venue(session: Session, operational_status: str = "active") -> tuple[Patient, Dossier, Venue]:
    """Crée un patient, dossier et venue de test."""
    # Créer les tables
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)
    
    patient = Patient(
        patient_seq=get_next_sequence(session, "patient"),
        identifier="TEST123",
        family="TestPatient",
        given="Jean",
        gender="M",
        birth_date="19800101"
    )
    session.add(patient)
    session.flush()
    
    dossier = Dossier(
        dossier_seq=get_next_sequence(session, "dossier"),
        patient_id=patient.id,
        uf_responsabilite="TEST_UF",
        admit_time=datetime.utcnow()
    )
    session.add(dossier)
    session.flush()
    
    venue = Venue(
        venue_seq=get_next_sequence(session, "venue"),
        dossier_id=dossier.id,
        uf_responsabilite="TEST_UF",
        start_time=datetime.utcnow(),
        operational_status=operational_status
    )
    session.add(venue)
    session.flush()
    
    # Créer un mouvement initial A01
    mouvement = Mouvement(
        mouvement_seq=get_next_sequence(session, "mouvement"),
        venue_id=venue.id,
        type="ADT^A01",
        when=datetime.utcnow(),
        trigger_event="A01",
        status="completed"
    )
    session.add(mouvement)
    session.flush()
    
    return patient, dossier, venue


def _build_z99_message(visit_number: int, zbe9_value: str = "C", original_trigger: str = "A01") -> str:
    """Construit un message Z99 avec ZBE-9 et ZBE-6."""
    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return (
        f"MSH|^~\\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|{now}||ADT^Z99^ADT_A01|MSG{now}|P|2.5|||||FRA||||\r"
        f"EVN|Z99|{now}\r"
        f"PID|1||TEST123^^^HOSP^PI||TestPatient^Jean||19800101|M\r"
        f"PV1|1|I|SERV1^CH101^01|||||||||||||||{visit_number}||||||||||||||||||||||||||{now}|||||||||\r"
        f"ZBE|1||{now}|||{original_trigger}|||{zbe9_value}\r"
    )


def test_zbe9_c_accepted_in_active_venue():
    """ZBE-9='C' doit être accepté pour une venue en état 'active'."""
    with Session(engine) as session:
        patient, dossier, venue = _create_test_venue(session, operational_status="active")
        msg = _build_z99_message(venue.venue_seq, zbe9_value="C", original_trigger="A01")
        
        result = on_message_inbound(msg, session)
        
        # Le message doit être accepté (ACK AA)
        assert "MSA|AA" in result, f"Expected AA acknowledgment for active venue, got: {result}"
        print("✓ ZBE-9='C' accepté pour venue active (A01)")


def test_zbe9_c_accepted_in_planned_venue():
    """ZBE-9='C' doit être accepté pour une venue en état 'planned' (préadmission)."""
    with Session(engine) as session:
        patient, dossier, venue = _create_test_venue(session, operational_status="planned")
        # Mettre à jour le trigger initial en A05 (préadmission)
        mouvement = session.exec(
            select(Mouvement).where(Mouvement.venue_id == venue.id)
        ).first()
        if mouvement:
            mouvement.trigger_event = "A05"
            session.add(mouvement)
            session.flush()
        
        msg = _build_z99_message(venue.venue_seq, zbe9_value="C", original_trigger="A05")
        
        result = on_message_inbound(msg, session)
        
        # Le message doit être accepté (ACK AA)
        assert "MSA|AA" in result, f"Expected AA acknowledgment for planned venue, got: {result}"
        print("✓ ZBE-9='C' accepté pour venue planned (A05)")


def test_zbe9_c_rejected_in_cancelled_venue():
    """ZBE-9='C' doit être rejeté pour une venue en état 'cancelled'."""
    with Session(engine) as session:
        patient, dossier, venue = _create_test_venue(session, operational_status="cancelled")
        msg = _build_z99_message(venue.venue_seq, zbe9_value="C", original_trigger="A01")
        
        result = on_message_inbound(msg, session)
        
        # Le message doit être rejeté (ACK AE)
        assert "MSA|AE" in result, f"Expected AE acknowledgment for cancelled venue, got: {result}"
        assert "non autorisé" in result or "état" in result.lower(), "Error message should mention state"
        print("✓ ZBE-9='C' rejeté pour venue cancelled")


def test_zbe9_c_rejected_in_finished_venue():
    """ZBE-9='C' doit être rejeté pour une venue terminée (état 'finished')."""
    with Session(engine) as session:
        patient, dossier, venue = _create_test_venue(session, operational_status="finished")
        msg = _build_z99_message(venue.venue_seq, zbe9_value="C", original_trigger="A01")
        
        result = on_message_inbound(msg, session)
        
        # Le message doit être rejeté (ACK AE)
        assert "MSA|AE" in result, f"Expected AE acknowledgment for finished venue, got: {result}"
        print("✓ ZBE-9='C' rejeté pour venue finished")


def test_zbe9_c_rejected_for_invalid_original_trigger():
    """ZBE-9='C' doit être rejeté si ZBE-6 n'est pas A01/A04/A05."""
    # Ce test vérifie la validation au niveau de pam_validation.py
    from app.services.pam_validation import validate_pam
    
    msg = _build_z99_message(1000, zbe9_value="C", original_trigger="A02")  # A02 = transfert, non autorisé
    result = validate_pam(msg, direction="in", profile="IHE_PAM_FR")
    
    # Doit avoir une erreur ZBE9_C_INVALID_EVENT
    errors = [i for i in result.issues if i.severity == "error" and "ZBE9_C_INVALID_EVENT" in i.code]
    assert len(errors) > 0, f"Expected ZBE9_C_INVALID_EVENT error for A02, got issues: {result.issues}"
    print("✓ ZBE-9='C' rejeté pour événement original invalide (A02)")


def test_zbe9_c_rejected_in_non_z99_message():
    """ZBE-9='C' doit être rejeté dans les messages autres que Z99."""
    from app.services.pam_validation import validate_pam
    
    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    msg = (
        f"MSH|^~\\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|{now}||ADT^A01^ADT_A01|MSG{now}|P|2.5|||||FRA||||\r"
        f"EVN|A01|{now}\r"
        f"PID|1||TEST123^^^HOSP^PI||TestPatient^Jean||19800101|M\r"
        f"PV1|1|I|SERV1^CH101^01|||||||||||||||1000||||||||||||||||||||||||||{now}|||||||||\r"
        f"ZBE|1||{now}||||||C\r"  # ZBE-9='C' dans un A01, non autorisé
    )
    
    result = validate_pam(msg, direction="in", profile="IHE_PAM_FR")
    
    # Doit avoir une erreur ZBE9_C_NOT_Z99
    errors = [i for i in result.issues if i.severity == "error" and "ZBE9_C_NOT_Z99" in i.code]
    assert len(errors) > 0, f"Expected ZBE9_C_NOT_Z99 error for A01, got issues: {result.issues}"
    print("✓ ZBE-9='C' rejeté dans message A01 (non-Z99)")


if __name__ == "__main__":
    print("\n=== Tests validation ZBE-9='C' ===\n")
    
    # Tests de validation syntaxique (pam_validation.py)
    print("Tests de validation syntaxique:")
    test_zbe9_c_rejected_in_non_z99_message()
    test_zbe9_c_rejected_for_invalid_original_trigger()
    
    print("\nTests de validation d'état (workflow):")
    # Tests de validation d'état (transport_inbound.py)
    test_zbe9_c_accepted_in_active_venue()
    test_zbe9_c_accepted_in_planned_venue()
    test_zbe9_c_rejected_in_cancelled_venue()
    test_zbe9_c_rejected_in_finished_venue()
    
    print("\n=== Tous les tests réussis ✓ ===\n")
