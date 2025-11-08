from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from app.db import get_session
from app.models_endpoints import MessageLog

router = APIRouter(prefix="/inbox/fhir", tags=["inbox-fhir"])

@router.post("")
async def receive_fhir(request: Request, session=Depends(get_session)):
    # Reçoit un Bundle/Resource FHIR en JSON
    body = await request.body()
    log = MessageLog(direction="in", kind="FHIR", payload=body.decode("utf-8"), status="received")
    session.add(log); session.commit()
    outcome = {
        "resourceType": "OperationOutcome",
        "issue": [{"severity":"information","code":"informational","diagnostics":"Received"}]
    }
    log.ack_payload = str(outcome); log.status = "ack_ok"; session.add(log); session.commit()
    return JSONResponse(outcome, status_code=201)
