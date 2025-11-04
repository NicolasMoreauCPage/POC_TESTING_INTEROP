from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db import get_session
from app.models_endpoints import SystemEndpoint, MLLPConfig, FHIRConfig, MessageLog
from app.services.mllp import send_mllp
from app.services.fhir_transport import post_fhir_bundle as send_fhir
from app.services.pam import generate_pam_messages_for_dossier
from app.models import Dossier

import asyncio, contextlib
from datetime import datetime
from typing import Tuple, List, Optional
from pathlib import Path

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

router = APIRouter(
    prefix="/transport",
    tags=["transport"],
    responses={404: {"description": "Not found"}}
)

@router.get("/endpoints")
def list_eps(session: Session = Depends(get_session)):
    """List active endpoints with their configs."""
    endpoints = (
        session.exec(select(SystemEndpoint).where(SystemEndpoint.is_enabled==True))
        .all()
    )
    return [{
        "id": e.id,
        "name": e.name,
        "mllp_configs": [
            {"id": c.id, "name": c.name, "port": c.port, "is_enabled": c.is_enabled}
            for c in e.mllp_configs
        ],
        "fhir_configs": [
            {"id": c.id, "name": c.name, "base_url": c.base_url, "is_enabled": c.is_enabled}
            for c in e.fhir_configs
        ]
    } for e in endpoints]

@router.post("/send/pam/{dossier_id}/mllp/{config_id}")
async def send_pam_mllp(
    dossier_id: int, 
    config_id: int, 
    session: Session = Depends(get_session)
):
    """Send PAM messages to a specific MLLP config."""
    config = session.get(MLLPConfig, config_id)
    dossier = session.get(Dossier, dossier_id)
    
    if not config or not dossier or not config.is_enabled:
        raise HTTPException(
            status_code=400,
            detail="Configuration not found or disabled"
        )
    
    session.refresh(dossier, attribute_names=["patient", "venues"])
    for venue in dossier.venues:
        session.refresh(venue, attribute_names=["mouvements"])

    messages = generate_pam_messages_for_dossier(dossier)
    results = []
    
    for msg in messages:
        log = MessageLog(
            direction="out",
            kind="MLLP",
            endpoint_id=config.endpoint_id,
            mllp_config_id=config.id,
            payload=msg
        )
        session.add(log)
        session.commit()
        session.refresh(log)
        
        try:
            # Use MLLP config parameters
            ack = await send_mllp(config.host, config.port, msg)
            log.ack_payload = ack
            log.status = "ack_ok" if "MSA|AA" in ack else "ack_error"
            session.add(log)
            session.commit()
            results.append({"message_id": log.id, "status": log.status})
        except Exception as ex:
            log.status = "error"
            log.ack_payload = str(ex)
            session.add(log)
            session.commit()
            results.append({
                "message_id": log.id,
                "status": "error",
                "error": str(ex)
            })
    
    return {"results": results}

@router.post("/send/fhir/{config_id}")
async def send_fhir_bundle(
    config_id: int, 
    bundle: dict, 
    session: Session = Depends(get_session)
):
    """Send FHIR bundle to a specific FHIR config."""
    config = session.get(FHIRConfig, config_id)
    if not config or not config.is_enabled:
        raise HTTPException(
            status_code=400,
            detail="Configuration not found or disabled"
        )

    # Log outbound message
    log = MessageLog(
        direction="out",
        kind="FHIR",
        endpoint_id=config.endpoint_id,
        fhir_config_id=config.id,
        payload=str(bundle)
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    
    # Build full URL with optional path prefix
    base_url = config.base_url.rstrip("/")
    path_prefix = config.path_prefix.strip("/")
    full_url = f"{base_url}/{path_prefix}" if path_prefix else base_url
    
    # Send using config params
    status, resp = await send_fhir(
        full_url,
        bundle,
        config.auth_kind or "none",
        config.auth_token
    )
    
    log.ack_payload = str(resp)
    log.status = "ack_ok" if status in (200, 201, 202) else "ack_error"
    session.add(log)
    session.commit()
    
    return {
        "status": status,
        "response": resp,
        "log_id": log.id
    }
