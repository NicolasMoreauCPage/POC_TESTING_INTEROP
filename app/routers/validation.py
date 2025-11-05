"""
Router pour l'interface de validation de messages HL7 v2.5
Permet de valider un message HL7 en dehors du contexte GHT
"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.pam_validation import validate_pam
import json

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/validation", response_class=HTMLResponse)
async def validation_page(request: Request):
    """Page de validation de messages HL7."""
    # Message exemple par défaut
    example_message = """MSH|^~\\&|SENDING_APP|SEND_FAC|RECEIVING_APP|RECV_FAC|20251105120000||ADT^A01^ADT_A01|MSG001|P|2.5
EVN|A01|20251105120000
PID|1||123456^^^HOSP||DUPONT^JEAN||19800101|M
PV1|1|I|CARDIO^101^1|||||||||||||||||1"""
    
    return templates.TemplateResponse("validation.html", {
        "request": request,
        "title": "Validation Messages HL7 v2.5",
        "validation_done": False,
        "hl7_message": example_message
    })


@router.post("/validation/validate", response_class=HTMLResponse)
async def validate_message(
    request: Request,
    hl7_message: str = Form(...),
    direction: str = Form(default="inbound"),
    profile: str = Form(default="IHE_PAM_FR")
):
    """Valide un message HL7 et retourne le rapport."""
    
    print(f"[VALIDATION] Received message of length: {len(hl7_message)}")
    print(f"[VALIDATION] Direction: {direction}, Profile: {profile}")
    
    # Validation du message
    result = validate_pam(hl7_message, direction, profile)
    print(f"[VALIDATION] Result level: {result.level}, issues: {len(result.issues)}")
    
    # Classifier les issues par sévérité
    errors = [i for i in result.issues if i.severity == "error"]
    warnings = [i for i in result.issues if i.severity == "warn"]
    infos = [i for i in result.issues if i.severity == "info"]
    
    # Classifier par couche de validation
    ihe_pam = []
    hapi = []
    hl7_base = []
    datatypes = []
    segment_order = []
    
    for issue in result.issues:
        code = issue.code
        if "ORDER" in code:
            segment_order.append(issue)
        elif code.startswith("PV1_MISSING") or code.startswith("EVN_MISSING") or code.startswith("PID_MISSING"):
            ihe_pam.append(issue)
        elif "SEGMENT" in code or code.endswith("_REQUIRED") or code.endswith("_FORBIDDEN") or "OPTIONAL_SEGMENTS" in code:
            hapi.append(issue)
        elif code.startswith("MSH") or code.startswith("EVN_MISMATCH"):
            hl7_base.append(issue)
        elif "_CX_" in code or "_XPN_" in code or "_XAD_" in code or "_XTN_" in code or "_TS_" in code or code.startswith("PV1_2") or code.startswith("PV1_3") or code.startswith("PV1_7") or code.startswith("PID"):
            datatypes.append(issue)
        else:
            hl7_base.append(issue)
    
    return templates.TemplateResponse("validation.html", {
        "request": request,
        "title": "Validation Messages HL7 v2.5",
        "validation_done": True,
        "hl7_message": hl7_message,
        "direction": direction,
        "profile": profile,
        "result": result,
        "errors": errors,
        "warnings": warnings,
        "infos": infos,
        "ihe_pam": ihe_pam,
        "hapi": hapi,
        "hl7_base": hl7_base,
        "datatypes": datatypes,
        "segment_order": segment_order,
    })
