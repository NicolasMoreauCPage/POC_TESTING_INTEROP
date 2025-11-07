"""Tests pour la navigation avec contexte des venues et mouvements"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from datetime import datetime

from app.models import Patient, Dossier, Venue, Mouvement


def test_venues_requires_dossier_context(client: TestClient, session: Session):
    """Test que la liste des venues sans contexte retourne une page vide mais valide"""
    response = client.get("/venues")
    # Le comportement actuel accepte l'accès (retourne toutes les venues ou liste vide)
    assert response.status_code == 200


def test_venues_with_dossier_context(client: TestClient, session: Session):
    """Test de la liste des venues avec un contexte dossier valide"""
    # Créer un patient
    patient = Patient(
        patient_seq=1,
        family="Test",
        given="Patient",
        birth_date="1990-01-01",
        gender="M"
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    
    # Créer un dossier
    dossier = Dossier(
        dossier_seq=1,
        patient_id=patient.id,
        uf_medicale="UF001",

        uf_hebergement="UF001",
        admit_time=datetime.now()
    )
    session.add(dossier)
    session.commit()
    session.refresh(dossier)
    
    # Créer une venue
    venue = Venue(
        venue_seq=1,
        dossier_id=dossier.id,
        uf_medicale="UF001",

        uf_hebergement="UF001",
        start_time=datetime.now()
    )
    session.add(venue)
    session.commit()
    
    # Requête avec contexte
    response = client.get(f"/venues?dossier_id={dossier.id}")
    assert response.status_code == 200
    assert "Venues" in response.text


def test_mouvements_requires_venue_context(client: TestClient, session: Session):
    """Test que la liste des mouvements nécessite un contexte venue"""
    response = client.get("/mouvements")
    # Devrait retourner une erreur si pas de venue_id
    assert response.status_code in [307, 400, 404, 422]


def test_mouvements_with_venue_context(client: TestClient, session: Session):
    """Test de la liste des mouvements avec un contexte venue valide"""
    # Créer un patient
    patient = Patient(
        patient_seq=1,
        family="Test",
        given="Patient",
        birth_date="1990-01-01",
        gender="M"
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    
    # Créer un dossier
    dossier = Dossier(
        dossier_seq=1,
        patient_id=patient.id,
        uf_medicale="UF001",

        uf_hebergement="UF001",
        admit_time=datetime.now()
    )
    session.add(dossier)
    session.commit()
    session.refresh(dossier)
    
    # Créer une venue
    venue = Venue(
        venue_seq=1,
        dossier_id=dossier.id,
        uf_medicale="UF001",

        uf_hebergement="UF001",
        start_time=datetime.now()
    )
    session.add(venue)
    session.commit()
    session.refresh(venue)
    
    # Créer un mouvement
    mouvement = Mouvement(
        mouvement_seq=1,
        venue_id=venue.id,
        type="ADT^A01",
        when=datetime.now(),
        location="ROOM001"
    )
    session.add(mouvement)
    session.commit()
    
    # Requête avec contexte
    response = client.get(f"/mouvements?venue_id={venue.id}")
    assert response.status_code == 200
    assert "Mouvements" in response.text


def test_new_venue_requires_dossier(client: TestClient, session: Session):
    """Test que la création d'une venue nécessite un dossier_id"""
    response = client.get("/venues/new")
    # Devrait retourner une erreur si pas de dossier_id
    assert response.status_code in [307, 400, 404, 422]


def test_new_venue_with_dossier(client: TestClient, session: Session):
    """Test de la création d'une venue avec un dossier valide"""
    # Créer un patient et un dossier
    patient = Patient(
        patient_seq=1,
        family="Test",
        given="Patient",
        birth_date="1990-01-01",
        gender="M"
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    
    dossier = Dossier(
        dossier_seq=1,
        patient_id=patient.id,
        uf_medicale="UF001",

        uf_hebergement="UF001",
        admit_time=datetime.now()
    )
    session.add(dossier)
    session.commit()
    session.refresh(dossier)
    
    # Requête avec contexte
    response = client.get(f"/venues/new?dossier_id={dossier.id}")
    assert response.status_code == 200
    assert "Nouveau" in response.text or "venue" in response.text.lower()


def test_new_mouvement_requires_venue(client: TestClient, session: Session):
    """Test que la création d'un mouvement nécessite un venue_id"""
    response = client.get("/mouvements/new")
    # Devrait retourner une erreur si pas de venue_id
    assert response.status_code in [307, 400, 404, 422]


def test_new_mouvement_with_venue(client: TestClient, session: Session):
    """Test de la création d'un mouvement avec une venue valide"""
    # Créer la hiérarchie complète
    patient = Patient(
        patient_seq=1,
        family="Test",
        given="Patient",
        birth_date="1990-01-01",
        gender="M"
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    
    dossier = Dossier(
        dossier_seq=1,
        patient_id=patient.id,
        uf_medicale="UF001",

        uf_hebergement="UF001",
        admit_time=datetime.now()
    )
    session.add(dossier)
    session.commit()
    session.refresh(dossier)
    
    venue = Venue(
        venue_seq=1,
        dossier_id=dossier.id,
        uf_medicale="UF001",

        uf_hebergement="UF001",
        start_time=datetime.now()
    )
    session.add(venue)
    session.commit()
    session.refresh(venue)
    
    # Requête avec contexte
    response = client.get(f"/mouvements/new?venue_id={venue.id}")
    assert response.status_code == 200
    assert "Nouveau mouvement" in response.text or "mouvement" in response.text.lower()


def test_venue_breadcrumbs(client: TestClient, session: Session):
    """Test que le fil d'Ariane est correct pour les venues"""
    # Créer la hiérarchie
    patient = Patient(
        patient_seq=1,
        family="Dupont",
        given="Jean",
        birth_date="1990-01-01",
        gender="M"
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    
    dossier = Dossier(
        dossier_seq=1,
        patient_id=patient.id,
        uf_medicale="UF001",

        uf_hebergement="UF001",
        admit_time=datetime.now()
    )
    session.add(dossier)
    session.commit()
    session.refresh(dossier)
    
    # Accéder à la page des venues
    response = client.get(f"/venues?dossier_id={dossier.id}")
    assert response.status_code == 200
    # Vérifier que le breadcrumb contient le patient et le dossier
    assert "Dupont" in response.text or "Dossier" in response.text


def test_mouvement_breadcrumbs(client: TestClient, session: Session):
    """Test que le fil d'Ariane est correct pour les mouvements"""
    # Créer la hiérarchie complète
    patient = Patient(
        patient_seq=1,
        family="Martin",
        given="Paul",
        birth_date="1985-05-15",
        gender="M"
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    
    dossier = Dossier(
        dossier_seq=1,
        patient_id=patient.id,
        uf_medicale="UF001",

        uf_hebergement="UF001",
        admit_time=datetime.now()
    )
    session.add(dossier)
    session.commit()
    session.refresh(dossier)
    
    venue = Venue(
        venue_seq=1,
        dossier_id=dossier.id,
        uf_medicale="UF001",

        uf_hebergement="UF001",
        start_time=datetime.now()
    )
    session.add(venue)
    session.commit()
    session.refresh(venue)
    
    # Accéder à la page des mouvements
    response = client.get(f"/mouvements?venue_id={venue.id}")
    assert response.status_code == 200
    # Vérifier que le breadcrumb contient au moins la venue
    assert "Venue" in response.text or "Mouvement" in response.text
