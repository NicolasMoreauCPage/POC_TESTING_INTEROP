"""Tests pour les espaces de noms et le contexte GHT"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models_structure_fhir import GHTContext, IdentifierNamespace


def test_create_ght_context(session: Session):
    """Test de création d'un contexte GHT"""
    ght = GHTContext(
        name="GHT Test",
        code="GHT_TEST",
        description="Test GHT",
        oid_racine="1.2.250.1.test",
        fhir_server_url="http://test.fhir.com",
        is_active=True
    )
    session.add(ght)
    session.commit()
    session.refresh(ght)
    
    assert ght.id is not None
    assert ght.name == "GHT Test"
    assert ght.code == "GHT_TEST"
    assert ght.oid_racine == "1.2.250.1.test"


def test_create_namespace(session: Session):
    """Test de création d'un espace de noms"""
    # Créer d'abord un GHT
    ght = GHTContext(
        name="GHT Test",
        code="GHT_TEST",
        description="Test GHT",
        is_active=True
    )
    session.add(ght)
    session.commit()
    session.refresh(ght)
    
    # Créer un namespace
    ns = IdentifierNamespace(
        name="IPP",
        system="urn:oid:1.2.250.1.71.1.2.1",
        oid="1.2.250.1.71.1.2.1",
        type="IPP",
        description="Identifiant Patient Permanent",
        ght_context_id=ght.id,
        is_active=True
    )
    session.add(ns)
    session.commit()
    session.refresh(ns)
    
    assert ns.id is not None
    assert ns.name == "IPP"
    assert ns.ght_context_id == ght.id


def test_ght_namespace_relationship(session: Session):
    """Test de la relation GHT <-> Namespaces"""
    # Créer un GHT avec des namespaces
    ght = GHTContext(
        name="GHT Test",
        code="GHT_TEST",
        description="Test GHT",
        is_active=True
    )
    session.add(ght)
    session.commit()
    session.refresh(ght)
    
    # Créer plusieurs namespaces
    ns1 = IdentifierNamespace(
        name="IPP",
        system="urn:oid:1.2.250.1.71.1.2.1",
        type="IPP",
        ght_context_id=ght.id
    )
    ns2 = IdentifierNamespace(
        name="NDA",
        system="urn:oid:1.2.250.1.71.1.2.2",
        type="NDA",
        ght_context_id=ght.id
    )
    session.add(ns1)
    session.add(ns2)
    session.commit()
    
    # Vérifier la relation
    ght_reloaded = session.get(GHTContext, ght.id)
    # Accéder à l'attribut pour forcer le lazy loading
    namespaces = ght_reloaded.namespaces
    
    assert len(namespaces) == 2
    ns_names = [ns.name for ns in namespaces]
    assert "IPP" in ns_names
    assert "NDA" in ns_names


def test_query_namespace_by_type(session: Session):
    """Test de recherche de namespace par type"""
    # Créer un GHT avec des namespaces
    ght = GHTContext(
        name="GHT Test",
        code="GHT_TEST",
        description="Test GHT",
        is_active=True
    )
    session.add(ght)
    session.commit()
    session.refresh(ght)
    
    ns_ipp = IdentifierNamespace(
        name="IPP Hospital A",
        system="urn:oid:1.2.250.1.71.1.2.1",
        type="IPP",
        ght_context_id=ght.id
    )
    ns_nda = IdentifierNamespace(
        name="NDA Hospital A",
        system="urn:oid:1.2.250.1.71.1.2.2",
        type="NDA",
        ght_context_id=ght.id
    )
    session.add(ns_ipp)
    session.add(ns_nda)
    session.commit()
    
    # Rechercher tous les IPP
    ipp_namespaces = session.exec(
        select(IdentifierNamespace).where(
            IdentifierNamespace.type == "IPP",
            IdentifierNamespace.ght_context_id == ght.id
        )
    ).all()
    
    assert len(ipp_namespaces) == 1
    assert ipp_namespaces[0].name == "IPP Hospital A"


def test_inactive_namespace(session: Session):
    """Test de namespace inactif"""
    ght = GHTContext(
        name="GHT Test",
        code="GHT_TEST",
        description="Test GHT",
        is_active=True
    )
    session.add(ght)
    session.commit()
    session.refresh(ght)
    
    ns = IdentifierNamespace(
        name="OLD_IPP",
        system="urn:oid:1.2.250.1.old",
        type="IPP",
        ght_context_id=ght.id,
        is_active=False  # Namespace inactif
    )
    session.add(ns)
    session.commit()
    
    # Rechercher uniquement les namespaces actifs
    active_ns = session.exec(
        select(IdentifierNamespace).where(
            IdentifierNamespace.ght_context_id == ght.id,
            IdentifierNamespace.is_active == True
        )
    ).all()
    
    assert len(active_ns) == 0


def test_ght_demo_interop_initialization(session: Session):
    """Test que le GHT Démo Interop peut être initialisé correctement"""
    # Créer le GHT Démo pour les tests
    ght = session.exec(
        select(GHTContext).where(GHTContext.name == "GHT Démo Interop")
    ).first()
    
    if not ght:
        ght = GHTContext(
            name="GHT Démo Interop",
            code="DEMO_INTEROP",
            description="GHT de démonstration pour tests d'interopérabilité",
            oid_racine="1.2.250.1.xxx.1.1",
            fhir_server_url="http://localhost:8000/fhir",
            is_active=True
        )
        session.add(ght)
        session.commit()
        session.refresh(ght)
        
        # Créer les namespaces standards
        namespaces_config = [
            {"name": "CPAGE", "system": "http://cpage.fr/identifiers", "type": "PI"},
            {"name": "IPP", "system": "http://interop.demo/ns/ipp", "type": "PI"},
            {"name": "NDA", "system": "http://interop.demo/ns/nda", "type": "AN"},
            {"name": "VENUE", "system": "http://interop.demo/ns/venue", "type": "VN"},
        ]
        
        for ns_cfg in namespaces_config:
            ns = IdentifierNamespace(
                name=ns_cfg["name"],
                system=ns_cfg["system"],
                type=ns_cfg["type"],
                ght_context_id=ght.id,
                is_active=True
            )
            session.add(ns)
        session.commit()
        session.refresh(ght)
    
    # Vérifications
    assert ght is not None
    assert ght.code != ""
    assert ght.is_active == True
    
    # Vérifier que les namespaces sont présents
    namespaces = ght.namespaces  # Lazy loading
    assert len(namespaces) >= 4  # Au moins CPAGE, IPP, NDA, VENUE
    
    ns_names = [ns.name for ns in namespaces]
    assert "CPAGE" in ns_names
    assert "IPP" in ns_names
    assert "NDA" in ns_names
    assert "VENUE" in ns_names
