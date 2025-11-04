from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from app.db import get_session
from app.models import Patient, Dossier, Venue
from app.models_endpoints import MessageLog
from app.models_structure_fhir import GHTContext

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(tags=["home"])

@router.get("/", response_class=HTMLResponse)
def home(request: Request, session=Depends(get_session)):
    ght_context = request.state.ght_context
    if not ght_context:
        return templates.TemplateResponse(
            request,
            "ght_contexts.html",
            {
                "request": request,
                "contexts": session.exec(select(GHTContext).order_by(GHTContext.name)).all(),
            },
        )

    patients = session.exec(
        select(Patient).where(Patient.ght_context_id == ght_context.id) if hasattr(Patient, "ght_context_id") else select(Patient)
    ).all()
    dossiers = session.exec(
        select(Dossier).where(Dossier.ght_context_id == ght_context.id) if hasattr(Dossier, "ght_context_id") else select(Dossier)
    ).all()
    venues = session.exec(
        select(Venue).where(Venue.ght_context_id == ght_context.id) if hasattr(Venue, "ght_context_id") else select(Venue)
    ).all()
    recent_messages = session.exec(select(MessageLog).order_by(MessageLog.created_at.desc()).limit(10)).all()

    stats = {
        "patients": len(patients),
        "dossiers": len(dossiers),
        "venues": len(venues),
    }
    return templates.TemplateResponse(
        request,
        "ght_dashboard.html",
        {
            "request": request,
            "stats": stats,
            "message_logs": recent_messages,
            "ght_context": ght_context,
        },
    )

@router.get("/api-docs", response_class=HTMLResponse)
def api_documentation(request: Request):
    """Documentation des APIs FHIR et HL7"""
    return templates.TemplateResponse(request, "api_docs.html", {"request": request})
