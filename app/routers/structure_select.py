from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlmodel import select, Session
from app.db import get_session
from app.models_structure import (
    UniteFonctionnelle,
    UniteHebergement,
    Chambre,
    Lit
)

router = APIRouter(prefix="/structure", tags=["structure"])

@router.get("/uf")
def list_uf(service_id: int | None = None, session: Session = Depends(get_session)):
    stmt = select(UniteFonctionnelle)
    if service_id:
        stmt = stmt.where(UniteFonctionnelle.service_id == service_id)
    ufs = session.exec(stmt).all()
    return [{"id": uf.id, "name": uf.name, "identifier": uf.identifier} for uf in ufs]

@router.get("/uh/{uf_id}")
def list_uh(uf_id: int, session: Session = Depends(get_session)):
    stmt = select(UniteHebergement).where(UniteHebergement.unite_fonctionnelle_id == uf_id)
    uhs = session.exec(stmt).all()
    return [{"id": uh.id, "name": uh.name, "identifier": uh.identifier} for uh in uhs]

@router.get("/chambres/{uh_id}")
def list_chambres(uh_id: int, session: Session = Depends(get_session)):
    stmt = select(Chambre).where(Chambre.unite_hebergement_id == uh_id)
    chambres = session.exec(stmt).all()
    return [{"id": c.id, "name": c.name, "identifier": c.identifier} for c in chambres]

@router.get("/lits/{chambre_id}")
def list_lits(chambre_id: int, session: Session = Depends(get_session)):
    stmt = select(Lit).where(Lit.chambre_id == chambre_id)
    lits = session.exec(stmt).all()
    return [{"id": l.id, "name": l.name, "identifier": l.identifier, "status": l.operational_status} for l in lits]