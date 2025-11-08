"""Tests UI pour les pages diverses (home, docs, guide, validation, interop, vocabularies).
"""
from fastapi.testclient import TestClient


def test_home_page(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    assert "MedData" in r.text or "FHIR" in r.text


def test_docs_page(client: TestClient):
    r = client.get("/documentation")
    assert r.status_code == 200
    assert "Documentation" in r.text


def test_user_guide_page(client: TestClient):
    r = client.get("/guide")
    assert r.status_code == 200
    assert "Guide" in r.text


def test_validation_page(client: TestClient):
    r = client.get("/validation")
    assert r.status_code == 200
    assert "Validation" in r.text


def test_vocabularies_page(client: TestClient):
    r = client.get("/vocabularies")
    assert r.status_code == 200
    assert "Listes de valeurs" in r.text or "valeurs" in r.text.lower()


def test_interop_page(client: TestClient):
    r = client.get("/interop/mllp/status")
    assert r.status_code == 200
    data = r.json()
    assert "running_ids" in data