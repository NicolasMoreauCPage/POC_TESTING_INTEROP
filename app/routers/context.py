from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.db import get_session
from app.models import Patient, Dossier
from app.models_structure_fhir import GHTContext, EntiteJuridique

router = APIRouter()


def _redirect_back(request: Request, fallback: str = "/") -> RedirectResponse:
    referer = request.headers.get("referer") or request.headers.get("referrer")
    target = referer if referer and referer.startswith("/") else fallback
    # Use 303 to force GET after potential POSTs
    return RedirectResponse(url=target, status_code=303)


@router.get("/patient/{patient_id}")
def set_patient_context(patient_id: int, request: Request, session: Session = Depends(get_session)):
    patient = session.get(Patient, patient_id)
    if not patient:
        return RedirectResponse("/patients", status_code=303)
    request.session["patient_id"] = patient_id
    # Do NOT clear dossier_id automatically; user may be working on a dossier
    # from the same patient. Let dossier context persist unless incompatible.
    return _redirect_back(request, fallback=f"/patients/{patient_id}")


@router.get("/dossier/{dossier_id}")
def set_dossier_context(dossier_id: int, request: Request, session: Session = Depends(get_session)):
    dossier = session.get(Dossier, dossier_id)
    if not dossier:
        return RedirectResponse("/dossiers", status_code=303)
    request.session["dossier_id"] = dossier_id
    # Align patient context with dossier's patient
    if dossier.patient_id:
        request.session["patient_id"] = dossier.patient_id
    return _redirect_back(request, fallback=f"/dossiers/{dossier_id}")


@router.get("/clear")
def clear_context(kind: str | None = None, request: Request = None):
    if kind == "patient":
        request.session.pop("patient_id", None)
    elif kind == "dossier":
        request.session.pop("dossier_id", None)
    elif kind == "ght":
        request.session.pop("ght_context_id", None)
        # si on efface le GHT, l'EJ n'est peut-être plus cohérent => on l'efface aussi
        request.session.pop("ej_context_id", None)
    elif kind == "ej":
        request.session.pop("ej_context_id", None)
        # conserver le GHT si choisi indépendamment
    else:
        # clear all known contexts
        request.session.pop("patient_id", None)
        request.session.pop("dossier_id", None)
        request.session.pop("ght_context_id", None)
        request.session.pop("ej_context_id", None)
    return _redirect_back(request, fallback="/")


@router.get("/select")
def select_context(request: Request):
    """Page de sélection de contexte (redirige vers la gestion des GHT pour l'instant)."""
    return RedirectResponse("/admin/ght", status_code=303)


@router.get("/ght/{ght_id}")
def set_ght_context(ght_id: int, request: Request, session: Session = Depends(get_session)):
    ght = session.get(GHTContext, ght_id)
    if not ght:
        return RedirectResponse("/admin/ght", status_code=303)
    # Définir le contexte GHT
    request.session["ght_context_id"] = ght_id
    # Si un EJ est sélectionné mais n'appartient pas à ce GHT, l'effacer
    ej_id = request.session.get("ej_context_id")
    if ej_id:
        ej = session.get(EntiteJuridique, ej_id)
        if not ej or ej.ght_context_id != ght_id:
            request.session.pop("ej_context_id", None)
    return _redirect_back(request, fallback=f"/admin/ght/{ght_id}")


@router.get("/ej/{ej_id}")
def set_ej_context(ej_id: int, request: Request, session: Session = Depends(get_session)):
    ej = session.get(EntiteJuridique, ej_id)
    if not ej:
        return RedirectResponse("/admin/ght", status_code=303)
    # Définir le contexte EJ et, par cohérence d'UI, aligner le GHT
    request.session["ej_context_id"] = ej_id
    if ej.ght_context_id:
        request.session["ght_context_id"] = ej.ght_context_id
    return _redirect_back(request, fallback=f"/admin/ght/{ej.ght_context_id}")
