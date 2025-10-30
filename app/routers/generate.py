from fastapi import APIRouter, Depends
from fastapi.responses import Response, JSONResponse
from app.db import get_session
from app.models import Dossier
from app.services.pam import generate_pam_messages_for_dossier
from app.services.fhir import generate_fhir_bundle_for_dossier

router = APIRouter(prefix="/generate", tags=["generate"])

@router.post("/pam/{dossier_id}")
def gen_pam(dossier_id: int, session=Depends(get_session)):
    d = session.get(Dossier, dossier_id)
    session.refresh(d, attribute_names=["patient", "venues"])
    for v in d.venues:
        session.refresh(v, attribute_names=["mouvements"])
    msgs = generate_pam_messages_for_dossier(d)
    content = "\r\r".join(msgs) + "\r"
    filename = f"pam_dossier_{d.dossier_seq}.hl7"
    return Response(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.post("/fhir/{dossier_id}")
def gen_fhir(dossier_id: int, session=Depends(get_session)):
    d = session.get(Dossier, dossier_id)
    session.refresh(d, attribute_names=["patient"])
    bundle = generate_fhir_bundle_for_dossier(d)
    filename = f"fhir_dossier_{d.dossier_seq}.json"
    return JSONResponse(
        bundle,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
