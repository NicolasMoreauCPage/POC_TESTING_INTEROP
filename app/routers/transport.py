from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlmodel import select
from app.db import get_session
from app.models_endpoints import SystemEndpoint, MessageLog
from app.services.mllp import send_mllp
from app.services.fhir_transport import send_fhir
from app.services.pam import generate_pam_messages_for_dossier
from app.models import Dossier

import asyncio, contextlib
from datetime import datetime
from typing import Tuple
from sqlmodel import Session

VT = b"\x0b"   # <VT>
FS = b"\x1c"   # <FS>
CR = b"\x0d"   # <CR>

router = APIRouter(prefix="/transport", tags=["transport"])

@router.get("/endpoints")
def list_eps(session=Depends(get_session)):
    eps = session.exec(select(SystemEndpoint).where(SystemEndpoint.is_enabled==True)).all()
    return [{"id": e.id, "name": e.name, "kind": e.kind, "role": e.role} for e in eps]

@router.post("/send/pam/{dossier_id}/{endpoint_id}")
async def send_pam(dossier_id: int, endpoint_id: int, session=Depends(get_session)):
    e = session.get(SystemEndpoint, endpoint_id)
    d = session.get(Dossier, dossier_id)
    session.refresh(d, attribute_names=["patient", "venues"])
    for v in d.venues:
        session.refresh(v, attribute_names=["mouvements"])

    if not e or e.kind != "MLLP":
        return JSONResponse({"error":"endpoint not found or not MLLP"}, status_code=400)

    messages = generate_pam_messages_for_dossier(d)
    results = []
    for m in messages:
        log = MessageLog(direction="out", kind="MLLP", endpoint_id=e.id, payload=m)
        session.add(log); session.commit(); session.refresh(log)
        try:
            ack = await send_mllp(e.host, e.port, m)
            log.ack_payload = ack
            log.status = "ack_ok" if "MSA|AA" in ack else "ack_error"
            session.add(log); session.commit()
            results.append({"message_id": log.id, "status": log.status})
        except Exception as ex:
            log.status = "error"
            log.ack_payload = str(ex)
            session.add(log); session.commit()
            results.append({"message_id": log.id, "status":"error", "error": str(ex)})
    return {"results": results}

@router.post("/send/fhir/{endpoint_id}")
async def send_fhir_bundle(endpoint_id: int, bundle: dict, session=Depends(get_session)):
    e = session.get(SystemEndpoint, endpoint_id)
    if not e or e.kind != "FHIR":
        return JSONResponse({"error":"endpoint not found or not FHIR"}, status_code=400)

    log = MessageLog(direction="out", kind="FHIR", endpoint_id=e.id, payload=str(bundle))
    session.add(log); session.commit(); session.refresh(log)
    status, resp = await send_fhir(e.base_url, bundle, e.auth_kind or "none", e.auth_token)
    log.ack_payload = str(resp)
    log.status = "ack_ok" if status in (200,201,202) else "ack_error"
    session.add(log); session.commit()
    return {"status": status, "response": resp, "log_id": log.id}
