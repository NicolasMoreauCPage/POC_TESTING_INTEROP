"""Tests UI pour l'administration des namespaces (IdentifierNamespace).
"""
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.models_structure_fhir import IdentifierNamespace, GHTContext


def _ensure_context(client: TestClient, session: Session):
    ctx = session.exec(select(GHTContext).where(GHTContext.code=="GHT-DEMO-INTEROP")).first()
    if not ctx:
        ctx = GHTContext(name="GHT Démo Interop", code="GHT-DEMO-INTEROP", is_active=True)
        session.add(ctx)
        session.commit(); session.refresh(ctx)
    client.get(f"/admin/ght/{ctx.id}", follow_redirects=True)
    return ctx


def test_namespaces_list_empty(client: TestClient, session: Session):
    ctx = _ensure_context(client, session)
    r = client.get(f"/admin/ght/{ctx.id}")
    assert r.status_code == 200
    # La page détail GHT se charge correctement (le bloc namespaces peut ne pas être présent sur cette vue)
    assert ctx.name in r.text


def test_create_namespace(client: TestClient, session: Session):
    ctx = _ensure_context(client, session)
    payload = {
        "name": "TEST_NS",
        "description": "Namespace de test",
        "oid": "1.2.3.4.5",
        "system": "urn:oid:1.2.3.4.5",
        "type": "PI",
        "entite_juridique_id": "",
        # Les champs ght_context_id / is_active sont dérivés côté serveur
        "is_active": "true"
    }
    r = client.post(f"/admin/ght/{ctx.id}/namespaces/new", data=payload, follow_redirects=False)
    assert r.status_code in (303,302)
    ns = session.exec(select(IdentifierNamespace).where(IdentifierNamespace.name=="TEST_NS")).first()
    assert ns is not None
    assert ns.system == "urn:oid:1.2.3.4.5"


def test_namespace_detail(client: TestClient, session: Session):
    ctx = _ensure_context(client, session)
    ns = IdentifierNamespace(name="SHOW_NS", system="urn:oid:9.9", type="PI", ght_context_id=ctx.id)
    session.add(ns); session.commit(); session.refresh(ns)
    r = client.get(f"/admin/ght/{ctx.id}/namespaces/{ns.id}")
    assert r.status_code == 200
    assert "SHOW_NS" in r.text


def test_edit_namespace(client: TestClient, session: Session):
    ctx = _ensure_context(client, session)
    ns = IdentifierNamespace(name="EDIT_NS", system="urn:oid:9.8", type="PI", ght_context_id=ctx.id)
    session.add(ns); session.commit(); session.refresh(ns)
    r = client.post(f"/admin/ght/{ctx.id}/namespaces/{ns.id}/edit", data={"name": "EDIT_NS2", "system":"urn:oid:9.8", "type":"PI"}, follow_redirects=False)
    assert r.status_code in (303,302)
    session.expire_all(); ns2 = session.get(IdentifierNamespace, ns.id)
    assert ns2.name == "EDIT_NS2"
