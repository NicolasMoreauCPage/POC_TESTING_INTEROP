from datetime import datetime

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models_endpoints import MessageLog, SystemEndpoint
from app.models_structure_fhir import GHTContext


def _select_ght_context(client: TestClient, ctx: GHTContext) -> None:
    """Helper to mark a GHT context as active for the client session."""
    response = client.get(f"/admin/ght/{ctx.id}", follow_redirects=True)
    assert response.status_code == 200


def test_messages_page_renders_without_data(client: TestClient) -> None:
    response = client.get("/messages")
    assert response.status_code == 200
    assert "Supervision des messages" in response.text


def test_messages_page_with_sample_data(
    client: TestClient,
    session: Session,
) -> None:
    endpoint = SystemEndpoint(name="Endpoint A", kind="MLLP", role="receiver")
    session.add(endpoint)
    session.commit()
    session.refresh(endpoint)

    log = MessageLog(
        direction="in",
        kind="MLLP",
        endpoint_id=endpoint.id,
        payload="MSH|^~\\&",
        status="received",
        created_at=datetime.utcnow(),
    )
    session.add(log)
    session.commit()

    response = client.get("/messages")
    assert response.status_code == 200
    assert "Endpoint A" in response.text


def test_structure_page_requires_selected_ght(
    client: TestClient,
    session: Session,
) -> None:
    ctx = GHTContext(name="GHT Test", code="GHT-TEST")
    session.add(ctx)
    session.commit()
    session.refresh(ctx)

    _select_ght_context(client, ctx)

    response = client.get("/structure")
    assert response.status_code == 200
    assert "Structure hospitalière" in response.text or "Structure" in response.text


def test_admin_ght_listing(client: TestClient, session: Session) -> None:
    ctx = GHTContext(name="GHT Demo", code="GHT-DEMO")
    session.add(ctx)
    session.commit()

    response = client.get("/admin/ght")
    assert response.status_code == 200
    assert "Sélection du contexte GHT" in response.text
    assert "GHT Demo" in response.text


def test_create_ght_context(client: TestClient, session: Session) -> None:
    payload = {
        "name": "GHT Tests",
        "code": "GHT-TESTS",
        "description": "Contexte de test",
        "is_active": "true",
    }
    response = client.post("/admin/ght/new", data=payload, follow_redirects=True)
    assert response.status_code == 200

    ctx = session.exec(select(GHTContext).where(GHTContext.code == "GHT-TESTS")).first()
    assert ctx is not None
    assert ctx.name == "GHT Tests"


def test_fhir_location_bundle_default(
    client: TestClient,
    session: Session
) -> None:
    # We need to select a GHT context first
    ctx = GHTContext(name="GHT Test", code="GHT-TEST")
    session.add(ctx)
    session.commit()
    session.refresh(ctx)
    _select_ght_context(client, ctx)
    
    response = client.get("/fhir/Location?_format=json")
    assert response.status_code == 200
    body = response.json()
    assert body["resourceType"] == "Bundle"
    assert body["type"] == "searchset"
