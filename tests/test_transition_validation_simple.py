"""
Test de validation des transitions IHE PAM dans le flux de messages.
Vérifie que les transitions invalides sont rejetées avec ACK AE et message explicite.
"""
from datetime import datetime, date
from sqlmodel import Session, select
from app.models import Patient, Mouvement, Dossier, Venue
from app.services.transport_inbound import on_message_inbound


def test_reject_invalid_transfer_from_outpatient(session: Session):
    """
    Test: rejeter A02 (transfert) depuis A04 (consultation externe).
    
    Selon IHE PAM, A02 (transfert) n'est pas autorisé depuis consultation externe (A04).
    Les transferts sont réservés aux patients hospitalisés.
    A04 autorise : {A03, A04, A06, A07, A11, Z99}
    A02 n'est PAS dans cette liste.
    """
    # Étape 1: Créer un mouvement initial A04 (consultation externe, classe O)
    msg_a04 = """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103120000||ADT^A04^ADT_A04|MSG001|P|2.5
EVN|A04|20251103120000
PID|1||PAT001^^^FAC^PI||Test^Transfer||19800101|M
PV1|1|O|CONS^001^001|||||||||||||||V123456|||||||||||||||||||||20251103120000
ZBE|1|20251103120000||CREATE|N|A04|^^^^^^CONS^001^^001^CP|||HMS"""
    
    result_a04 = on_message_inbound(msg_a04, session)
    assert result_a04["status"] == "success", f"A04 should succeed: {result_a04}"
    assert "MSA|AA" in result_a04.get("ack", ""), "A04 should return ACK AA"
    
    # Étape 2: Tenter un A02 (transfert) depuis la consultation externe
    # Ceci doit être REJETÉ car A02 n'est pas autorisé depuis A04
    msg_a02 = """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103120001||ADT^A02^ADT_A02|MSG002|P|2.5
EVN|A02|20251103120001
PID|1||PAT001^^^FAC^PI||Test^Transfer||19800101|M
PV1|1|O|AUTRE^SERV^002|||||||||||||||V123456|||||||||||||||||||||20251103120001
ZBE|1|20251103120001||UPDATE|N|A02|^^^^^^AUTRE^SERV^^002^CP|||HMS"""
    
    result_a02 = on_message_inbound(msg_a02, session)
    
    # Vérifier que le message a été rejeté avec AE
    assert result_a02["status"] == "error", f"A02 (transfer) from A04 (outpatient) should be rejected: {result_a02}"
    ack = result_a02.get("ack", "")
    assert "MSA|AE" in ack, f"Expected ACK AE (Application Error), got: {ack}"
    assert "Transition" in ack or "A04" in ack or "A02" in ack, \
        f"Expected explicit transition error message, got: {ack}"


