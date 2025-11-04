"""Routes FastAPI pour les profils IHE PIX/PDQ et FHIR PIXm/PDQm."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlmodel import Session
import logging

from app.db import get_session
from app.services.pix_pdq_manager import PIXPDQManager
from app.services.mllp import build_ack
from app.models_endpoints import MessageLog
from datetime import datetime

router = APIRouter(prefix="/ihe", tags=["ihe"])
logger = logging.getLogger(__name__)

pix_pdq_manager = PIXPDQManager()

# Routes HL7v2 PIX/PDQ
@router.post("/pix/query")
async def pix_query(request: Request, session: Session = Depends(get_session)):
    """
    Point d'entrée pour les requêtes PIX (QBP^Q23).
    Correspond au profil IHE PIX Query [ITI-9].
    """
    try:
        msg = await request.body()
        msg = msg.decode("utf-8") if isinstance(msg, bytes) else str(msg)
        success, error, identifiers = pix_pdq_manager.handle_pix_query(msg, session)
        
        # Logger la requête
        log = MessageLog(
            direction="in",
            kind="PIX",
            payload=msg,
            status="processed" if success else "error",
            created_at=datetime.utcnow()
        )
        session.add(log)
        
        if not success:
            session.commit()
            return build_ack(msg, ack_code="AE", text=error)
            
        # Construire la réponse RSP^K23 avec MSA
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        # Extract message control ID from incoming message
        msg_id = now
        try:
            msh = next((l for l in msg.split("\r") if l.startswith("MSH")), "")
            if msh:
                msg_id = msh.split("|")[9]
        except:
            pass
            
        rsp = f"MSH|^~\\&|SERVEUR|DOMAINE|CLIENT|DOMAINE|{now}||RSP^K23^RSP_K21|{now}|P|2.5|||NE|AL|FRA|UTF-8||FR\r"
        rsp += f"MSA|AA|{msg_id}\r"
        
        if identifiers:
            for identifier in identifiers:
                rsp += f"PID|||{identifier.value}^^^{identifier.system}^^{identifier.type.value}|||||||\r"
                
        log.ack_payload = rsp
        log.message_type = "QBP^Q23"
        session.commit()
        return rsp
        
    except Exception as e:
        logger.exception("PIX query error")
        return build_ack(msg, ack_code="AR", text=str(e))

@router.post("/pdq/query")
async def pdq_query(request: Request, session: Session = Depends(get_session)):
    """
    Point d'entrée pour les requêtes PDQ (QBP^Q22).
    Correspond au profil IHE PDQ Query [ITI-21].
    """
    try:
        msg = await request.body()
        msg = msg.decode("utf-8") if isinstance(msg, bytes) else str(msg)
        
        # Validate basic HL7 structure
        if not msg.startswith("MSH|") or "\r" not in msg:
            raise HTTPException(status_code=400, detail="Invalid HL7 message")
        
        success, error, patients = pix_pdq_manager.handle_pdq_query(msg, session)
        
        # Logger la requête
        log = MessageLog(
            direction="in", 
            kind="PDQ",
            payload=msg,
            status="processed" if success else "error",
            created_at=datetime.utcnow()
        )
        session.add(log)
        
        if not success:
            session.commit()
            return build_ack(msg, ack_code="AE", text=error)
            
        # Construire la réponse RSP^K22 avec MSA
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        # Extract message control ID from incoming message
        msg_id = now
        try:
            msh = next((l for l in msg.split("\r") if l.startswith("MSH")), "")
            if msh:
                msg_id = msh.split("|")[9]
        except:
            pass
            
        rsp = f"MSH|^~\\&|SERVEUR|DOMAINE|CLIENT|DOMAINE|{now}||RSP^K22^RSP_K21|{now}|P|2.5|||NE|AL|FRA|UTF-8||FR\r"
        rsp += f"MSA|AA|{msg_id}\r"
        
        if patients:
            for p in patients:
                rsp += (f"PID|||{p.external_id or ''}||{p.family or ''}^{p.given or ''}||"
                       f"{p.birth_date or ''}|{p.gender or ''}|||||\r")
                
        log.ack_payload = rsp
        log.message_type = "QBP^Q22"
        session.commit()
        return rsp
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions (validation errors)
    except Exception as e:
        logger.exception("PDQ query error")
        return build_ack(msg, ack_code="AR", text=str(e))

# Routes FHIR PIXm/PDQm
@router.post("/pixm/$ihe-pix")
async def pixm_query(sourceIdentifier: str, session: Session = Depends(get_session)):
    """
    Point d'entrée pour les requêtes PIXm.
    Implémente l'opération $ihe-pix du profil IHE PIXm.
    """
    try:
        params = {"sourceIdentifier": sourceIdentifier}
        result = pix_pdq_manager.handle_pixm_query(params, session)
        
        # Logger la requête
        log = MessageLog(
            direction="in",
            kind="PIXm",
            payload=f"sourceIdentifier={sourceIdentifier}",
            status="processed",
            created_at=datetime.utcnow()
        )
        session.add(log)
        session.commit()
        
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("PIXm query error")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pdqm/Patient")
async def pdqm_search(
    family: str = None,
    given: str = None,
    identifier: str = None,
    birthdate: str = None,
    gender: str = None,
    session: Session = Depends(get_session)
):
    """
    Point d'entrée pour les requêtes PDQm.
    Implémente la recherche Patient du profil IHE PDQm.
    """
    try:
        params = {
            "family": family,
            "given": given,
            "identifier": identifier,
            "birthdate": birthdate,
            "gender": gender
        }
        # Filtrer les paramètres None
        params = {k: v for k, v in params.items() if v is not None}
        
        result = pix_pdq_manager.handle_pdqm_query(params, session)
        
        # Logger la requête
        log = MessageLog(
            direction="in",
            kind="PDQm",
            payload=str(params),
            status="processed",
            created_at=datetime.utcnow()
        )
        session.add(log)
        session.commit()
        
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("PDQm query error")
        raise HTTPException(status_code=500, detail=str(e))