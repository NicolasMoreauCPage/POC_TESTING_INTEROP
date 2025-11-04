from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from app.db import get_session
from app.models import Dossier, DossierType
from app.utils.dossier_helpers import sync_dossier_class

router = APIRouter(prefix="/dossier-type", tags=["dossier"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/{dossier_id}/change", response_class=HTMLResponse)
async def show_change_type_form(
    request: Request,
    dossier_id: int,
    session: Session = Depends(get_session)
):
    """Affiche le formulaire de changement de type"""
    dossier = session.get(Dossier, dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")
        
    return templates.TemplateResponse(
        "dossier_type_change.html",
        {"request": request, "dossier": dossier}
    )

@router.post("/{dossier_id}/change")
async def change_dossier_type(
    dossier_id: int,
    new_type: DossierType,
    force: bool = False,
    session: Session = Depends(get_session)
):
    """
    Change le type d'un dossier avec validation et possibilité de forcer le changement.
    
    Args:
        dossier_id: ID du dossier à modifier
        new_type: Nouveau type de dossier
        force: Si True, permet le changement même en cas d'incompatibilités
    """
    dossier = session.get(Dossier, dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")
        
    # Si le type ne change pas, pas besoin de validation
    if dossier.dossier_type == new_type:
        return {"message": "Aucun changement nécessaire"}
    
    old_type = dossier.dossier_type
    
    try:
        if not force:
            dossier.update_type(new_type, session)
        else:
            # Forcer le changement sans validation
            dossier.dossier_type = new_type
            sync_dossier_class(dossier)
            
        session.commit()
        return {
            "status": "success",
            "message": f"Type de dossier modifié de {old_type.value} vers {new_type.value}",
            "warnings": []
        }
        
    except ValueError as e:
        session.rollback()
        return {
            "status": "error",
            "message": "Changement de type impossible",
            "warnings": [str(e)],
            "can_force": True
        }
    
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))