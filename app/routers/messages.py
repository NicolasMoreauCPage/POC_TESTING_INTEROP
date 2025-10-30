from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, col
from datetime import datetime
from typing import Optional

from app.db import get_session
from app.models_endpoints import MessageLog, SystemEndpoint

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/messages", tags=["messages"])

NEG_STATUSES = {"ack_error", "error"}  # ajuste selon ton usage

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def list_messages(
    request: Request,
    session: Session = Depends(get_session),
    endpoint_id: Optional[int] = Query(None),
    date_start: Optional[str] = Query(None),  # "2025-10-01T00:00"
    date_end: Optional[str] = Query(None),    # "2025-10-31T23:59"
    neg_ack_only: bool = Query(False),
    kind: Optional[str] = Query(None),        # "MLLP" | "FHIR"
    limit: int = Query(500, ge=1, le=5000),
):
    stmt = select(MessageLog).order_by(MessageLog.created_at.desc())

    if endpoint_id:
        stmt = stmt.where(MessageLog.endpoint_id == endpoint_id)

    if date_start:
        try:
            ds = datetime.fromisoformat(date_start)
            stmt = stmt.where(MessageLog.created_at >= ds)
        except Exception:
            pass

    if date_end:
        try:
            de = datetime.fromisoformat(date_end)
            stmt = stmt.where(MessageLog.created_at <= de)
        except Exception:
            pass

    if neg_ack_only:
        stmt = stmt.where(col(MessageLog.status).in_(NEG_STATUSES))

    if kind in ("MLLP", "FHIR"):
        stmt = stmt.where(MessageLog.kind == kind)

    msgs = session.exec(stmt.limit(limit)).all()
    endpoints = session.exec(select(SystemEndpoint).order_by(SystemEndpoint.name)).all()
    ep_name = {e.id: e.name for e in endpoints}

    return templates.TemplateResponse(
        "messages.html",
        {
            "request": request,
            "messages": msgs,
            "endpoints": endpoints,
            "ep_name": ep_name,
            "filters": {
                "endpoint_id": endpoint_id or "",
                "date_start": date_start or "",
                "date_end": date_end or "",
                "neg_ack_only": neg_ack_only,
                "kind": kind or "",
                "limit": limit,
            },
        },
    )

@router.get("/{message_id}", response_class=HTMLResponse)
def message_detail(message_id: int, request: Request, session: Session = Depends(get_session)):
    m = session.get(MessageLog, message_id)
    if not m:
        return templates.TemplateResponse("not_found.html", {"request": request, "title": "Message introuvable"}, status_code=404)
    ep = session.get(SystemEndpoint, m.endpoint_id) if m.endpoint_id else None
    return templates.TemplateResponse(
        "message_detail.html",
        {"request": request, "m": m, "endpoint": ep},
    )
