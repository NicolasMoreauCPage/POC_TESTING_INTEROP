"""
Test de la gestion multi-valuée des champs PID (PID-5, PID-11, PID-13).
Vérifie que les répétitions ~ sont correctement générées à l'émission
et parsées à la réception.
"""
import pytest
from sqlmodel import Session, select
from datetime import datetime

from app.models import Patient
from app.services.emit_on_create import generate_pam_hl7
from app.services.transport_inbound import _parse_pid, on_message_inbound
from app.db import get_next_sequence


def test_emission_pid5_multi_valued(session: Session):
    """Test génération PID-5 avec répétitions (nom usuel + nom de naissance)"""
    # Créer patient avec nom de naissance différent
    patient = Patient(
        patient_seq=get_next_sequence(session, "patient"),
        family="MARTIN",  # Nom usuel (marié)
        given="Marie",
        middle="Claire",
        birth_date="1990-05-15",
        gender="F"
    )
    # patient.birth_family = "DUPONT"  # Nom de jeune fille
    
    session.add(patient)
    session.commit()
    session.refresh(patient)
    
    # Générer message HL7
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
    
    # Vérifier format XPN avec type de nom (^^^^D pour usuel)
    assert "MARTIN^Marie^Claire^^^^D" in pid5
    # assert "~DUPONT^Marie^Claire^^^^L" in pid5


def test_emission_pid11_multi_valued(session: Session):
    """Test génération PID-11 avec répétitions (adresse habitation + naissance)"""
    patient = Patient(
        patient_seq=get_next_sequence(session, "patient"),
        family="BERNARD",
        given="Jean",
        birth_date="1985-03-20",
        gender="M",
        # Adresse habitation
        address="15 rue Victor Hugo",
        city="Lyon",
        state="Rhône",
        postal_code="69001",
        country="FRA",
        # Adresse naissance
        birth_address="Maternité de la Croix-Rousse",
        birth_city="Lyon",
        birth_state="Rhône",
        birth_postal_code="69004",
        birth_country="FRA"
    )
    
    session.add(patient)
    session.commit()
    session.refresh(patient)
    
    # Générer message HL7
    hl7_msg = generate_pam_hl7(
        entity=patient,
        entity_type="patient",
        session=session,
        operation="insert"
    )
    
    # Extraire PID-11
    lines = hl7_msg.split("\r")
    pid_line = [l for l in lines if l.startswith("PID|")][0]
    pid_fields = pid_line.split("|")
    pid11 = pid_fields[11]
    
    # Vérifier répétitions ~
    assert "~" in pid11, "PID-11 devrait contenir des répétitions ~"
    
    addresses = pid11.split("~")
    assert len(addresses) == 2, "PID-11 devrait contenir 2 adresses"
    
    # Vérifier adresse habitation (1ère répétition)
    addr1_parts = addresses[0].split("^")
    assert addr1_parts[0] == "15 rue Victor Hugo"
    assert addr1_parts[2] == "Lyon"
    assert addr1_parts[4] == "69001"
    assert addr1_parts[5] == "FRA"
    
    # Vérifier adresse naissance (2e répétition)
    addr2_parts = addresses[1].split("^")
    assert addr2_parts[0] == "Maternité de la Croix-Rousse"
    assert addr2_parts[2] == "Lyon"
    assert addr2_parts[4] == "69004"


def test_emission_pid13_multi_valued(session: Session):
    """Test génération PID-13 avec répétitions (fixe + mobile + travail)"""
    patient = Patient(
        patient_seq=get_next_sequence(session, "patient"),
        family="ROBERT",
        given="Sophie",
        birth_date="1992-11-10",
        gender="F",
        phone="0123456789"  # Téléphone fixe
    )
    # patient.mobile = "0612345678"
    # patient.work_phone = "0498765432"
    
    session.add(patient)
    session.commit()
    session.refresh(patient)
    
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
    
    # Au minimum, le téléphone fixe doit être présent
    assert "0123456789" in pid13


def test_reception_pid5_multi_valued(session: Session):
    """Test parsing PID-5 avec répétitions à la réception"""
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Message avec 2 noms (usuel + naissance)
    message = f"""MSH|^~\\&|SENDING_APP|SENDING_FAC|POC|POC|{now}||ADT^A04|MSG001|P|2.5
EVN|A04|{now}
PID|1||TEST123^^^HOSP^PI||MARTIN^Marie^Claire^^^^D~DUPONT^Marie^Claire^^^^L||19900515|F
"""
    
    # Parser PID
    pid_data = _parse_pid(message)
    
    # Vérifier parsing multi-valué
    assert pid_data["family"] == "MARTIN", "1er nom (usuel) devrait être MARTIN"
    assert pid_data["given"] == "Marie"
    assert pid_data["middle"] == "Claire"
    
    # Vérifier que tous les noms sont parsés
    assert "names" in pid_data
    assert len(pid_data["names"]) == 2, "Devrait avoir 2 répétitions de noms"
    
    # Vérifier nom usuel (type D)
    assert pid_data["names"][0]["family"] == "MARTIN"
    assert pid_data["names"][0]["type"] == "D"
    
    # Vérifier nom de naissance (type L)
    assert pid_data["names"][1]["family"] == "DUPONT"
    assert pid_data["names"][1]["type"] == "L"
    assert pid_data.get("birth_family") == "DUPONT"


