from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from datetime import datetime
from app.db import get_session, get_next_sequence, peek_next_sequence
from app.models import Mouvement, Venue
from app.services.emit_on_create import emit_to_senders

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/mouvements", tags=["mouvements"])

@router.get("", response_class=HTMLResponse)
def list_mouvements(request: Request, venue_id: int | None = Query(None), session=Depends(get_session)):
    stmt = select(Mouvement)
    if venue_id:
        stmt = stmt.where(Mouvement.venue_id == venue_id)
    mouvements = session.exec(stmt).all()
    rows = [{"cells": [m.mouvement_seq, m.id, m.venue_id, m.type, m.when, m.location], "detail_url": f"/mouvements/{m.id}"} for m in mouvements]

@router.get("/{mouvement_id}", response_class=HTMLResponse)
def mouvement_detail(mouvement_id: int, request: Request, session=Depends(get_session)):
    m = session.get(Mouvement, mouvement_id)
    if not m:
        return templates.TemplateResponse("not_found.html", {"request": request, "title": "Mouvement introuvable"}, status_code=404)
    return templates.TemplateResponse("mouvement_detail.html", {"request": request, "mouvement": m})


@router.get("/{mouvement_id}/edit", response_class=HTMLResponse)
def edit_mouvement(mouvement_id: int, request: Request, session=Depends(get_session)):
    m = session.get(Mouvement, mouvement_id)
    if not m:
        return templates.TemplateResponse("not_found.html", {"request": request, "title": "Mouvement introuvable"}, status_code=404)
    fields = [
        {"label": "Venue ID", "name": "venue_id", "type": "number", "value": m.venue_id},
        {"label": "Type (ex: ADT^A01)", "name": "type", "type": "text", "value": m.type},
        {"label": "Quand", "name": "when", "type": "datetime-local", "value": m.when.strftime('%Y-%m-%dT%H:%M') if m.when else ''},
        {"label": "Localisation", "name": "location", "type": "text", "value": m.location},
        {"label": "Numéro de séquence", "name": "mouvement_seq", "type": "number", "value": m.mouvement_seq},
    ]
    return templates.TemplateResponse("form.html", {"request": request, "title": "Modifier mouvement", "fields": fields, "action_url": f"/mouvements/{mouvement_id}/edit"})


@router.post("/{mouvement_id}/edit")
def update_mouvement(
    mouvement_id: int,
    venue_id: int = Form(...),
    type: str = Form(...),
    when: str = Form(...),
    location: str = Form(None),
    mouvement_seq: int = Form(...),
    session=Depends(get_session),
):
    m = session.get(Mouvement, mouvement_id)
    if not m:
        return templates.TemplateResponse("not_found.html", {"request": {}, "title": "Mouvement introuvable"}, status_code=404)
    m.venue_id = venue_id
    m.type = type
    m.when = datetime.fromisoformat(when)
    m.location = location
    m.mouvement_seq = mouvement_seq
    session.add(m); session.commit()
    emit_to_senders(m, "mouvement", session)
    return RedirectResponse(url="/mouvements", status_code=303)


@router.post("/{mouvement_id}/delete")
def delete_mouvement(mouvement_id: int, session=Depends(get_session)):
    m = session.get(Mouvement, mouvement_id)
    if not m:
        return templates.TemplateResponse("not_found.html", {"request": {}, "title": "Mouvement introuvable"}, status_code=404)
    session.delete(m); session.commit()
    emit_to_senders(m, "mouvement", session)
    return RedirectResponse(url="/mouvements", status_code=303)
    ctx = {"request": request, "title": "Mouvements",
           "headers": ["Seq", "ID", "Venue", "Type", "Date/Heure", "Localisation"],
           "rows": rows, "new_url": "/mouvements/new"}
    return templates.TemplateResponse("list.html", ctx)

@router.get("/new", response_class=HTMLResponse)
def new_mouvement(request: Request, session=Depends(get_session)):
    next_seq = peek_next_sequence(session, "mouvement")
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
    fields = [
        {"label": "Venue ID", "name": "venue_id", "type": "number"},
        {"label": "Type (ex: ADT^A01)", "name": "type", "type": "text"},
        {"label": "Quand", "name": "when", "type": "datetime-local", "value": now_str},
        {"label": "Localisation", "name": "location", "type": "text"},
        {"label": "Numéro de séquence", "name": "mouvement_seq", "type": "number", "value": next_seq},
    ]
    return templates.TemplateResponse("form.html", {"request": request, "title": "Nouveau mouvement", "fields": fields})

@router.post("/new")
def create_mouvement(
    venue_id: int = Form(...),
    type: str = Form(...),
    when: str = Form(...),
    location: str = Form(None),
    mouvement_seq: int | None = Form(None),
    session=Depends(get_session),
):
    when_dt = datetime.fromisoformat(when)
    seq = mouvement_seq or get_next_sequence(session, "mouvement")
    m = Mouvement(
        venue_id=venue_id,
        type=type,
        when=when_dt,
        location=location,
        mouvement_seq=seq,
    )
    session.add(m); session.commit()
    emit_to_senders(m, "mouvement", session)
    return RedirectResponse(url="/mouvements", status_code=303)
