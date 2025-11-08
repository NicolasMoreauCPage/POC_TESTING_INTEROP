"""Tests UI pour l'administration des endpoints (SystemEndpoint).
Couvre pages: liste, détail, nouveau, édition, clone structure, transport config.
"""
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.models_endpoints import SystemEndpoint


def _ensure_context(client: TestClient, session: Session):
    from app.models_structure_fhir import GHTContext
    ctx = session.exec(select(GHTContext).where(GHTContext.code=="GHT-DEMO-INTEROP")).first()
    if not ctx:
        ctx = GHTContext(name="GHT Démo Interop", code="GHT-DEMO-INTEROP", is_active=True)
        session.add(ctx)
        session.commit(); session.refresh(ctx)
    r = client.get(f"/admin/ght/{ctx.id}", follow_redirects=True)
    assert r.status_code == 200
    return ctx


def test_endpoints_list_empty(client: TestClient, session: Session):
    _ensure_context(client, session)
    # Utiliser la vue admin pour éviter lazy load sur objet détaché
    r = client.get("/endpoints/admin")
    assert r.status_code == 200
    assert "Systèmes" in r.text or "Endpoints" in r.text


def test_endpoint_create_form(client: TestClient, session: Session):
    _ensure_context(client, session)
    r = client.get("/endpoints/new")
    assert r.status_code == 200
    for field in ["name", "kind", "role"]:
        assert f'name="{field}"' in r.text


def test_create_mllp_endpoint(client: TestClient, session: Session):
    _ensure_context(client, session)
    payload = {
        "name": "MLLP Demo 1",
        "kind": "mllp",
        "role": "receiver",
        "host": "127.0.0.1",
        "port": "2599",
        "sending_app": "XAPP",
        "sending_facility": "XFAC",
        "receiving_app": "MedBridge",
        "receiving_facility": "GHT-DEMO",
        "pam_validate_enabled": "true",
        "pam_validate_mode": "warn",
        "pam_profile": "IHE_PAM_FR"
    }
    # Le handler de création est POST /endpoints/new
    r = client.post("/endpoints/new", data=payload, follow_redirects=False)
    assert r.status_code in (303, 302)
    ep = session.exec(select(SystemEndpoint).where(SystemEndpoint.name=="MLLP Demo 1")).first()
    assert ep is not None
    assert ep.kind.upper() == "MLLP"
    assert ep.role == "receiver"


def test_view_endpoint_detail(client: TestClient, session: Session):
    _ensure_context(client, session)
    ep = SystemEndpoint(name="FHIR Demo", kind="fhir", role="sender", base_url="http://127.0.0.1:8000/fhir")
    session.add(ep); session.commit(); session.refresh(ep)
    r = client.get(f"/endpoints/{ep.id}")
    assert r.status_code == 200
    assert "FHIR Demo" in r.text
    assert "sender" in r.text


def test_edit_endpoint(client: TestClient, session: Session):
    ctx = _ensure_context(client, session)
    ep = SystemEndpoint(name="Edit Me", kind="mllp", role="receiver", host="127.0.0.1", port=2601)
    session.add(ep); session.commit(); session.refresh(ep)
    # L'update nécessite au moins un rattachement GHT ou EJ
    form = {"name": "Edited EP", "kind": "mllp", "role": "receiver", "host": "127.0.0.1", "port": "2602", "ght_context_id": str(ctx.id)}
    r = client.post(f"/endpoints/{ep.id}/update", data=form, follow_redirects=False)
    assert r.status_code in (303,302)
    session.expire_all(); ep2 = session.get(SystemEndpoint, ep.id)
    assert ep2.name == "Edited EP"
    assert ep2.port == 2602


def test_delete_endpoint(client: TestClient, session: Session):
    _ensure_context(client, session)
    ep = SystemEndpoint(name="To Delete", kind="mllp", role="receiver", host="127.0.0.1", port=2603)
    session.add(ep); session.commit(); session.refresh(ep)
    r = client.post(f"/endpoints/{ep.id}/delete", follow_redirects=False)
    assert r.status_code in (303,302)
    # Après suppression, tenter de recharger doit retourner None sans ObjectDeletedError (objet expiré localement)
    session.expunge(ep)
    gone = session.get(SystemEndpoint, ep.id)
    assert gone is None


def test_clone_structure_form_display(client: TestClient, session: Session):
    _ensure_context(client, session)
    src = SystemEndpoint(name="Source EP", kind="fhir", role="receiver", base_url="http://127.0.0.1:8000/fhir")
    session.add(src); session.commit(); session.refresh(src)
    r = client.get(f"/endpoints/{src.id}/clone-structure")
    assert r.status_code == 200
    assert "clone" in r.text.lower()


def test_clone_structure_endpoint_flow(client: TestClient, session: Session):
    _ensure_context(client, session)
    # Créer un endpoint source
    src = SystemEndpoint(name="Source EP", kind="fhir", role="receiver", base_url="http://127.0.0.1:8000/fhir")
    session.add(src); session.commit(); session.refresh(src)
    r = client.get(f"/endpoints/{src.id}/clone-structure")
    assert r.status_code == 200
    assert "Cloner" in r.text or "Clone" in r.text

def test_transport_view_configs(client: TestClient, session: Session):
    _ensure_context(client, session)
    ep = SystemEndpoint(name="Transport EP", kind="mllp", role="receiver", host="127.0.0.1", port=2610)
    session.add(ep); session.commit(); session.refresh(ep)
    # Router transport_views est monté sous /transport et possède déjà un prefix /transport
    r = client.get(f"/transport/transport/endpoints/{ep.id}/transport")
    assert r.status_code == 200
    assert "transport" in r.text.lower()
