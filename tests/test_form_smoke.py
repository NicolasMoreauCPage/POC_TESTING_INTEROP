import json

from sqlmodel import select
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models_structure_fhir import GHTContext


def test_create_ght_via_form(client: TestClient, session: Session):
    """POST the GHT creation form and ensure the new context appears."""
    resp = client.post(
        "/admin/ght/new",
        data={"name": "GHT Smoke", "code": "GHT-SMOKE", "description": "smoke", "is_active": "true"},
        allow_redirects=True,
    )
    assert resp.status_code == 200
    assert "GHT Smoke" in resp.text

    # confirm in DB
    ctx = session.exec(select(GHTContext).where(GHTContext.code == "GHT-SMOKE")).first()
    assert ctx is not None


def test_send_message_mllp_and_fhir(client: TestClient, test_endpoints):
    """Send both MLLP and FHIR simulated messages via the send form."""

    # MLLP with test endpoint
    payload = "MSH|^~\\&|S|F|R|F|202501010101||ADT^A01|MSG001|P|2.5.1\rPID|1||123^^^HOSP^PI||DOE^JOHN"
    r = client.post("/messages/send", 
                   data={
                       "kind": "MLLP",
                       "endpoint_id": str(test_endpoints["mllp"].id),
                       "payload": payload
                   },
                   follow_redirects=True)
    assert r.status_code == 200
    assert "MLLP" in r.text
    # ack content is shown in a <pre> block
    assert "<pre" in r.text

    # FHIR with test endpoint
    bundle = {"resourceType": "Bundle", "type": "collection", "entry": []}
    r2 = client.post("/messages/send",
                    data={
                        "kind": "FHIR",
                        "endpoint_id": str(test_endpoints["fhir"].id),
                        "payload": json.dumps(bundle)
                    },
                    follow_redirects=True)
    assert r2.status_code == 200
    assert "FHIR" in r2.text
    assert "Logged message id=" in r2.text
