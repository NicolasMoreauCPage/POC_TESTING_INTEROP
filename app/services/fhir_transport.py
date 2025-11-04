"""Transport FHIR sortant (HTTP POST) et validation de transitions.

Notes SSL
- En environnement d'entreprise avec proxy/PKI, passer `verify` au client
    httpx (ex: `verify='/chemin/ca.pem'`) ou définir `SSL_CERT_FILE` /
    `REQUESTS_CA_BUNDLE` dans l'environnement.
"""

import httpx
from typing import Optional, Tuple
from app.state_transitions import is_valid_transition

async def post_fhir_bundle(base_url: str, resource_json: dict, auth_kind: str = "none", auth_token: str | None = None) -> Tuple[int, dict]:
    """POST d'une Resource/Bundle FHIR vers `base_url`.

    Headers
    - Content-Type: application/fhir+json
    - Authorization: Bearer <token> (si `auth_kind=='bearer'`)
    """
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

def validate_fhir_transition(current_state: Optional[str], event_code: str) -> bool:
    """Valide les transitions d'état pour les mouvements FHIR."""
    return is_valid_transition(current_state, event_code)