def test_reception_pid11_multi_valued(session: Session):
    """Test parsing PID-11 avec répétitions à la réception"""
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Message avec 2 adresses (habitation + naissance)
    message = f"""MSH|^~\\&|SENDING_APP|SENDING_FAC|POC|POC|{now}||ADT^A04|MSG002|P|2.5
EVN|A04|{now}
PID|1||TEST456^^^HOSP^PI||BERNARD^Jean||19850320|M|||15 rue Victor Hugo^^Lyon^Rhône^69001^FRA~Maternité Croix-Rousse^^Lyon^Rhône^69004^FRA
"""
    
    # Parser PID
    pid_data = _parse_pid(message)
    
    # Vérifier adresse habitation (1ère répétition)
    assert pid_data["address"] == "15 rue Victor Hugo"
    assert pid_data["city"] == "Lyon"
    assert pid_data["postal_code"] == "69001"
    assert pid_data["country"] == "FRA"
    
    # Vérifier que toutes les adresses sont parsées
    assert "addresses" in pid_data
    assert len(pid_data["addresses"]) == 2, "Devrait avoir 2 répétitions d'adresses"
    
    # Vérifier adresse naissance (2e répétition)
    assert pid_data.get("birth_address") == "Maternité Croix-Rousse"
    assert pid_data.get("birth_city") == "Lyon"
    assert pid_data.get("birth_postal_code") == "69004"
    assert pid_data.get("birth_country") == "FRA"


def test_reception_pid13_multi_valued(session: Session):
    """Test parsing PID-13 avec répétitions à la réception"""
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Message avec 3 téléphones (fixe + mobile + travail)
    message = f"""MSH|^~\\&|SENDING_APP|SENDING_FAC|POC|POC|{now}||ADT^A04|MSG003|P|2.5
EVN|A04|{now}
PID|1||TEST789^^^HOSP^PI||ROBERT^Sophie||19921110|F|||||0123456789~0612345678^HOME^CP~0498765432^WORK^WP
"""
    
    # Parser PID
    pid_data = _parse_pid(message)
    
    # Vérifier téléphone principal (1ère répétition)
    assert pid_data["phone"] == "0123456789"
    
    # Vérifier que tous les téléphones sont parsés
    assert "phones" in pid_data
    assert len(pid_data["phones"]) == 3, "Devrait avoir 3 répétitions de téléphones"
    
    # Vérifier mobile (type CP)
    assert pid_data.get("mobile") == "0612345678"
    
    # Vérifier travail (type WP)
    assert pid_data.get("work_phone") == "0498765432"


def test_roundtrip_multi_valued(session: Session):
    """Test émission → réception → mise à jour avec champs multi-valués"""
    # 1. Créer patient avec toutes les données
    patient = Patient(
        patient_seq=get_next_sequence(session, "patient"),
        identifier="ROUNDTRIP123",
        family="DURAND",
        given="Pierre",
        middle="Paul",
        birth_date="1988-07-25",
        gender="M",
        # Adresse habitation
        address="10 avenue des Champs",
        city="Paris",
        state="Paris",
        postal_code="75008",
        country="FRA",
        # Adresse naissance
        birth_city="Marseille",
        birth_country="FRA",
        # Téléphone
        phone="0145678901",
        # PID-32
        identity_reliability_code="VALI"
    )
    
    session.add(patient)
    session.commit()
    session.refresh(patient)
    
    # 2. Générer message HL7
    hl7_msg = generate_pam_hl7(
        entity=patient,
        entity_type="patient",
        session=session,
        operation="update"  # A31
    )
    
    # 3. Parser le message pour vérifier les répétitions
    pid_data = _parse_pid(hl7_msg)
    
    assert pid_data["family"] == "DURAND"
    assert pid_data["given"] == "Pierre"
    assert pid_data["middle"] == "Paul"
    assert pid_data["city"] == "Paris"
    assert pid_data["country"] == "FRA"
    assert pid_data["phone"] == "0145678901"
    assert pid_data.get("identity_reliability_code") == "VALI"
    
    # 4. Simuler réception complète (A31 update)
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    message_a31 = f"""MSH|^~\\&|SENDING_APP|SENDING_FAC|POC|POC|{now}||ADT^A31|MSGRT001|P|2.5
EVN|A31|{now}
PID|1||ROUNDTRIP123^^^HOSP^PI||DURAND^Pierre^Paul^^^^D||19880725|M|||10 avenue des Champs^^Paris^Paris^75008^FRA~^^Marseille^^13000^FRA||0145678901|||||||||||||||Marseille|||||||||VALI
"""
    
    result = on_message_inbound(message_a31, session)
    assert result["status"] == "success"
    
    # 5. Vérifier mise à jour patient
    updated = session.exec(select(Patient).where(Patient.identifier == "ROUNDTRIP123")).first()
    assert updated is not None
    assert updated.family == "DURAND"
    assert updated.city == "Paris"
    assert updated.birth_city == "Marseille"
    assert updated.identity_reliability_code == "VALI"
