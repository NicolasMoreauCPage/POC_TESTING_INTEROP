from datetime import datetime
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db import get_session
from app.models_endpoints import SystemEndpoint, MLLPConfig, FHIRConfig

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(
    prefix="/transport", 
    tags=["transport"],
    responses={404: {"description": "Not found"}}
)

# View routes for transport config management

@router.get("/endpoints/{endpoint_id}/transport")
async def view_transport_configs(request: Request, endpoint_id: int, session: Session = Depends(get_session)):
    """View transport configurations for an endpoint."""
    endpoint = session.get(SystemEndpoint, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return templates.TemplateResponse(
        "endpoint_transport.html", 
        {
            "request": request,
            "endpoint": endpoint,
            "mllp_configs": endpoint.mllp_configs,
            "fhir_configs": endpoint.fhir_configs
        }
    )

@router.get("/endpoints/{endpoint_id}/mllp/new")
async def new_mllp_config_form(request: Request, endpoint_id: int, session: Session = Depends(get_session)):
    """Display form to create a new MLLP config."""
    endpoint = session.get(SystemEndpoint, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return templates.TemplateResponse(
        "mllp_config_form.html",
        {
            "request": request,
            "endpoint": endpoint,
            "config": None
        }
    )

@router.post("/endpoints/{endpoint_id}/mllp/new")
async def create_mllp_config(
    endpoint_id: int,
    name: str = Form(...),
    port: int = Form(...),
    host: str = Form("0.0.0.0"),
    sending_app: str = Form(...),
    sending_facility: str = Form(...),
    receiving_app: Optional[str] = Form(None),
    receiving_facility: Optional[str] = Form(None),
    is_enabled: bool = Form(True),
    session: Session = Depends(get_session)
):
    """Create a new MLLP configuration."""
    endpoint = session.get(SystemEndpoint, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    # Check port availability
    existing = session.exec(
        select(MLLPConfig).where(MLLPConfig.port == port)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Port already in use")
    
    config = MLLPConfig(
        name=name,
        port=port,
        host=host,
        sending_app=sending_app,
        sending_facility=sending_facility,
        receiving_app=receiving_app,
        receiving_facility=receiving_facility,
        is_enabled=is_enabled,
        endpoint_id=endpoint_id
    )
    
    session.add(config)
    session.commit()
    session.refresh(config)
    
    return RedirectResponse(
        f"/endpoints/{endpoint_id}/transport",
        status_code=303
    )

@router.get("/endpoints/{endpoint_id}/mllp/{config_id}/edit")
async def edit_mllp_config_form(
    request: Request,
    endpoint_id: int,
    config_id: int,
    session: Session = Depends(get_session)
):
    """Display form to edit an MLLP config."""
    endpoint = session.get(SystemEndpoint, endpoint_id)
    config = session.get(MLLPConfig, config_id)
    
    if not endpoint or not config:
        raise HTTPException(status_code=404, detail="Endpoint or config not found")
    if config.endpoint_id != endpoint_id:
        raise HTTPException(status_code=403, detail="Config does not belong to endpoint")
    
    return templates.TemplateResponse(
        "mllp_config_form.html",
        {
            "request": request,
            "endpoint": endpoint,
            "config": config
        }
    )

@router.post("/endpoints/{endpoint_id}/mllp/{config_id}/edit")
async def update_mllp_config(
    endpoint_id: int,
    config_id: int,
    name: str = Form(...),
    port: int = Form(...),
    host: str = Form("0.0.0.0"),
    sending_app: str = Form(...),
    sending_facility: str = Form(...),
    receiving_app: Optional[str] = Form(None),
    receiving_facility: Optional[str] = Form(None),
    is_enabled: bool = Form(True),
    session: Session = Depends(get_session)
):
    """Update an MLLP configuration."""
    config = session.get(MLLPConfig, config_id)
    if not config or config.endpoint_id != endpoint_id:
        raise HTTPException(status_code=404, detail="Config not found")
    
    # Check port availability if changed
    if port != config.port:
        existing = session.exec(
            select(MLLPConfig).where(MLLPConfig.port == port)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Port already in use")
    
    config.name = name
    config.port = port
    config.host = host
    config.sending_app = sending_app
    config.sending_facility = sending_facility
    config.receiving_app = receiving_app
    config.receiving_facility = receiving_facility
    config.is_enabled = is_enabled
    config.updated_at = datetime.utcnow()
    
    session.add(config)
    session.commit()
    session.refresh(config)
    
    return RedirectResponse(
        f"/endpoints/{endpoint_id}/transport",
        status_code=303
    )

@router.get("/endpoints/{endpoint_id}/fhir/new")
async def new_fhir_config_form(request: Request, endpoint_id: int, session: Session = Depends(get_session)):
    """Display form to create a new FHIR config."""
    endpoint = session.get(SystemEndpoint, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return templates.TemplateResponse(
        "fhir_config_form.html",
        {
            "request": request,
            "endpoint": endpoint,
            "config": None
        }
    )

@router.post("/endpoints/{endpoint_id}/fhir/new")
async def create_fhir_config(
    endpoint_id: int,
    name: str = Form(...),
    base_url: str = Form(...),
    path_prefix: str = Form(""),
    version: str = Form("R4"),
    auth_kind: str = Form("none"),
    auth_token: Optional[str] = Form(None),
    supported_resources: str = Form("*"),
    is_enabled: bool = Form(True),
    session: Session = Depends(get_session)
):
    """Create a new FHIR configuration."""
    endpoint = session.get(SystemEndpoint, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    config = FHIRConfig(
        name=name,
        base_url=base_url,
        path_prefix=path_prefix,
        version=version,
        auth_kind=auth_kind,
        auth_token=auth_token,
        supported_resources=supported_resources,
        is_enabled=is_enabled,
        endpoint_id=endpoint_id
    )
    
    session.add(config)
    session.commit()
    session.refresh(config)
    
    return RedirectResponse(
        f"/endpoints/{endpoint_id}/transport",
        status_code=303
    )

@router.get("/endpoints/{endpoint_id}/fhir/{config_id}/edit")
async def edit_fhir_config_form(
    request: Request,
    endpoint_id: int,
    config_id: int,
    session: Session = Depends(get_session)
):
    """Display form to edit a FHIR config."""
    endpoint = session.get(SystemEndpoint, endpoint_id)
    config = session.get(FHIRConfig, config_id)
    
    if not endpoint or not config:
        raise HTTPException(status_code=404, detail="Endpoint or config not found")
    if config.endpoint_id != endpoint_id:
        raise HTTPException(status_code=403, detail="Config does not belong to endpoint")
    
    return templates.TemplateResponse(
        "fhir_config_form.html",
        {
            "request": request,
            "endpoint": endpoint,
            "config": config
        }
    )

@router.post("/endpoints/{endpoint_id}/fhir/{config_id}/edit")
async def update_fhir_config(
    endpoint_id: int,
    config_id: int,
    name: str = Form(...),
    base_url: str = Form(...),
    path_prefix: str = Form(""),
    version: str = Form("R4"),
    auth_kind: str = Form("none"),
    auth_token: Optional[str] = Form(None),
    supported_resources: str = Form("*"),
    is_enabled: bool = Form(True),
    session: Session = Depends(get_session)
):
    """Update a FHIR configuration."""
    config = session.get(FHIRConfig, config_id)
    if not config or config.endpoint_id != endpoint_id:
        raise HTTPException(status_code=404, detail="Config not found")
    
    config.name = name
    config.base_url = base_url
    config.path_prefix = path_prefix
    config.version = version
    config.auth_kind = auth_kind
    config.auth_token = auth_token
    config.supported_resources = supported_resources
    config.is_enabled = is_enabled
    config.updated_at = datetime.utcnow()
    
    session.add(config)
    session.commit()
    session.refresh(config)
    
    return RedirectResponse(
        f"/endpoints/{endpoint_id}/transport",
        status_code=303
    )