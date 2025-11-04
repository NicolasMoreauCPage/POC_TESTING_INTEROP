"""Tests des profils IHE PIX/PDQ et FHIR PIXm/PDQm."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from datetime import datetime

from app.models import Patient
from app.models_identifiers import Identifier, IdentifierType
from app.models_endpoints import MessageLog, SystemEndpoint
from app.services.pix_pdq_manager import PIXPDQManager

def test_pix_query(client: TestClient, session: Session):
    """Test d'une requête PIX (QBP^Q23)."""
    # 1. Créer un endpoint et un patient test avec plusieurs identifiants
    endpoint = SystemEndpoint(name="PIX", kind="MLLP", role="receiver")
    session.add(endpoint)
    
    patient = Patient(
        family="DUPONT",
        given="Jean",
        birth_date="19800101",
        external_id="P1"
    )
    session.add(patient)
    session.commit()
    
    ids = [
        Identifier(
            patient_id=patient.id,
            system="HOPITAL_A",
            value="ID001",
            type=IdentifierType.PI,
            status="active"
        ),
        Identifier(
            patient_id=patient.id,
            system="HOPITAL_B",
            value="ID002",
            type=IdentifierType.PI,
            status="active"
        )
    ]
    session.add_all(ids)
    session.commit()
    
    # 2. Requête PIX
    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    msg = (
        f"MSH|^~\\&|CLIENT|HOPITAL_A|SERVEUR|DOMAINE|{now}||QBP^Q23^QBP_Q21|{now}|P|2.5\r"
        f"QPD|IHE PIX Query|Q231|ID001^^^HOPITAL_A"
    )
    
    response = client.post("/ihe/pix/query", content=msg)
    assert response.status_code == 200
    
    # Vérifier la réponse HL7
    assert "MSH|" in response.text
    assert "MSA|AA|" in response.text  # ACK positif
    assert "RSP^K23" in response.text
    assert "ID001^^^HOPITAL_A" in response.text
    assert "ID002^^^HOPITAL_B" in response.text
    
    # Vérifier le log
    log = session.exec(
        select(MessageLog)
        .where(MessageLog.kind == "PIX")
        .order_by(MessageLog.created_at.desc())
    ).first()
    assert log is not None
    assert log.status == "processed"
    assert log.message_type == "QBP^Q23"

def test_pdq_query(client: TestClient, session: Session):
    """Test d'une requête PDQ (QBP^Q22)."""
    # 1. Créer un endpoint et plusieurs patients tests
    endpoint = SystemEndpoint(name="PDQ", kind="MLLP", role="receiver")
    session.add(endpoint)
    
    patients = [
        Patient(
            family="DUPONT",
            given="Jean",
            birth_date="19800101",
            external_id="P1"
        ),
        Patient(
            family="DUPONT",
            given="Marie",
            birth_date="19820202",
            external_id="P2"
        )
    ]
    session.add_all(patients)
    session.commit()
    
    # 2. Requête PDQ avec critères
    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    msg = (
        f"MSH|^~\\&|CLIENT|HOPITAL|SERVEUR|DOMAINE|{now}||QBP^Q22^QBP_Q21|{now}|P|2.5\r"
        f"QPD|IHE PDQ Query|Q221|@PID.5.1^DUPONT"
    )
    
    response = client.post("/ihe/pdq/query", content=msg)
    assert response.status_code == 200
    
    # Vérifier la réponse HL7
    assert "MSH|" in response.text
    assert "MSA|AA|" in response.text  # ACK positif
    assert "RSP^K22" in response.text
    assert "DUPONT^Jean" in response.text
    assert "DUPONT^Marie" in response.text
    
    # Test avec critères multiples
    msg = (
        f"MSH|^~\\&|CLIENT|HOPITAL|SERVEUR|DOMAINE|{now}||QBP^Q22^QBP_Q21|{now}|P|2.5\r"
        f"QPD|IHE PDQ Query|Q222|@PID.5.1^DUPONT~@PID.7^19800101"
    )
    
    response = client.post("/ihe/pdq/query", content=msg)
    assert response.status_code == 200
    assert "DUPONT^Jean" in response.text
    assert "DUPONT^Marie" not in response.text
    
    # Vérifier les logs
    logs = session.exec(
        select(MessageLog)
        .where(MessageLog.kind == "PDQ")
        .order_by(MessageLog.created_at)
    ).all()
    assert len(logs) == 2
    assert all(log.status == "processed" for log in logs)
    assert all(log.message_type == "QBP^Q22" for log in logs)

def test_pixm_query(client: TestClient, session: Session):
    """Test d'une requête PIXm."""
    # 1. Créer un patient avec identifiants FHIR
    patient = Patient(
        family="DUPONT",
        given="Jean",
        birth_date="19800101",
        external_id="P1"
    )
    session.add(patient)
    session.commit()
    
    ids = [
        Identifier(
            patient_id=patient.id,
            system="http://hopital-a.fr/id",
            value="ID001",
            type=IdentifierType.PI,
            status="active"
        ),
        Identifier(
            patient_id=patient.id,
            system="http://hopital-b.fr/id",
            value="ID002",
            type=IdentifierType.PI,
            status="active"
        )
    ]
    session.add_all(ids)
    session.commit()
    
    # 2. Requête PIXm
    response = client.post(
        "/ihe/pixm/$ihe-pix",
        params={"sourceIdentifier": "ID001^^^http://hopital-a.fr/id"},
        headers={"Accept": "application/fhir+json"}
    )
    assert response.status_code == 200
    
    # Vérifier le Bundle de réponse
    bundle = response.json()
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "searchset"
    assert bundle["total"] == 2
    
    # Vérifier les identifiants retournés et leur structure
    identifiers = [
        e["resource"]["parameter"][0]["valueIdentifier"]
        for e in bundle["entry"]
    ]
    assert any(i["system"] == "http://hopital-a.fr/id" and i["value"] == "ID001" for i in identifiers)
    assert any(i["system"] == "http://hopital-b.fr/id" and i["value"] == "ID002" for i in identifiers)
    
    # Vérifier le log
    log = session.exec(
        select(MessageLog)
        .where(MessageLog.kind == "PIXm")
        .order_by(MessageLog.created_at.desc())
    ).first()
    assert log is not None
    assert log.status == "processed"

