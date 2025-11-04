"""
Tests des interfaces UH et Chambres
"""
import pytest
from fastapi.testclient import TestClient
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select
from app.models_structure import (
    EntiteGeographique, Pole, Service, UniteFonctionnelle,
    UniteHebergement, Chambre, Lit, LocationMode, LocationPhysicalType,
    LocationServiceType, LocationStatus
)
from app.app import app


@pytest.fixture(name="test_structure_hierarchy")
def test_structure_hierarchy_fixture(session: Session):
    """Crée une hiérarchie de test complète"""
    # Création EG
    eg = EntiteGeographique(
        name="Hôpital Test",
        identifier="EG_TEST_001",
        physical_type=LocationPhysicalType.SI,
        finess="123456789",
        mode=LocationMode.INSTANCE,
        status=LocationStatus.ACTIVE,
        part_of=None,
        managing_organization=None
    )
    session.add(eg)
    session.commit()

    # Création Pôle
    pole = Pole(
        name="Pôle Test",
        identifier="POLE_TEST_001",
        entite_geo_id=eg.id,
        physical_type=LocationPhysicalType.BU,
        mode=LocationMode.INSTANCE,
        status=LocationStatus.ACTIVE,
        part_of=eg,
        managing_organization=None
    )
    session.add(pole)
    session.commit()

    # Création Service
    service = Service(
        name="Service Test",
        identifier="SERV_TEST_001",
        pole_id=pole.id,
        physical_type=LocationPhysicalType.WI,
        mode=LocationMode.INSTANCE,
        status=LocationStatus.ACTIVE,
        service_type=LocationServiceType.MCO,
        part_of=pole,
        managing_organization=None
    )
    session.add(service)
    session.commit()

    # Création UF
    uf = UniteFonctionnelle(
        name="UF Test",
        identifier="UF_TEST_001",
        service_id=service.id,
        physical_type=LocationPhysicalType.FL,
        mode=LocationMode.INSTANCE,
        status=LocationStatus.ACTIVE,
        part_of=service,
        managing_organization=None
    )
    session.add(uf)
    session.commit()

    # Création UH
    uh = UniteHebergement(
        name="UH Test",
        identifier="UH_TEST_001",
        unite_fonctionnelle_id=uf.id,
        physical_type=LocationPhysicalType.RO,
        mode=LocationMode.INSTANCE,
        status=LocationStatus.ACTIVE,
        part_of=uf,
        managing_organization=None
    )
    session.add(uh)
    session.commit()

    # Création Chambre
    chambre = Chambre(
        name="101",
        identifier="CHAM_TEST_001",
        unite_hebergement_id=uh.id,
        physical_type=LocationPhysicalType.RO,
        mode=LocationMode.INSTANCE,
        status=LocationStatus.ACTIVE,
        part_of=uh,
        managing_organization=None
    )
    session.add(chambre)
    session.commit()

    # Création Lits
    lit1 = Lit(
        name="101-A",
        identifier="LIT_TEST_001",
        chambre_id=chambre.id,
        physical_type=LocationPhysicalType.BD,
        mode=LocationMode.INSTANCE,
        status=LocationStatus.ACTIVE,
        operationalStatus="free",
        part_of=chambre,
        managing_organization=None
    )
    lit2 = Lit(
        name="101-B",
        identifier="LIT_TEST_002",
        chambre_id=chambre.id,
        physical_type=LocationPhysicalType.BD,
        mode=LocationMode.INSTANCE,
        status=LocationStatus.ACTIVE,
        operationalStatus="occupied",
        part_of=chambre,
        managing_organization=None
    )
    session.add(lit1)
    session.add(lit2)
    session.commit()

    return {
        "eg": eg,
        "pole": pole,
        "service": service,
        "uf": uf,
        "uh": uh,
        "chambre": chambre,
        "lits": [lit1, lit2]
    }


def test_list_unites_hebergement(client: TestClient, test_structure_hierarchy):
    """Test de la liste des UH"""
    response = client.get("/structure/uh")
    assert response.status_code == 200
    assert "UH Test" in response.text
    assert "UF Test" in response.text
    assert "hospitalization" in response.text
    assert "active" in response.text


