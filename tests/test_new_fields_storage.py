"""
Test complet de bout-en-bout pour les champs birth_family, mobile et work_phone.
Vérifie que les données sont correctement stockées en DB et récupérées.
"""
import pytest
from sqlmodel import Session, select
from datetime import datetime

from app.models import Patient
from app.services.emit_on_create import generate_pam_hl7
from app.services.transport_inbound import on_message_inbound
from app.db import get_next_sequence


def test_birth_family_storage_and_emission(session: Session):
    """Test stockage et émission du nom de naissance (birth_family)"""
    # Créer patient avec nom de naissance
    patient = Patient(
        patient_seq=get_next_sequence(session, "patient"),
        identifier="TEST_BIRTH_FAMILY_001",
        family="MARTIN",  # Nom marital actuel
        given="Sophie",
        birth_family="DUPONT",  # Nom de jeune fille
        birth_date="1985-06-15",
        gender="F"
    )
    
    session.add(patient)
    session.commit()
    session.refresh(patient)
    
    # Vérifier stockage en DB
    assert patient.birth_family == "DUPONT"
    
    # Générer message HL7 et vérifier émission
    hl7_msg = generate_pam_hl7(
        entity=patient,
        entity_type="patient",
        session=session,
        operation="insert"
    )
    
    # Extraire PID-5
    lines = hl7_msg.split("\r")
    pid_line = [l for l in lines if l.startswith("PID|")][0]
    pid_fields = pid_line.split("|")
    pid5 = pid_fields[5]
    
    # Vérifier que les 2 noms sont émis avec répétitions ~
    assert "~" in pid5, "PID-5 devrait contenir une répétition ~"
    names = pid5.split("~")
    assert len(names) == 2, "PID-5 devrait contenir 2 noms"
    
    # Nom usuel (type D)
    assert "MARTIN^Sophie" in names[0]
    assert "^^^^D" in names[0]
    
    # Nom de naissance (type L)
    assert "DUPONT^Sophie" in names[1]
    assert "^^^^L" in names[1]


def test_multiple_phones_storage_and_emission(session: Session):
    """Test stockage et émission de plusieurs téléphones"""
    # Créer patient avec 3 téléphones
    patient = Patient(
        patient_seq=get_next_sequence(session, "patient"),
        identifier="TEST_PHONES_001",
        family="BERNARD",
        given="Jean",
        birth_date="1990-03-20",
        gender="M",
        phone="0123456789",  # Fixe
        mobile="0612345678",  # Mobile
        work_phone="0498765432"  # Travail
    )
    
    session.add(patient)
    session.commit()
    session.refresh(patient)
    
    # Vérifier stockage en DB
    assert patient.phone == "0123456789"
    assert patient.mobile == "0612345678"
    assert patient.work_phone == "0498765432"
    
    # Générer message HL7
    hl7_msg = generate_pam_hl7(
        entity=patient,
        entity_type="patient",
        session=session,
        operation="insert"
    )
    
    # Extraire PID-13
    lines = hl7_msg.split("\r")
    pid_line = [l for l in lines if l.startswith("PID|")][0]
    pid_fields = pid_line.split("|")
    pid13 = pid_fields[13]
    
    # Vérifier répétitions ~
    assert "~" in pid13, "PID-13 devrait contenir des répétitions ~"
    phones = pid13.split("~")
    assert len(phones) == 3, "PID-13 devrait contenir 3 téléphones"
    
    # Vérifier que tous les numéros sont présents
    all_phones_str = "|".join(phones)
    assert "0123456789" in all_phones_str
    assert "0612345678" in all_phones_str
    assert "0498765432" in all_phones_str


def test_complete_reception_and_storage(session: Session):
    """Test réception HL7 complet avec stockage des nouveaux champs"""
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Message HL7 avec tous les champs multi-valués
    # PID-23=BirthPlace, PID-32=IdentityReliabilityCode
    message = f"""MSH|^~\\&|SENDING_APP|SENDING_FAC|POC|POC|{now}||ADT^A04|MSG_FULL_001|P|2.5
EVN|A04|{now}
PID|1||FULL_TEST_001^^^HOSP^PI||MARTIN^Marie^Claire^^^^D~DUPONT^Marie^Claire^^^^L||19850615|F|||15 rue Victor Hugo^^Lyon^Rhône^69001^FRA~^^Marseille^^13000^FRA||0123456789~0698765432^HOME^CP~0487654321^WORK^WP||||||||||Marseille|||||||||VALI
"""
    
    # Traiter le message
    result = on_message_inbound(message, session)
    assert result["status"] == "success"
    
    # Récupérer le patient créé
    patient = session.exec(select(Patient).where(Patient.identifier == "FULL_TEST_001")).first()
    assert patient is not None
    
    # Vérifier tous les champs
    assert patient.family == "MARTIN"
    assert patient.given == "Marie"
    assert patient.middle == "Claire"
    assert patient.birth_family == "DUPONT"  # ✅ Nouveau champ
    
    assert patient.address == "15 rue Victor Hugo"
    assert patient.city == "Lyon"
    assert patient.postal_code == "69001"
    
    assert patient.birth_city == "Marseille"
    assert patient.birth_postal_code == "13000"
    
    assert patient.phone == "0123456789"
    assert patient.mobile == "0698765432"  # ✅ Nouveau champ
    assert patient.work_phone == "0487654321"  # ✅ Nouveau champ
    
    assert patient.identity_reliability_code == "VALI"


