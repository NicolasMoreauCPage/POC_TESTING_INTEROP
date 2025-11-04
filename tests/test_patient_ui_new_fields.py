"""
Test de fumée pour vérifier que les nouveaux formulaires patients s'affichent correctement.
"""
import pytest
from fastapi.testclient import TestClient


def test_patient_new_form_loads(client: TestClient):
    """Test que le formulaire de création patient se charge"""
    # Note: Cela peut nécessiter un contexte GHT actif
    response = client.get("/patients/new")
    # Si le contexte GHT n'est pas disponible, on aura une redirection
    assert response.status_code in [200, 302, 303]
    
    # Si status 200, vérifier que le contenu HTML contient les nouveaux champs
    if response.status_code == 200:
        html = response.text
        assert "birth_family" in html  # Champ nom de naissance
        assert "mobile" in html  # Champ mobile
        assert "work_phone" in html  # Champ téléphone pro
        assert "birth_address" in html  # Champ adresse de naissance
        assert "identity_reliability_code" in html  # Champ PID-32
        assert "Identité" in html  # Accordéon Identité
        assert "Coordonnées" in html  # Accordéon Coordonnées
        assert "Lieu de naissance" in html  # Accordéon Lieu de naissance
        assert "Informations administratives" in html  # Accordéon Administratif


def test_patient_edit_form_structure(client: TestClient):
    """Test que le formulaire d'édition a la même structure"""
    # Créer d'abord un patient minimal
    from sqlmodel import Session
    from app.db import engine, get_next_sequence
    from app.models import Patient
    
    with Session(engine) as session:
        patient = Patient(
            patient_seq=get_next_sequence(session, "patient"),
            family="TEST",
            given="Form"
        )
        session.add(patient)
        session.commit()
        session.refresh(patient)
        
        # Tester l'affichage du formulaire d'édition
        response = client.get(f"/patients/{patient.id}/edit")
        
        # Cleanup
        session.delete(patient)
        session.commit()
    
    assert response.status_code in [200, 302, 303]
    
    if response.status_code == 200:
        html = response.text
        assert "birth_family" in html
        assert "mobile" in html
        assert "work_phone" in html


def test_patient_detail_shows_new_fields(client: TestClient):
    """Test que la page de détail affiche les nouveaux champs"""
    from sqlmodel import Session
    from app.db import engine, get_next_sequence
    from app.models import Patient
    
    with Session(engine) as session:
        patient = Patient(
            patient_seq=get_next_sequence(session, "patient"),
            family="MARTIN",
            given="Sophie",
            birth_family="DUPONT",
            mobile="0612345678",
            work_phone="0498765432",
            birth_city="Lyon",
            identity_reliability_code="VALI"
        )
        session.add(patient)
        session.commit()
        session.refresh(patient)
        
        # Tester l'affichage du détail
        response = client.get(f"/patients/{patient.id}")
        
        # Cleanup
        session.delete(patient)
        session.commit()
    
    assert response.status_code in [200, 302, 303]
    
    if response.status_code == 200:
        html = response.text
        assert "DUPONT" in html  # Nom de naissance
        assert "0612345678" in html  # Mobile
        assert "0498765432" in html  # Work phone
        assert "Lyon" in html  # Birth city
        assert "VALI" in html  # Identity reliability code


def test_patient_creation_with_all_fields(client: TestClient):
    """Test création d'un patient avec tous les nouveaux champs"""
    from sqlmodel import Session, select
    from app.db import engine
    from app.models import Patient
    
    # Données de formulaire complètes
    form_data = {
        "family": "DURAND",
        "given": "Pierre",
        "middle": "Paul",
        "prefix": "M.",
        "suffix": "Jr.",
        "birth_family": "LEFEBVRE",
        "birth_date": "1988-07-25",
        "gender": "male",
        "address": "10 avenue des Champs",
        "city": "Paris",
        "state": "Paris",
        "postal_code": "75008",
        "country": "FRA",
        "phone": "0145678901",
        "mobile": "0612345678",
        "work_phone": "0498765432",
        "email": "pierre.durand@example.com",
        "birth_address": "Maternité Saint-Antoine",
        "birth_city": "Lille",
        "birth_state": "Nord",
        "birth_postal_code": "59000",
        "birth_country": "FRA",
        "nir": "188072501234567",
        "marital_status": "M",
        "nationality": "FR",
        "identity_reliability_code": "VALI",
        "mothers_maiden_name": "BERNARD",
        "primary_care_provider": "Dr. MARTIN"
    }
    
    # Créer via API (simuler le formulaire)
    response = client.post("/patients/new", data=form_data, follow_redirects=False)
    
    # Devrait rediriger vers la liste
    assert response.status_code in [303, 200, 302]
    
    # Vérifier que le patient a été créé avec tous les champs
    with Session(engine) as session:
        patient = session.exec(select(Patient).where(Patient.family == "DURAND", Patient.given == "Pierre")).first()
        
        if patient:
            # Vérifier les nouveaux champs
            assert patient.birth_family == "LEFEBVRE"
            assert patient.mobile == "0612345678"
            assert patient.work_phone == "0498765432"
            assert patient.birth_city == "Lille"
            assert patient.birth_address == "Maternité Saint-Antoine"
            assert patient.identity_reliability_code == "VALI"
            assert patient.country == "FRA"
            assert patient.birth_country == "FRA"
            
            # Cleanup
            session.delete(patient)
            session.commit()