def test_list_unites_hebergement_with_filters(client: TestClient, test_structure_hierarchy):
    """Test des filtres sur la liste des UH"""
    uf_id = test_structure_hierarchy["uf"].id

    # Test filtre UF
    response = client.get(f"/structure/uh?uf_id={uf_id}")
    assert response.status_code == 200
    assert "UH Test" in response.text

    # Test filtre mode
    response = client.get("/structure/uh?mode=instance")
    assert response.status_code == 200
    assert "UH Test" in response.text

    # Test filtre status
    response = client.get("/structure/uh?status=active")
    assert response.status_code == 200
    assert "UH Test" in response.text

    # Test combinaison de filtres
    response = client.get(f"/structure/uh?uf_id={uf_id}&mode=instance&status=active")
    assert response.status_code == 200
    assert "UH Test" in response.text


def test_view_unite_hebergement_detail(client: TestClient, test_structure_hierarchy):
    """Test de la vue détaillée d'une UH"""
    uh_id = test_structure_hierarchy["uh"].id
    response = client.get(f"/structure/uh/{uh_id}")
    assert response.status_code == 200
    assert "UH Test" in response.text
    assert "101" in response.text  # Numéro de chambre
    # Template shows only the last two chars of the bed name (e.g. '-A')
    assert "-A" in response.text  # Numéro de lit (suffix)
    assert "-B" in response.text  # Numéro de lit (suffix)


def test_new_unite_hebergement_form(client: TestClient):
    """Test du formulaire de création d'UH"""
    response = client.get("/structure/uh/new")
    assert response.status_code == 200
    assert 'name="name"' in response.text
    assert 'name="unite_fonctionnelle_id"' in response.text
    assert 'name="mode"' in response.text
    assert 'name="status"' in response.text


def test_create_unite_hebergement(client: TestClient, test_structure_hierarchy, session: Session):
    """Test de la création d'une UH"""
    uf_id = test_structure_hierarchy["uf"].id

    # Soumission du formulaire
    response = client.post(
        "/structure/uh",
        data={
            "name": "Nouvelle UH",
            "identifier": "UH_TEST_NEW",
            "unite_fonctionnelle_id": str(uf_id),
            "mode": "instance",
            "physical_type": "ro",
            "status": "active",
            "part_of_id": str(test_structure_hierarchy["uf"].id),
            "managing_organization_id": str(test_structure_hierarchy["eg"].id)
        },
        follow_redirects=False
    )
    assert response.status_code == 303  # Redirection après création

    # Vérification en base
    uh = session.exec(
        select(UniteHebergement).where(UniteHebergement.name == "Nouvelle UH")
    ).first()
    assert uh is not None
    assert uh.unite_fonctionnelle_id == uf_id
    assert uh.mode == "instance"
    assert uh.status == "active"


def test_edit_unite_hebergement(client: TestClient, test_structure_hierarchy, session: Session):
    """Test de la modification d'une UH"""
    uh = test_structure_hierarchy["uh"]

    # Soumission du formulaire
    response = client.post(
        f"/structure/uh/{uh.id}",
        data={
            "name": "UH Modifiée",
            "identifier": uh.identifier,
            "unite_fonctionnelle_id": str(uh.unite_fonctionnelle_id),
            "mode": "ambulatory",
            "physical_type": "ro",
            "status": "active",
            "part_of_id": str(test_structure_hierarchy["uf"].id),
            "managing_organization_id": str(test_structure_hierarchy["eg"].id)
        },
        follow_redirects=False
    )
    assert response.status_code == 303  # Redirection après modification

    # Vérification en base
    # Ensure the session sees the committed changes from the app session
    session.expire_all()
    uh_updated = session.get(UniteHebergement, uh.id)
    assert uh_updated.name == "UH Modifiée"
    assert uh_updated.mode == "ambulatory"