def test_roundtrip_with_new_fields(session: Session):
    """Test cycle complet: création → émission → réception → MAJ"""
    # 1. Créer patient avec tous les nouveaux champs
    patient = Patient(
        patient_seq=get_next_sequence(session, "patient"),
        identifier="ROUNDTRIP_FULL_001",
        family="DURAND",
        given="Pierre",
        birth_family="LEFEBVRE",
        birth_date="1988-07-25",
        gender="M",
        address="10 avenue des Champs",
        city="Paris",
        postal_code="75008",
        country="FRA",
        phone="0145678901",
        mobile="0612345678",
        work_phone="0498765432",
        birth_city="Lille",
        identity_reliability_code="VALI"
    )
    
    session.add(patient)
    session.commit()
    session.refresh(patient)
    
    # 2. Émettre message HL7
    hl7_msg = generate_pam_hl7(
        entity=patient,
        entity_type="patient",
        session=session,
        operation="update"
    )
    
    # 3. Vérifier PID-5 (noms)
    pid_line = [l for l in hl7_msg.split("\r") if l.startswith("PID|")][0]
    pid_fields = pid_line.split("|")
    assert "~" in pid_fields[5]  # Répétitions noms
    assert "DURAND" in pid_fields[5] and "LEFEBVRE" in pid_fields[5]
    
    # 4. Vérifier PID-13 (téléphones)
    assert "~" in pid_fields[13]  # Répétitions téléphones
    assert "0145678901" in pid_fields[13]
    assert "0612345678" in pid_fields[13]
    assert "0498765432" in pid_fields[13]
    
    # 5. Modifier et réinjecter (simuler réception)
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    message_update = f"""MSH|^~\\&|SENDING_APP|SENDING_FAC|POC|POC|{now}||ADT^A31|MSGRT_FULL|P|2.5
EVN|A31|{now}
PID|1||ROUNDTRIP_FULL_001^^^HOSP^PI||DURAND^Pierre^^^^D~LEFEBVRE^Pierre^^^^L||19880725|M|||10 avenue des Champs^^Paris^^75008^FRA~^^Lille^^^FRA||0145678901~0612345678^HOME^CP~0498765432^WORK^WP|||||||||||||||Lille|||||||||VALI
"""
    
    result = on_message_inbound(message_update, session)
    assert result["status"] == "success"
    
    # 6. Vérifier MAJ en DB
    updated = session.exec(select(Patient).where(Patient.identifier == "ROUNDTRIP_FULL_001")).first()
    assert updated.family == "DURAND"
    assert updated.birth_family == "LEFEBVRE"
    assert updated.phone == "0145678901"
    assert updated.mobile == "0612345678"
    assert updated.work_phone == "0498765432"
    assert updated.birth_city == "Lille"
    assert updated.identity_reliability_code == "VALI"


def test_partial_phones_no_crash(session: Session):
    """Test que l'absence de mobile/work_phone ne cause pas d'erreur"""
    # Patient avec seulement téléphone fixe
    patient = Patient(
        patient_seq=get_next_sequence(session, "patient"),
        identifier="PARTIAL_PHONE_001",
        family="ROBERT",
        given="Alice",
        birth_date="1995-12-10",
        gender="F",
        phone="0123456789"
        # mobile et work_phone absents
    )
    
    session.add(patient)
    session.commit()
    session.refresh(patient)
    
    # Vérifier stockage
    assert patient.phone == "0123456789"
    assert patient.mobile is None
    assert patient.work_phone is None
    
    # Émettre message HL7 (ne doit pas planter)
    hl7_msg = generate_pam_hl7(
        entity=patient,
        entity_type="patient",
        session=session,
        operation="insert"
    )
    
    # PID-13 doit contenir au moins le fixe
    pid_line = [l for l in hl7_msg.split("\r") if l.startswith("PID|")][0]
    pid_fields = pid_line.split("|")
    assert "0123456789" in pid_fields[13]