def test_pdqm_search(client: TestClient, session: Session):
    """Test d'une recherche PDQm."""
    # 1. Créer des patients tests
    patients = [
        Patient(
            family="DUPONT",
            given="Jean",
            birth_date="1980-01-01",
            gender="male",
            external_id="P1"
        ),
        Patient(
            family="DUPONT",
            given="Marie", 
            birth_date="1982-02-02",
            gender="female",
            external_id="P2"
        )
    ]
    session.add_all(patients)
    session.commit()
    
    # Ajouter des identifiants
    for p in patients:
        id = Identifier(
            patient_id=p.id,
            system="http://hopital.fr/id",
            value=p.external_id,
            type=IdentifierType.PI,
            status="active"
        )
        session.add(id)
    session.commit()
    
    # 2. Tests des différents critères de recherche
    
    # 2.1 Recherche par nom
    response = client.get(
        "/ihe/pdqm/Patient",
        params={"family": "DUPONT"},
        headers={"Accept": "application/fhir+json"}
    )
    assert response.status_code == 200
    
    bundle = response.json()
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "searchset"
    assert bundle["total"] == 2
    
    # 2.2 Recherche par nom et genre
    response = client.get(
        "/ihe/pdqm/Patient",
        params={"family": "DUPONT", "gender": "male"},
        headers={"Accept": "application/fhir+json"}
    )
    assert response.status_code == 200
    
    bundle = response.json()
    assert bundle["total"] == 1
    patient = bundle["entry"][0]["resource"]
    assert patient["gender"] == "male"
    assert patient["name"][0]["family"] == "DUPONT"
    assert patient["name"][0]["given"][0] == "Jean"
    
    # 2.3 Recherche par date de naissance exacte
    response = client.get(
        "/ihe/pdqm/Patient",
        params={"birthdate": "1980-01-01"},
        headers={"Accept": "application/fhir+json"}
    )
    assert response.status_code == 200
    
    bundle = response.json()
    assert bundle["total"] == 1
    assert bundle["entry"][0]["resource"]["birthDate"] == "1980-01-01"
    
    # 2.4 Recherche par identifiant
    response = client.get(
        "/ihe/pdqm/Patient",
        params={"identifier": "http://hopital.fr/id|P1"},
        headers={"Accept": "application/fhir+json"}
    )
    assert response.status_code == 200
    
    bundle = response.json()
    assert bundle["total"] == 1
    patient = bundle["entry"][0]["resource"]
    assert any(
        i["system"] == "http://hopital.fr/id" and i["value"] == "P1"
        for i in patient["identifier"]
    )
    
    # Vérifier les logs
    logs = session.exec(
        select(MessageLog)
        .where(MessageLog.kind == "PDQm")
        .order_by(MessageLog.created_at)
    ).all()
    assert len(logs) == 4  # Un log par requête
    assert all(log.status == "processed" for log in logs)

def test_error_handling(client: TestClient, session: Session):
    """Test de la gestion des erreurs pour PIX/PDQ/PIXm/PDQm."""
    
    # 1. PIX - Identifiant source inconnu
    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    msg = (
        f"MSH|^~\\&|CLIENT|HOPITAL|SERVEUR|DOMAINE|{now}||QBP^Q23^QBP_Q21|{now}|P|2.5\r"
        f"QPD|IHE PIX Query|Q231|UNKNOWN_ID^^^HOPITAL"
    )
    
    response = client.post("/ihe/pix/query", content=msg)
    assert response.status_code == 200
    assert "MSA|AE|" in response.text  # ACK négatif
    
    # 2. PDQ - Message HL7 malformé
    msg = "MSH|^~\\&|CLIENT|HOPITAL|SERVEUR|DOMAINE|BAD_MESSAGE"
    response = client.post("/ihe/pdq/query", content=msg)
    assert response.status_code == 400
    assert "Invalid HL7 message" in response.text
    
    # 3. PIXm - Paramètre sourceIdentifier manquant
    response = client.post(
        "/ihe/pixm/$ihe-pix",
        headers={"Accept": "application/fhir+json"}
    )
    assert response.status_code in [400, 422]  # 422 = FastAPI validation error for missing parameter
    # For 422 errors, FastAPI uses "detail" key; for our 400 errors we use "message"
    # Just verify we got an error response
    assert response.json() is not None
    
    # 4. PIXm - Format d'identifiant invalide (returns empty bundle, not error)
    response = client.post(
        "/ihe/pixm/$ihe-pix",
        params={"sourceIdentifier": "invalid_format"},
        headers={"Accept": "application/fhir+json"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0  # Should return empty bundle for invalid identifier
    
    # 5. PDQm - Format de date invalide (returns empty bundle, not error)
    response = client.get(
        "/ihe/pdqm/Patient",
        params={"birthdate": "01/01/1980"},  # Format invalide
        headers={"Accept": "application/fhir+json"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0  # Should return empty bundle for no matches
    
    # Vérifier les logs d'erreur
    error_logs = session.exec(
        select(MessageLog)
        .where(MessageLog.status == "error")
        .order_by(MessageLog.created_at)
    ).all()
    assert len(error_logs) > 0  # Au moins un log d'erreur