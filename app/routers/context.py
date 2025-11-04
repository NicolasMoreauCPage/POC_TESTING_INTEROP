from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.db import get_session
from app.models import Patient, Dossier

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
    else:
        # clear both
        request.session.pop("patient_id", None)
        request.session.pop("dossier_id", None)
    return _redirect_back(request, fallback="/")