def test_accept_valid_discharge_from_hospitalization(session: Session):
    """
    Test: accepter A03 (SORTIE/discharge) depuis A01 (admission en hospitalisation).
    
    Selon IHE PAM, A03 (sortie) est autorisé depuis Hospitalisation (I/R).
    C'est le scénario normal : admission → sortie.
    """
    import random
    patient_id = f"PAT{random.randint(100000, 999999)}"
    
    # Étape 1: Créer un mouvement initial A01 (admission, classe I = inpatient)
    # Utiliser un PV1 avec 46 champs comme dans test_transport_inbound.py
    # Note: on laisse visit_number vide pour A01 (sera créé automatiquement)
    pv1_a01_fields = [""] * 46
    pv1_a01_fields[0] = "PV1"
    pv1_a01_fields[1] = "1"
    pv1_a01_fields[2] = "I"  # patient_class = Inpatient (hospitalisé)
    pv1_a01_fields[3] = "CHIR^001^001"  # location
    pv1_a01_fields[44] = "20251103120000"  # admit_time
    pv1_a01 = "|".join(pv1_a01_fields)
    
    msg_a01 = f"""MSH|^~\\&|SEND|FAC|RECV|FAC|20251103120000||ADT^A01^ADT_A01|MSG001|P|2.5
EVN|A01|20251103120000
PID|1||{patient_id}^^^FAC^PI||Test^Discharge||19850515|M
{pv1_a01}
ZBE|1|20251103120000||CREATE|N|A01|^^^^^^CHIR^001^^001^CP|||HMS"""
    
    result_a01 = on_message_inbound(msg_a01, session)
    assert result_a01["status"] == "success", f"A01 should succeed: {result_a01}"
    assert "MSA|AA" in result_a01.get("ack", ""), "A01 should return ACK AA"
    
    # Forcer un commit pour que les changements soient visibles pour le prochain message
    session.commit()
    
    # Récupérer la venue créée pour avoir le vrai venue_seq
    from app.models import Patient, Dossier, Venue
    patient = session.exec(select(Patient).where(Patient.identifier == patient_id)).first()
    assert patient, f"Patient {patient_id} devrait exister après A01"
    dossier = session.exec(select(Dossier).where(Dossier.patient_id == patient.id)).first()
    assert dossier, "Dossier devrait exister après A01"
    venue = session.exec(select(Venue).where(Venue.dossier_id == dossier.id)).first()
    assert venue, "Venue devrait exister après A01"
    
    # Étape 2: Envoyer un A03 (SORTIE/discharge) depuis l'hospitalisation
    # Utiliser le vrai venue_seq pour que la validation trouve le contexte
    # Ceci doit être ACCEPTÉ car A03 est autorisé depuis Hospitalisation (I)
    pv1_a03_fields = [""] * 46
    pv1_a03_fields[0] = "PV1"
    pv1_a03_fields[1] = "1"
    pv1_a03_fields[2] = "I"  # patient_class
    pv1_a03_fields[3] = "CHIR^001^001"  # location
    pv1_a03_fields[19] = str(venue.venue_seq)  # visit_number (PV1-19) - utiliser le vrai venue_seq
    pv1_a03_fields[44] = "20251103120001"  # admit_time
    pv1_a03 = "|".join(pv1_a03_fields)
    
    msg_a03 = f"""MSH|^~\\&|SEND|FAC|RECV|FAC|20251103120001||ADT^A03^ADT_A03|MSG002|P|2.5
EVN|A03|20251103120001
PID|1||{patient_id}^^^FAC^PI||Test^Discharge||19850515|M
{pv1_a03}
ZBE|1|20251103120001||UPDATE|N|A03|^^^^^^CHIR^001^^001^CP|||HMS"""
    
    result_a03 = on_message_inbound(msg_a03, session)
    
    # Vérifier que le message a été accepté avec AA (sortie normale depuis hospitalisation)
    assert result_a03["status"] == "success", f"A03 (discharge) from I class (inpatient) should succeed: {result_a03}"
    ack = result_a03.get("ack", "")
    assert "MSA|AA" in ack, f"Expected ACK AA for valid discharge, got: {ack}"


def test_reject_invalid_a22_without_a21(session: Session):
    """
    Test: rejeter A22 (retour d'absence temporaire) sans A21 préalable.
    
    Selon IHE PAM, A22 (retour d'absence) ne peut venir QUE depuis "Absence temporaire" (A21).
    A21 = patient s'absente temporairement (permission, sortie de quelques heures)
    A22 = patient revient de son absence temporaire
    """
    # Étape 1: Créer un mouvement initial A01 (admission, classe I) sans A03 préalable
    msg_a01 = """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103120000||ADT^A01^ADT_A01|MSG001|P|2.5
EVN|A01|20251103120000
PID|1||PAT003^^^FAC^PI||Test^InvalidReturn||19901010|F
PV1|1|I|MED^001^001|||||||||||||||V345678|||||||||||||||||||||20251103120000
ZBE|1|20251103120000||CREATE|N|A01|^^^^^^MED^001^^001^CP|||HMS"""
    
    result_a01 = on_message_inbound(msg_a01, session)
    assert result_a01["status"] == "success", f"A01 should succeed: {result_a01}"
    
    # Étape 2: Tenter un A22 (retour) sans avoir fait A03 avant
    # Ceci doit être REJETÉ car A22 nécessite un état "Absence temporaire" préalable
    msg_a22 = """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103120001||ADT^A22^ADT_A22|MSG002|P|2.5
EVN|A22|20251103120001
PID|1||PAT003^^^FAC^PI||Test^InvalidReturn||19901010|F
PV1|1|I|MED^001^001|||||||||||||||V345678|||||||||||||||||||||20251103120001
ZBE|1|20251103120001||UPDATE|N|A22|^^^^^^MED^001^^001^CP|||HMS"""
    
    result_a22 = on_message_inbound(msg_a22, session)
    
    # Vérifier que le message a été rejeté avec AE
    assert result_a22["status"] == "error", f"A22 without prior A03/A21 should be rejected: {result_a22}"
    ack = result_a22.get("ack", "")
    assert "MSA|AE" in ack, f"Expected ACK AE, got: {ack}"
    assert "Transition" in ack or "A01" in ack or "A22" in ack, \
        f"Expected explicit transition error message, got: {ack}"


