"""
Tests de la gestion des identifiants et des domaines d'identification
"""
import pytest
from datetime import datetime
from sqlmodel import Session, select

from app.models_identifiers import Identifier, IdentifierType
from app.models import Patient
from app.services.identifier_manager import (
    parse_hl7_cx_identifier,
    create_identifier_from_hl7,
    create_fhir_identifier,
    create_identifier_from_fhir,
    get_main_identifier,
    merge_identifiers
)


def test_parse_hl7_cx_identifier():
    """Test du parsing des identifiants HL7 CX"""
    # Test identifiant simple
    value, ns, auth, type_code = parse_hl7_cx_identifier("12345")
    assert value == "12345"
    assert ns == ""
    assert auth is None
    assert type_code is None
    
    # Test identifiant complet (format CX standard: ID^CheckDigit^CheckDigitScheme^AssigningAuthority^TypeCode)
    value, ns, auth, type_code = parse_hl7_cx_identifier("12345^HOPITAL^1.2.3.4^OID_AUTH^PI")
    assert value == "12345"
    assert ns == "OID_AUTH"  # CX-4 = Assigning Authority (system)
    assert auth is None      # Not used
    assert type_code == "PI"


def test_create_identifier_from_hl7(session: Session):
    """Test de création d'identifiant depuis HL7"""
    # Créer un patient pour le test
    patient = Patient(nom="TEST")
    session.add(patient)
    session.commit()
    
    # Test création identifiant (format CX: system à position 3)
    identifier = create_identifier_from_hl7(
        "12345^^^OID_AUTH^PI",
        "patient",
        patient.id
    )
    
    assert identifier.value == "12345"
    assert identifier.system == "OID_AUTH"
    assert identifier.type == IdentifierType.PI
    assert identifier.patient_id == patient.id


def test_fhir_identifier_conversion():
    """Test de conversion FHIR des identifiants"""
    # Créer un identifiant
    identifier = Identifier(
        value="12345",
        system="http://hopital.fr/identifiers",
        type=IdentifierType.PI,
        status="active"
    )
    
    # Convertir en FHIR
    fhir = create_fhir_identifier(identifier)
    assert fhir["value"] == "12345"
    assert fhir["system"] == "http://hopital.fr/identifiers"
    assert fhir["type"]["coding"][0]["code"] == "PI"
    
    # Reconvertir en identifiant
    new_id = create_identifier_from_fhir(fhir)
    assert new_id.value == identifier.value
    assert new_id.system == identifier.system
    assert new_id.type == identifier.type


def test_get_main_identifier():
    """Test de récupération de l'identifiant principal"""
    identifiers = [
        Identifier(value="1", type=IdentifierType.PI, status="inactive"),
        Identifier(value="2", type=IdentifierType.IPP, status="active"),
        Identifier(value="3", type=IdentifierType.VN, status="active")
    ]
    
    # Test avec type spécifique
    main = get_main_identifier(identifiers, IdentifierType.IPP)
    assert main.value == "2"
    
    # Test sans type (premier actif)
    main = get_main_identifier(identifiers)
    assert main.value == "2"
    
    # Test liste vide
    assert get_main_identifier([]) is None


def test_merge_identifiers():
    """Test de fusion des identifiants"""
    existing = [
        Identifier(value="1", system="sys1", status="active"),
        Identifier(value="2", system="sys2", status="inactive")
    ]
    
    new = [
        Identifier(value="1", system="sys1", status="active"),  # Doublon
        Identifier(value="3", system="sys3", status="active")   # Nouveau
    ]
    
    # Test fusion avec conservation des inactifs
    merged = merge_identifiers(existing, new, keep_inactive=True)
    assert len(merged) == 3
    assert any(i.value == "2" for i in merged)  # Inactif conservé
    
    # Test fusion sans conservation des inactifs
    merged = merge_identifiers(existing, new, keep_inactive=False)
    assert len(merged) == 2
    assert all(i.status == "active" for i in merged)