"""
Tests des flux d'identités et mouvements
Scénario complet :
1. Création d'un patient (ADT^A01)
2. Mise à jour des infos patient (ADT^A31)
3. Mouvement du patient (ADT^A02)
4. Sortie du patient (ADT^A03)
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from datetime import datetime

from app.models import Patient, Dossier, Venue, Mouvement
from app.services.transport_inbound import on_message_inbound


def test_complete_patient_workflow(client: TestClient, session: Session, hl7_adt_a01):
    """Test d'un workflow complet patient/dossier/venue/mouvement"""
    # 1. Admission (A01)
    result = on_message_inbound(hl7_adt_a01, session)
    assert result["status"] == "success"
    
    # Vérification création patient
    patient = session.exec(select(Patient).where(Patient.identifier == "12345")).first()
    assert patient is not None
    assert patient.nom == "DUPONT"
    assert patient.prenom == "JEAN"
    
    # Vérification création dossier
    dossier = session.exec(select(Dossier).where(Dossier.patient_id == patient.id)).first()
    assert dossier is not None
    
    # Vérification création venue
    venue = session.exec(select(Venue).where(Venue.dossier_id == dossier.id)).first()
    assert venue is not None
    assert venue.status == "active"
    
    # 2. Mise à jour patient (A31)
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    message_a31 = f"""MSH|^~\\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|{now}||ADT^A31|MSG00002|P|2.5.1|
EVN|A31|{now}||||
PID|1||12345^^^HOPITAL^PI||DUPONT^JEAN-PIERRE^^^^^L||19800101|M|||2 RUE DU TEST^^VILLE^^75002^FRA||0123456789|||||||"""
    
    result = on_message_inbound(message_a31, session)
    assert result["status"] == "success"
    
    # Vérification mise à jour patient
    patient = session.exec(select(Patient).where(Patient.identifier == "12345")).first()
    assert patient.prenom == "JEAN-PIERRE"
    
    # 3. Transfert (A02)
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    message_a02 = f"""MSH|^~\\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|{now}||ADT^A02|MSG00003|P|2.5.1|
EVN|A02|{now}||||
PID|1||12345^^^HOPITAL^PI||DUPONT^JEAN-PIERRE^^^^^L||19800101|M|||2 RUE DU TEST^^VILLE^^75002^FRA||0123456789|||||||
PV1|1|I|NEURO^202^2^HOPITAL||||12345^DOC^JOHN^^^^^||||||||||TRF|A0|||||||||||||||||||||||||{now}|"""
    
    result = on_message_inbound(message_a02, session)
    assert result["status"] == "success"
    
    # Vérification création mouvement
    mouvements = session.exec(select(Mouvement).where(Mouvement.venue_id == venue.id)).all()
    assert len(mouvements) == 2  # Entrée + transfert
    assert mouvements[-1].movement_type == "transfer"  # movement_type contient le label métier, type contient ADT^A02
    
    # 4. Sortie (A03)
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    message_a03 = f"""MSH|^~\\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|{now}||ADT^A03|MSG00004|P|2.5.1|
EVN|A03|{now}||||
PID|1||12345^^^HOPITAL^PI||DUPONT^JEAN-PIERRE^^^^^L||19800101|M|||2 RUE DU TEST^^VILLE^^75002^FRA||0123456789|||||||
PV1|1|O|NEURO^202^2^HOPITAL||||12345^DOC^JOHN^^^^^||||||||||DIS|A0|||||||||||||||||||||||||{now}|"""
    
    result = on_message_inbound(message_a03, session)
    assert result["status"] == "success"
    
    # Vérification statut venue
    venue = session.refresh(venue)
    assert venue.status == "completed"
    
    # Vérification mouvement sortie
    mouvements = session.exec(select(Mouvement).where(Mouvement.venue_id == venue.id)).all()
    assert len(mouvements) == 3  # Entrée + transfert + sortie
    assert mouvements[-1].movement_type == "discharge"  # movement_type contient le label métier, type contient ADT^A03