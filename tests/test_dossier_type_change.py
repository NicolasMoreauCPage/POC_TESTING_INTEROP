import pytest
from datetime import datetime
from sqlmodel import Session, select
from app.models import Dossier, DossierType, Venue, Mouvement
from app.utils.dossier_validators import validate_dossier_type_change, check_movements_compatibility

@pytest.fixture
def dossier(session: Session):
    """Crée un dossier de test"""
    dossier = Dossier(
        dossier_seq=get_next_seq(session, "dossier"),
        patient_id=1,
        uf_responsabilite="TEST",
        admit_time=datetime.now(),
        dossier_type=DossierType.HOSPITALISE
    )
    session.add(dossier)
    session.commit()
    return dossier

@pytest.fixture
def venue(session: Session, dossier: Dossier):
    """Crée une venue de test"""
    venue = Venue(
        venue_seq=get_next_seq(session, "venue"),
        dossier_id=dossier.id,
        uf_responsabilite="TEST",
        start_time=datetime.now()
    )
    session.add(venue)
    session.commit()
    return venue

def get_next_seq(session: Session, name: str) -> int:
    """Helper pour obtenir la prochaine valeur de séquence"""
    from app.db import get_next_sequence
    return get_next_sequence(session, name)

def create_movement(session: Session, venue: Venue, event_type: str):
    """Helper pour créer un mouvement de test"""
    mvt = Mouvement(
        mouvement_seq=get_next_seq(session, "mouvement"),
        venue_id=venue.id,
        type=f"ADT^{event_type}",
        when=datetime.now()
    )
    session.add(mvt)
    session.commit()
    return mvt

def test_compatible_change(session: Session, dossier: Dossier):
    """Test un changement de type compatible sans mouvements"""
    can_change, warnings = validate_dossier_type_change(
        session, dossier, DossierType.EXTERNE
    )
    assert can_change
    assert not warnings

def test_incompatible_movements(session: Session, dossier: Dossier, venue: Venue):
    """Test qu'un changement est bloqué si des mouvements sont incompatibles"""
    # Créer un mouvement de transfert (spécifique aux hospitalisés)
    create_movement(session, venue, "A02")
    
    # Tenter de changer en externe
    can_change, warnings = validate_dossier_type_change(
        session, dossier, DossierType.EXTERNE
    )
    assert not can_change
    assert len(warnings) > 0
    assert "A02" in warnings[0]

def test_multiple_incompatible_movements(session: Session, dossier: Dossier, venue: Venue):
    """Test avec plusieurs mouvements incompatibles"""
    # Créer plusieurs mouvements spécifiques aux hospitalisés
    create_movement(session, venue, "A02")  # Transfert
    create_movement(session, venue, "A21")  # Absence temporaire
    
    can_change, warnings = validate_dossier_type_change(
        session, dossier, DossierType.EXTERNE
    )
    assert not can_change
    assert len(warnings) == 3  # 2 incompatibilités + message de blocage

def test_urgence_to_hospitalise(session: Session, dossier: Dossier, venue: Venue):
    """Test la transition urgence vers hospitalisé"""
    dossier.dossier_type = DossierType.URGENCE
    session.commit()
    
    # Créer un mouvement A04 (arrivée aux urgences)
    create_movement(session, venue, "A04")
    
    # Le changement vers hospitalisé devrait être permis
    can_change, warnings = validate_dossier_type_change(
        session, dossier, DossierType.HOSPITALISE
    )
    assert can_change
    assert not warnings

def test_model_dossier_type_validation(session: Session, dossier: Dossier, venue: Venue):
    """Test que le modèle Dossier valide les changements de type"""
    # Créer un mouvement incompatible
    create_movement(session, venue, "A02")
    
    # Le changement devrait lever une exception
    with pytest.raises(ValueError) as exc:
        dossier.update_type(DossierType.EXTERNE, session)
    
    assert "incompatible" in str(exc.value)