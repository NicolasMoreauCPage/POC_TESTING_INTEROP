"""Tests UI navigation de la structure hospitalière (pages racine, filtres, redirections).
"""
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.models_structure import EntiteGeographique, Pole, Service, UniteFonctionnelle
from app.models_structure_fhir import GHTContext


def _ensure_context(client: TestClient, session: Session):
    ctx = session.exec(select(GHTContext).where(GHTContext.code=="GHT-DEMO-INTEROP")).first()
    if not ctx:
        ctx = GHTContext(name="GHT Démo Interop", code="GHT-DEMO-INTEROP", is_active=True)
        session.add(ctx); session.commit(); session.refresh(ctx)
    client.get(f"/admin/ght/{ctx.id}", follow_redirects=True)
    return ctx


def _seed_structure_min(session: Session):
    # Fournir finess obligatoire
    eg = EntiteGeographique(name="EG Demo", identifier="EG_DEMO", physical_type="si", mode="instance", status="active", finess="123456789")
    session.add(eg); session.commit(); session.refresh(eg)
    pole = Pole(name="Pole Demo", identifier="POLE_DEMO", entite_geo_id=eg.id, physical_type="bu", mode="instance", status="active")
    session.add(pole); session.commit(); session.refresh(pole)
    service = Service(name="Service Demo", identifier="SERV_DEMO", pole_id=pole.id, physical_type="wi", mode="instance", status="active", service_type="mco")
    session.add(service); session.commit(); session.refresh(service)
    uf = UniteFonctionnelle(name="UF Demo", identifier="UF_DEMO", service_id=service.id, physical_type="fl", mode="instance", status="active")
    session.add(uf); session.commit(); session.refresh(uf)
    return {"eg": eg, "pole": pole, "service": service, "uf": uf}


def test_structure_root_redirects(client: TestClient, session: Session):
    _ensure_context(client, session)
    r = client.get("/structure")
    assert r.status_code == 200
    assert "Structure hospitalière" in r.text or "Structure" in r.text


def test_structure_eg_listing(client: TestClient, session: Session):
    _ensure_context(client, session)
    data = _seed_structure_min(session)
    r = client.get("/structure/eg")
    assert r.status_code == 200
    assert data["eg"].name in r.text


def test_structure_pole_listing(client: TestClient, session: Session):
    _ensure_context(client, session)
    data = _seed_structure_min(session)
    r = client.get("/structure/poles")
    assert r.status_code == 200
    assert data["pole"].name in r.text


def test_structure_service_listing(client: TestClient, session: Session):
    _ensure_context(client, session)
    data = _seed_structure_min(session)
    r = client.get("/structure/services")
    assert r.status_code == 200
    assert data["service"].name in r.text


def test_structure_uf_listing(client: TestClient, session: Session):
    _ensure_context(client, session)
    data = _seed_structure_min(session)
    r = client.get("/structure/ufs")
    assert r.status_code == 200
    assert data["uf"].name in r.text


# La route /structure/select n'existe pas dans le routeur actuel; test supprimé.


def test_structure_dashboard(client: TestClient, session: Session):
    _ensure_context(client, session)
    r = client.get("/structure")
    assert r.status_code == 200
    # Template structure_new.html
    assert "service_types" in r.text or "Structure" in r.text


def test_structure_uh_listing(client: TestClient, session: Session):
    _ensure_context(client, session)
    data = _seed_structure_min(session)
    # Pas d'UH créée encore -> liste vide mais page accessible
    r = client.get("/structure/uh")
    assert r.status_code == 200
    assert "Unité d'Hébergement" in r.text or "UH" in r.text
