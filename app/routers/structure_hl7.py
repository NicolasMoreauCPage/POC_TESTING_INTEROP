from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import PlainTextResponse
from sqlmodel import Session

from app.db import get_session
from app.services.mfn_structure import process_mfn_message, generate_mfn_message

router = APIRouter(
    prefix="/structure",
    tags=["structure"]
)

@router.post("/import/hl7", response_model=dict)
async def import_hl7_structure(
    message: str = Body(..., media_type="text/plain"),
    session: Session = Depends(get_session)
):
    """
    Importe la structure depuis un message HL7 MFN M05
    Le corps de la requête doit être le message HL7 brut.
    """
    try:
        results = process_mfn_message(message, session)
        return {
            "message": "Structure importée avec succès",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/hl7", response_class=PlainTextResponse)
async def export_hl7_structure(
    session: Session = Depends(get_session)
):
    """
    Exporte la structure au format HL7 MFN M05
    Retourne un message HL7 brut.
    """
    try:
        message = generate_mfn_message(session)
        return message
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))