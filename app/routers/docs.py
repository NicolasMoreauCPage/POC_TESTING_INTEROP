"""Router pour la documentation des standards."""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from ..db import get_session

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/standards", response_class=HTMLResponse)
async def standards_docs(
    request: Request,
    session: Session = Depends(get_session)
):
    """Page de documentation des standards supportés."""
    return templates.TemplateResponse(
        "standards_docs.html",
        {
            "request": request,
            "title": "Documentation des standards",
        }
    )


@router.get("/standards-docs", response_class=HTMLResponse)
async def standards_docs_legacy(
    request: Request,
    session: Session = Depends(get_session)
):
    """Alias conservé pour compatibilité avec l'ancien chemin."""
    return await standards_docs(request, session)