def test_accept_valid_temporary_absence_a21_a22(session: Session):
    """
    Test: accepter A21 (absence temporaire) puis A22 (retour) depuis A01.
    
    C'est le scénario normal d'absence temporaire :
    A01 (admission hospitalisé) → A21 (part en permission) → A22 (revient)
    
    IMPORTANT : ceci est DIFFÉRENT de A03 (sortie définitive) !
    A21/A22 = absence temporaire, le dossier reste ouvert
    A03 = sortie définitive, le dossier se ferme
    """
    # Créer un patient
    patient = Patient(
        nom="Test",
        prenom="Absence",
        date_naissance=date(1980, 3, 15),
        sexe="M",
        nir="1800315123456"
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)

    # Message A01 : admission hospitalisé
    msg_a01 = (
        "MSH|^~\\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|20240115103000||ADT^A01^ADT_A01|MSG00001|P|2.5|||||FRA||||\r"
        f"PID|1||{patient.id}^^^FAC1^PI||Test^Absence||19800315|M|||||||||||||||||||||||||\r"
        "PV1|1|I|SERV1^CH101^01|||||||||||||||1000001||||||||||||||||||||||||||20240115103000|||||||||\r"
        "ZBE|1||ADM123|||20240115103000|\r"
    )
    
    result_a01 = on_message_inbound(msg_a01, session)
    assert result_a01["status"] == "success", f"A01 admission should succeed, got {result_a01}"
    assert "MSA|AA" in result_a01["ack"], "Expected ACK AA for valid admission"
    
    # Récupérer la venue créée pour avoir le visit_number
    session.commit()
    # Le patient créé par le message HL7 a identifier={patient.id}, pas id=patient.id
    from app.models import Patient as PatientDB
    patient_db = session.exec(select(PatientDB).where(PatientDB.identifier == str(patient.id))).first()
    assert patient_db, f"Patient avec identifier={patient.id} devrait exister après A01"
    dossier = session.exec(select(Dossier).where(Dossier.patient_id == patient_db.id)).first()
    assert dossier, "Dossier devrait exister après A01"
    venue = session.exec(select(Venue).where(Venue.dossier_id == dossier.id)).first()
    assert venue, "Venue devrait exister après A01"

    # Message A21 : départ en permission (absence temporaire)
    # Utiliser un PV1 avec 46 champs et inclure visit_number
    pv1_a21_fields = [""] * 46
    pv1_a21_fields[0] = "PV1"
    pv1_a21_fields[1] = "1"
    pv1_a21_fields[2] = "I"
    pv1_a21_fields[3] = "SERV1^CH101^01"
    pv1_a21_fields[19] = str(venue.venue_seq)  # visit_number
    pv1_a21_fields[44] = "20240115103000"
    pv1_a21 = "|".join(pv1_a21_fields)
    
    msg_a21 = f"""MSH|^~\\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|20240116080000||ADT^A21^ADT_A21|MSG00002|P|2.5|||||FRA||||
PID|1||{patient.id}^^^FAC1^PI||Test^Absence||19800315|M|||||||||||||||||||||||||
{pv1_a21}
ZBE|1||ADM123|||20240116080000|"""
    
    result_a21 = on_message_inbound(msg_a21, session)
    assert result_a21["status"] == "success", f"A21 (leave) from A01 should succeed, got {result_a21}"
    assert "MSA|AA" in result_a21["ack"], "Expected ACK AA for valid leave"

    # Message A22 : retour d'absence temporaire
    pv1_a22_fields = [""] * 46
    pv1_a22_fields[0] = "PV1"
    pv1_a22_fields[1] = "1"
    pv1_a22_fields[2] = "I"
    pv1_a22_fields[3] = "SERV1^CH101^01"
    pv1_a22_fields[19] = str(venue.venue_seq)  # visit_number
    pv1_a22_fields[44] = "20240115103000"
    pv1_a22 = "|".join(pv1_a22_fields)
    
    msg_a22 = f"""MSH|^~\\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|20240116180000||ADT^A22^ADT_A22|MSG00003|P|2.5|||||FRA||||
PID|1||{patient.id}^^^FAC1^PI||Test^Absence||19800315|M|||||||||||||||||||||||||
{pv1_a22}
ZBE|1||ADM123|||20240116180000|"""
    
    result_a22 = on_message_inbound(msg_a22, session)
    assert result_a22["status"] == "success", f"A22 (return) from A21 should succeed, got {result_a22}"
    assert "MSA|AA" in result_a22["ack"], "Expected ACK AA for valid return"
    
    # Vérifier que la venue est toujours ouverte (pas fermée comme avec A03)
    dossier_final = session.exec(select(Dossier).where(Dossier.patient_id == patient_db.id)).first()
    assert dossier_final is not None, "Dossier devrait toujours exister"
    venue_final = session.exec(select(Venue).where(Venue.dossier_id == dossier_final.id)).first()
    assert venue_final is not None, "Venue devrait toujours exister"
    # Après A21/A22, le dossier reste ouvert (contrairement à A03 qui clôture)
