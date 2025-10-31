import httpx
from typing import Tuple
from app.state_transitions import is_valid_transition

async def send_fhir(base_url: str, resource_json: dict, auth_kind: str = "none", auth_token: str | None = None) -> Tuple[int, dict]:
    headers = {"Content-Type": "application/fhir+json"}
    if auth_kind == "bearer" and auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    async with httpx.AsyncClient(timeout=15) as client:
        # pour le POC, POST vers base_url (Bundle ou Resource)
        r = await client.post(base_url, headers=headers, json=resource_json)
        out_json = {}
        try:
            out_json = r.json()
        except Exception:
            pass
        return r.status_code, out_json

def validate_fhir_transition(current_state: str, event_code: str) -> bool:
    """
    Valide les transitions d'état pour les mouvements FHIR.
    """
    return is_valid_transition(current_state, event_code)