def test_delete_unite_hebergement(client: TestClient, test_structure_hierarchy, session: Session):
    """Test de la suppression d'une UH"""
    uh = test_structure_hierarchy["uh"]
    chambre = test_structure_hierarchy["chambre"]
    
    # D'abord on supprime les lits
    for lit in test_structure_hierarchy["lits"]:
        session.delete(lit)
    session.commit()

    # Ensuite on supprime la chambre
    session.delete(chambre)
    session.commit()

    # Tentative de suppression UH
    response = client.post(f"/structure/uh/{uh.id}/delete", follow_redirects=False)
    assert response.status_code == 303  # Redirection après suppression

    # Vérification en base
    # Use a fresh session to avoid identity-map refresh issues
    from sqlmodel import Session as _Session
    from app.db import engine as _engine
    with _Session(_engine) as check_sess:
        uh_deleted = check_sess.get(UniteHebergement, uh.id)
        assert uh_deleted is None


def test_cannot_delete_unite_hebergement_with_active_chambres(
    client: TestClient,
    test_structure_hierarchy
):
    """Test qu'on ne peut pas supprimer une UH avec des chambres actives"""
    uh = test_structure_hierarchy["uh"]

    # Tentative de suppression avec une chambre active
    response = client.post(f"/structure/uh/{uh.id}/delete")
    assert response.status_code == 400  # Bad Request
    assert "chambres actives" in response.text


def test_new_chambre_form(client: TestClient, test_structure_hierarchy):
    """Test du formulaire de création de chambre"""
    uh = test_structure_hierarchy["uh"]
    response = client.get(f"/structure/chambres/new?uh_id={uh.id}")
    assert response.status_code == 200
    assert 'name="name"' in response.text
    assert 'name="physical_type"' in response.text
    assert 'name="status"' in response.text


def test_create_chambre(client: TestClient, test_structure_hierarchy, session: Session):
    """Test de la création d'une chambre"""
    uh = test_structure_hierarchy["uh"]

    # Soumission du formulaire
    response = client.post(
        "/structure/chambres",
        data={
            "name": "102",
            "identifier": "CHAM_TEST_NEW",
            "unite_hebergement_id": str(uh.id),
            "physical_type": "ro",  # room
            "mode": "instance",
            "status": "active",
            "part_of_id": str(test_structure_hierarchy["uh"].id),
            "managing_organization_id": str(test_structure_hierarchy["eg"].id)
        },
        follow_redirects=False
    )
    assert response.status_code == 303  # Redirection après création

    # Vérification en base
    chambre = session.exec(
        select(Chambre).where(Chambre.name == "102")
    ).first()
    assert chambre is not None
    assert chambre.unite_hebergement_id == uh.id
    assert chambre.status == "active"


def test_delete_chambre(client: TestClient, test_structure_hierarchy, session: Session):
    """Test de la suppression d'une chambre"""
    chambre = test_structure_hierarchy["chambre"]
    uh_id = chambre.unite_hebergement_id

    # D'abord on supprime les lits
    for lit in test_structure_hierarchy["lits"]:
        session.delete(lit)
    session.commit()

    # Tentative de suppression
    response = client.post(
        f"/structure/chambres/{chambre.id}/delete",
        follow_redirects=False
    )
    assert response.status_code == 303  # Redirection après suppression

    # Vérification en base
    # Use a fresh session to avoid identity-map refresh issues
    from sqlmodel import Session as _Session
    from app.db import engine as _engine
    with _Session(_engine) as check_sess:
        chambre_deleted = check_sess.get(Chambre, chambre.id)
        assert chambre_deleted is None

    # Vérification redirection vers UH
    assert f"/structure/uh/{uh_id}" in response.headers["location"]


def test_cannot_delete_chambre_with_active_lits(
    client: TestClient,
    test_structure_hierarchy
):
    """Test qu'on ne peut pas supprimer une chambre avec des lits actifs"""
    chambre = test_structure_hierarchy["chambre"]

    # Tentative de suppression avec des lits actifs
    response = client.post(f"/structure/chambres/{chambre.id}/delete")
    assert response.status_code == 400  # Bad Request
    assert "lits actifs" in response.text