from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from starlette import status
from datetime import datetime, timezone

from app.db import get_session
from app.models_endpoints import SystemEndpoint
from app.runners import registry  # ⬅️ registre runtime (à créer si pas encore)

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/endpoints", tags=["endpoints"])

def _bool_from_str(v: str | None, default: bool = False) -> bool:
    if v is None:
        return default
    return str(v).lower() in {"1","true","on","yes","y"}

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def list_endpoints(request: Request, session=Depends(get_session)):
    eps = session.exec(select(SystemEndpoint)).all()
    running_ids = set(registry.running_ids())  # ⬅️ méthode utilitaire
    rows = []
    for e in eps:
        runtime = "RUNNING" if e.id in running_ids else "STOPPED"
        rows.append({
            "cells": [e.id, e.name, e.kind, e.role, e.host or "-", e.port or "-", e.base_url or "-", "ON" if e.is_enabled else "OFF", runtime],
            "detail_url": f"/endpoints/{e.id}"
        })
    ctx = {"request": request, "title": "Systèmes (Paramétrage)",
           "headers": ["ID","Nom","Type","Rôle","Host","Port","FHIR URL","Actif","Runtime"],
           "rows": rows, "new_url": "/endpoints/new"}
    return templates.TemplateResponse("list.html", ctx)

@router.get("/new", response_class=HTMLResponse)
def new_endpoint(request: Request):
    fields = [
        {"label":"Nom","name":"name","type":"text"},
        {"label":"Type (MLLP|FHIR)","name":"kind","type":"text"},
        {"label":"Rôle (sender|receiver|both)","name":"role","type":"text","value":"both"},
        {"label":"Actif (true/false)","name":"is_enabled","type":"text","value":"true"},
        {"label":"Host (MLLP)","name":"host","type":"text","placeholder":"0.0.0.0"},
        {"label":"Port (MLLP)","name":"port","type":"number"},
        {"label":"Sending App (MSH-3)","name":"sending_app","type":"text"},
        {"label":"Sending Facility (MSH-4)","name":"sending_facility","type":"text"},
        {"label":"Receiving App (MSH-5)","name":"receiving_app","type":"text"},
        {"label":"Receiving Facility (MSH-6)","name":"receiving_facility","type":"text"},
        {"label":"FHIR base URL","name":"base_url","type":"text"},
        {"label":"Auth kind (none|bearer)","name":"auth_kind","type":"text","value":"none"},
        {"label":"Auth token (si bearer)","name":"auth_token","type":"text"},
    ]
    return templates.TemplateResponse("form.html", {"request": request, "title":"Nouveau système", "fields":fields})

@router.post("/new")
def create_endpoint(
    name: str = Form(...),
    kind: str = Form(...),
    role: str = Form("both"),
    is_enabled: str = Form("true"),
    host: str = Form(None),
    port: int = Form(None),
    sending_app: str = Form(None),
    sending_facility: str = Form(None),
    receiving_app: str = Form(None),
    receiving_facility: str = Form(None),
    base_url: str = Form(None),
    auth_kind: str = Form("none"),
    auth_token: str = Form(None),
    session=Depends(get_session),
):
    e = SystemEndpoint(
        name=name, kind=kind.upper(), role=role, is_enabled=_bool_from_str(is_enabled, True),
        host=host, port=port,
        sending_app=sending_app, sending_facility=sending_facility,
        receiving_app=receiving_app, receiving_facility=receiving_facility,
        base_url=base_url, auth_kind=auth_kind, auth_token=auth_token
    )
    session.add(e); session.commit()
    return RedirectResponse(url="/endpoints", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/{endpoint_id}", response_class=HTMLResponse)
def detail_endpoint(endpoint_id: int, request: Request, session=Depends(get_session)):
    e = session.get(SystemEndpoint, endpoint_id)
    if not e:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    is_running = endpoint_id in set(registry.running_ids())
    return templates.TemplateResponse("endpoint_detail.html", {"request": request, "e": e, "is_running": is_running})

# ========= AJOUTS =========

@router.post("/{endpoint_id}/update")
def update_endpoint(
    endpoint_id: int,
    name: str = Form(...),
    kind: str = Form(...),
    role: str = Form("both"),
    is_enabled: str = Form("true"),
    host: str = Form(None),
    port: int = Form(None),
    sending_app: str = Form(None),
    sending_facility: str = Form(None),
    receiving_app: str = Form(None),
    receiving_facility: str = Form(None),
    base_url: str = Form(None),
    auth_kind: str = Form("none"),
    auth_token: str = Form(None),
    session=Depends(get_session),
):
    e = session.get(SystemEndpoint, endpoint_id)
    if not e:
        raise HTTPException(404, "Endpoint not found")

    e.name = name
    e.kind = kind.upper()
    e.role = role
    e.is_enabled = _bool_from_str(is_enabled, True)
    e.host, e.port = host, port
    e.sending_app, e.sending_facility = sending_app, sending_facility
    e.receiving_app, e.receiving_facility = receiving_app, receiving_facility
    e.base_url, e.auth_kind, e.auth_token = base_url, auth_kind, auth_token
    e.updated_at = datetime.now(timezone.utc)

    session.add(e); session.commit()
    return RedirectResponse(url=f"/endpoints/{endpoint_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/{endpoint_id}/delete")
def delete_endpoint(endpoint_id: int, session=Depends(get_session)):
    e = session.get(SystemEndpoint, endpoint_id)
    if not e:
        raise HTTPException(404, "Endpoint not found")
    # stop si en cours d'exécution
    if endpoint_id in set(registry.running_ids()):
        registry.stop(e, session)
    session.delete(e); session.commit()
    return RedirectResponse(url="/endpoints", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/{endpoint_id}/start")
def start_endpoint(endpoint_id: int, session=Depends(get_session)):
    e = session.get(SystemEndpoint, endpoint_id)
    if not e:
        raise HTTPException(404, "Endpoint not found")
    if endpoint_id not in set(registry.running_ids()):
        registry.start(e, session); session.commit()
    return RedirectResponse(url=f"/endpoints/{endpoint_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/{endpoint_id}/stop")
def stop_endpoint(endpoint_id: int, session=Depends(get_session)):
    e = session.get(SystemEndpoint, endpoint_id)
    if not e:
        raise HTTPException(404, "Endpoint not found")
    if endpoint_id in set(registry.running_ids()):
        registry.stop(e, session); session.commit()
    return RedirectResponse(url=f"/endpoints/{endpoint_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/{endpoint_id}/restart")
def restart_endpoint(endpoint_id: int, session=Depends(get_session)):
    e = session.get(SystemEndpoint, endpoint_id)
    if not e:
        raise HTTPException(404, "Endpoint not found")
    if endpoint_id in set(registry.running_ids()):
        registry.stop(e, session)
    registry.start(e, session); session.commit()
    return RedirectResponse(url=f"/endpoints/{endpoint_id}", status_code=status.HTTP_303_SEE_OTHER)
