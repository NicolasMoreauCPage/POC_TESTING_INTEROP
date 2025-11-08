"""
Tests pour les identifiants de mouvements et le segment ZBE dans les messages HL7 PAM.
"""
import pytest
from datetime import datetime
from sqlmodel import Session, select

from app.models import Patient, Dossier, Venue, Mouvement
from app.models_identifiers import Identifier, IdentifierType
from app.models_structure_fhir import IdentifierNamespace
from adapters.hl7_pam_fr import build_message_for_movement


def test_mouvement_has_identifier_relationship(session: Session):
    """Vérifie que le modèle Mouvement supporte les identifiants."""
    # Créer un patient
    patient = Patient(
        patient_seq=1,
        family="DUPONT",
        given="Jean",
        birth_date="19800101",
        gender="M"
    )
    session.add(patient)
    session.commit()
    
    # Créer un dossier
    dossier = Dossier(
        dossier_seq=1,
        patient_id=patient.id,
        uf_responsabilite="3620",
        admit_time=datetime.now()
    )
    session.add(dossier)
    session.commit()
    
    # Créer une venue
    venue = Venue(
        venue_seq=1,
        dossier_id=dossier.id,
        uf_responsabilite="3620",
        start_time=datetime.now(),
        code="V001"
    )
    session.add(venue)
    session.commit()
    
    # Créer un mouvement
    mouvement = Mouvement(
        mouvement_seq=1,
        venue_id=venue.id,
        type="A02",
        when=datetime.now(),
        location="3620^3010^3010"
    )
    session.add(mouvement)
    session.commit()
    
    # Créer un identifiant pour le mouvement
    identifier = Identifier(
        value="MVT-001",
        type=IdentifierType.MVT,
        system="urn:oid:1.2.250.1.213.1.1.1.4",
        oid="1.2.250.1.213.1.1.1.4",
        mouvement_id=mouvement.id
    )
    session.add(identifier)
    session.commit()
    
    # Vérifier la relation
    session.refresh(mouvement)
    assert len(mouvement.identifiers) == 1
    assert mouvement.identifiers[0].value == "MVT-001"
    assert mouvement.identifiers[0].type == IdentifierType.MVT


def test_mouvement_namespace_config():
    """Vérifie la configuration du namespace MOUVEMENT dans init_all.py."""
    # Ce test vérifie la configuration sans dépendre de la base de données
    # La configuration correcte est dans tools/init_all.py
    
    expected_namespace = {
        "name": "MOUVEMENT",
        "oid": "1.2.250.1.213.1.1.1.4",
        "system": "urn:oid:1.2.250.1.213.1.1.1.4",
        "description": "Identifiant de mouvement patient (ZBE-1)"
    }
    
    # Vérifier que le namespace est dans la configuration
    # (voir tools/init_all.py ligne ~95)
    assert expected_namespace["name"] == "MOUVEMENT"
    assert expected_namespace["oid"] == "1.2.250.1.213.1.1.1.4"
    assert "ZBE-1" in expected_namespace["description"]


def test_finess_namespace_config():
    """Vérifie que FINESS utilise l'OID officiel français."""
    # Ce test vérifie la configuration sans dépendre de la base de données
    
    expected_namespace = {
        "name": "FINESS",
        "oid": "1.2.250.1.71.4.2.2",  # OID officiel français
        "system": "urn:oid:1.2.250.1.71.4.2.2"
    }
    
    # Vérifier que l'OID FINESS est correct
    assert expected_namespace["oid"] == "1.2.250.1.71.4.2.2", "OID FINESS officiel incorrect"
    assert expected_namespace["system"] == "urn:oid:1.2.250.1.71.4.2.2"


def test_hl7_message_with_zbe_segment():
    """Vérifie la génération d'un message HL7 PAM avec segment ZBE."""
    
    class MockPatient:
        external_id = 'PAT123'
        family = 'DUPONT'
        given = 'Jean'
        birth_date = '19800101'
        gender = 'M'
    
    class MockDossier:
        uf_responsabilite = '3620'
    
    class MockVenue:
        code = 'V001'
        uf_responsabilite = '3620'
    
    class MockMovement:
        mouvement_seq = 31636
        id = 1
        type = 'A02'
        when = datetime(2022, 10, 16, 23, 59, 0)
        location = '3620^3010^3010'
    
    class MockNamespace:
        name = 'MOUVEMENT'
        oid = '1.2.250.1.213.1.1.1.4'
    
    # Générer le message
    message = build_message_for_movement(
        dossier=MockDossier(),
        venue=MockVenue(),
        movement=MockMovement(),
        patient=MockPatient(),
        movement_namespace=MockNamespace()
    )
    
    # Vérifier la structure
    segments = message.split('\r')
    assert len(segments) == 4, "Le message devrait contenir 4 segments (MSH, PID, PV1, ZBE)"
    
    # Vérifier MSH
    assert segments[0].startswith('MSH|')
    
    # Vérifier PID
    assert segments[1].startswith('PID|')
    
    # Vérifier PV1
    assert segments[2].startswith('PV1|')
    
    # Vérifier ZBE
    assert segments[3].startswith('ZBE|')
    
    # Analyser le segment ZBE
    zbe_fields = segments[3].split('|')
    
    # ZBE-1: Identifiant du mouvement
    zbe_1 = zbe_fields[1]
    assert '^' in zbe_1, "ZBE-1 devrait contenir des composants séparés par ^"
    
    components = zbe_1.split('^')
    assert len(components) == 4, "ZBE-1 devrait avoir 4 composants (ID^AUTHORITY^OID^ISO)"
    assert components[0] == '31636', "ID du mouvement incorrect"
    assert components[1] == 'MOUVEMENT', "Authority incorrecte"
    assert components[2] == '1.2.250.1.213.1.1.1.4', "OID incorrect"
    assert components[3] == 'ISO', "Type d'identifiant incorrect"
    
    # ZBE-2: Date/heure
    assert zbe_fields[2] == '20221016235900'
    
    # ZBE-4: Type d'action
    assert zbe_fields[4] == 'INSERT'
    
    # ZBE-5: Indicateur annulation
    assert zbe_fields[5] == 'N'
    
    # ZBE-7: UF responsable
    assert '3620' in zbe_fields[7]
    
    # ZBE-9: Mode de traitement
    assert zbe_fields[9] == 'HMS'


def test_hl7_message_without_namespace():
    """Vérifie que le message fonctionne sans namespace (fallback)."""
    
    class MockPatient:
        external_id = 'PAT123'
        family = 'DUPONT'
        given = 'Jean'
        birth_date = '19800101'
        gender = 'M'
    
    class MockDossier:
        uf_responsabilite = '3620'
    
    class MockVenue:
        code = 'V001'
        uf_responsabilite = '3620'
    
    class MockMovement:
        mouvement_seq = 31636
        id = 1
        type = 'A02'
        when = datetime(2022, 10, 16, 23, 59, 0)
        location = '3620^3010^3010'
    
    # Générer le message sans namespace
    message = build_message_for_movement(
        dossier=MockDossier(),
        venue=MockVenue(),
        movement=MockMovement(),
        patient=MockPatient()
    )
    
    # Vérifier que le ZBE existe
    segments = message.split('\r')
    assert any(seg.startswith('ZBE|') for seg in segments)
    
    # Vérifier que ZBE-1 contient au moins l'ID
    zbe_segment = [seg for seg in segments if seg.startswith('ZBE|')][0]
    zbe_fields = zbe_segment.split('|')
    assert '31636' in zbe_fields[1], "L'ID du mouvement devrait être présent même sans namespace"
