from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from app.db import get_session
from app.models import Patient, Dossier, Venue

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(tags=["home"])

@router.get("/", response_class=HTMLResponse)
def home(request: Request, session=Depends(get_session)):
    patients = session.exec(select(Patient)).all()
    dossiers = session.exec(select(Dossier)).all()
    venues = session.exec(select(Venue)).all()
    stats = {"patients": len(patients), "dossiers": len(dossiers), "venues": len(venues)}
    return templates.TemplateResponse("home.html", {"request": request, "stats": stats})
