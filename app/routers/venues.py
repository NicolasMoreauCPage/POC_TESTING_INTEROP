from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from datetime import datetime
from app.db import get_session, get_next_sequence, peek_next_sequence
from app.models import Venue, Dossier

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/venues", tags=["venues"])

@router.get("", response_class=HTMLResponse)
def list_venues(request: Request, dossier_id: int | None = Query(None), session=Depends(get_session)):
    stmt = select(Venue)
    if dossier_id:
        stmt = stmt.where(Venue.dossier_id == dossier_id)
    venues = session.exec(stmt).all()
    rows = [{"cells": [v.venue_seq, v.id, v.dossier_id, v.uf_responsabilite, v.start_time, v.code, v.label], "detail_url": None} for v in venues]
    ctx = {"request": request, "title": "Venues",
           "headers": ["Seq", "ID", "Dossier", "UF resp.", "Début", "Code", "Libellé"],
           "rows": rows, "new_url": "/venues/new"}
    return templates.TemplateResponse("list.html", ctx)

@router.get("/new", response_class=HTMLResponse)
def new_venue(request: Request, session=Depends(get_session)):
    next_seq = peek_next_sequence(session, "venue")
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
    fields = [
        {"label": "Dossier ID", "name": "dossier_id", "type": "number"},
        {"label": "UF de responsabilité", "name": "uf_responsabilite", "type": "text"},
        {"label": "Début de venue", "name": "start_time", "type": "datetime-local", "value": now_str},
        {"label": "Code (facultatif)", "name": "code", "type": "text"},
        {"label": "Libellé (facultatif)", "name": "label", "type": "text"},
        {"label": "Numéro de séquence", "name": "venue_seq", "type": "number", "value": next_seq},
    ]
    return templates.TemplateResponse("form.html", {"request": request, "title": "Nouvelle venue", "fields": fields})

@router.post("/new")
def create_venue(
    dossier_id: int = Form(...),
    uf_responsabilite: str = Form(...),
    start_time: str = Form(...),
    code: str = Form(None),
    label: str = Form(None),
    venue_seq: int | None = Form(None),
    session=Depends(get_session)
):
    start_dt = datetime.fromisoformat(start_time)
    seq = venue_seq or get_next_sequence(session, "venue")
    v = Venue(
        dossier_id=dossier_id,
        uf_responsabilite=uf_responsabilite,
        start_time=start_dt,
        code=code,
        label=label,
        venue_seq=seq,
    )
    session.add(v); session.commit()
    return RedirectResponse(url="/venues", status_code=303)
