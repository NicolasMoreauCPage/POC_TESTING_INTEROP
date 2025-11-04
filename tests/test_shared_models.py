"""Tests pour les modèles partagés (SystemEndpoint, MessageLog)"""
import pytest
from sqlmodel import Session, select
from datetime import datetime

from app.models_shared import SystemEndpoint, MessageLog
from app.models_structure_fhir import GHTContext


def test_create_system_endpoint(session: Session):
    """Test de création d'un SystemEndpoint"""
    endpoint = SystemEndpoint(
        name="Test MLLP Server",
        kind="MLLP",
        role="receiver",
        host="0.0.0.0",
        port=2575,
        sending_app="TEST_APP",
        sending_facility="TEST_FAC",
        is_enabled=True
    )
    session.add(endpoint)
    session.commit()
    session.refresh(endpoint)
    
    assert endpoint.id is not None
    assert endpoint.name == "Test MLLP Server"
    assert endpoint.kind == "MLLP"
    assert endpoint.port == 2575


def test_create_fhir_endpoint(session: Session):
    """Test de création d'un endpoint FHIR"""
    endpoint = SystemEndpoint(
        name="Test FHIR Server",
        kind="FHIR",
        role="sender",
        base_url="https://fhir.example.com/fhir",
        auth_kind="bearer",
        auth_token="test_token_123",
        is_enabled=True
    )
    session.add(endpoint)
    session.commit()
    session.refresh(endpoint)
    
    assert endpoint.id is not None
    assert endpoint.kind == "FHIR"
    assert endpoint.base_url == "https://fhir.example.com/fhir"
    assert endpoint.auth_kind == "bearer"


def test_endpoint_with_ght_context(session: Session):
    """Test de lien entre endpoint et GHT"""
    # Créer un GHT
    ght = GHTContext(
        name="GHT Test",
        code="GHT_TEST",
        description="Test GHT",
        is_active=True
    )
    session.add(ght)
    session.commit()
    session.refresh(ght)
    
    # Créer un endpoint lié au GHT
    endpoint = SystemEndpoint(
        name="GHT MLLP Server",
        kind="MLLP",
        role="both",
        host="0.0.0.0",
        port=2575,
        ght_context_id=ght.id,
        is_enabled=True
    )
    session.add(endpoint)
    session.commit()
    session.refresh(endpoint)
    
    assert endpoint.ght_context_id == ght.id
    
    # Vérifier la relation inverse
    ght_reloaded = session.get(GHTContext, ght.id)
    endpoints = ght_reloaded.endpoints  # Lazy loading
    assert len(endpoints) == 1
    assert endpoints[0].name == "GHT MLLP Server"


def test_create_message_log(session: Session):
    """Test de création d'un MessageLog"""
    # Créer un endpoint
    endpoint = SystemEndpoint(
        name="Test Endpoint",
        kind="MLLP",
        role="receiver",
        is_enabled=True
    )
    session.add(endpoint)
    session.commit()
    session.refresh(endpoint)
    
    # Créer un message log
    msg_log = MessageLog(
        direction="in",
        kind="MLLP",
        endpoint_id=endpoint.id,
        correlation_id="MSG001",
        status="received",
        payload="MSH|^~\\&|SENDER|...",
        ack_payload="MSH|^~\\&|RECEIVER|...|ACK|..."
    )
    session.add(msg_log)
    session.commit()
    session.refresh(msg_log)
    
    assert msg_log.id is not None
    assert msg_log.direction == "in"
    assert msg_log.kind == "MLLP"
    assert msg_log.endpoint_id == endpoint.id
    assert msg_log.status == "received"


def test_message_log_statuses(session: Session):
    """Test des différents statuts de MessageLog"""
    endpoint = SystemEndpoint(
        name="Test Endpoint",
        kind="MLLP",
        role="receiver",
        is_enabled=True
    )
    session.add(endpoint)
    session.commit()
    session.refresh(endpoint)
    
    statuses = ["received", "sent", "ack_ok", "ack_error", "error"]
    
    for status in statuses:
        msg_log = MessageLog(
            direction="in",
            kind="MLLP",
            endpoint_id=endpoint.id,
            status=status,
            payload=f"Test message {status}"
        )
        session.add(msg_log)
    
    session.commit()
    
    # Vérifier que tous les messages ont été créés
    all_logs = session.exec(select(MessageLog)).all()
    assert len(all_logs) == len(statuses)
    
    # Vérifier qu'on peut filtrer par statut
    error_logs = session.exec(
        select(MessageLog).where(MessageLog.status == "error")
    ).all()
    assert len(error_logs) == 1


def test_query_messages_by_endpoint(session: Session):
    """Test de recherche de messages par endpoint"""
    # Créer deux endpoints
    endpoint1 = SystemEndpoint(
        name="Endpoint 1",
        kind="MLLP",
        role="receiver",
        is_enabled=True
    )
    endpoint2 = SystemEndpoint(
        name="Endpoint 2",
        kind="FHIR",
        role="sender",
        is_enabled=True
    )
    session.add(endpoint1)
    session.add(endpoint2)
    session.commit()
    session.refresh(endpoint1)
    session.refresh(endpoint2)
    
    # Créer des messages pour chaque endpoint
    for i in range(3):
        msg1 = MessageLog(
            direction="in",
            kind="MLLP",
            endpoint_id=endpoint1.id,
            status="received",
            payload=f"Message {i} for endpoint 1"
        )
        session.add(msg1)
    
    for i in range(2):
        msg2 = MessageLog(
            direction="out",
            kind="FHIR",
            endpoint_id=endpoint2.id,
            status="sent",
            payload=f"Message {i} for endpoint 2"
        )
        session.add(msg2)
    
    session.commit()
    
    # Rechercher les messages par endpoint
    endpoint1_logs = session.exec(
        select(MessageLog).where(MessageLog.endpoint_id == endpoint1.id)
    ).all()
    endpoint2_logs = session.exec(
        select(MessageLog).where(MessageLog.endpoint_id == endpoint2.id)
    ).all()
    
    assert len(endpoint1_logs) == 3
    assert len(endpoint2_logs) == 2


def test_message_log_created_at(session: Session):
    """Test que created_at est automatiquement défini"""
    endpoint = SystemEndpoint(
        name="Test Endpoint",
        kind="MLLP",
        role="receiver",
        is_enabled=True
    )
    session.add(endpoint)
    session.commit()
    session.refresh(endpoint)
    
    before = datetime.utcnow()
    
    msg_log = MessageLog(
        direction="in",
        kind="MLLP",
        endpoint_id=endpoint.id,
        status="received",
        payload="Test message"
    )
    session.add(msg_log)
    session.commit()
    session.refresh(msg_log)
    
    after = datetime.utcnow()
    
    assert msg_log.created_at is not None
    assert before <= msg_log.created_at <= after


def test_endpoint_disabled(session: Session):
    """Test d'un endpoint désactivé"""
    endpoint = SystemEndpoint(
        name="Disabled Endpoint",
        kind="MLLP",
        role="receiver",
        is_enabled=False  # Désactivé
    )
    session.add(endpoint)
    session.commit()
    session.refresh(endpoint)
    
    # Vérifier qu'on peut filtrer les endpoints actifs
    active_endpoints = session.exec(
        select(SystemEndpoint).where(SystemEndpoint.is_enabled == True)
    ).all()
    
    # L'endpoint désactivé ne devrait pas être dans la liste
    assert endpoint not in active_endpoints
