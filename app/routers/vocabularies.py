from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from typing import Dict, List, Optional
from datetime import datetime

from app.db import get_session
from app.models_vocabulary import VocabularySystem, VocabularyValue, VocabularyMapping, VocabularySystemType


def _ensure_vocabularies(session: Session) -> None:
    systems_present = session.exec(select(VocabularySystem).limit(1)).first()
    if systems_present:
        return
    try:
        from app.vocabulary_init import init_vocabularies

        init_vocabularies(session)
        session.commit()
    except Exception:
        session.rollback()
        raise

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/vocabularies", tags=["vocabularies"])

@router.get("", response_class=HTMLResponse)
def list_vocabularies(request: Request, session: Session = Depends(get_session)):
    """Liste des systèmes de vocabulaire"""
    _ensure_vocabularies(session)
    systems = session.exec(select(VocabularySystem)).all()

    canonical_systems = [
        system for system in systems if system.system_type != VocabularySystemType.HL7V2
    ]

    grouped = []
    for system in canonical_systems:
        mapping_counts: Dict[str, int] = {}
        for value in system.values:
            for mapping in value.mappings:
                target_type = mapping.target_system.system_type.value
                mapping_counts[target_type] = mapping_counts.get(target_type, 0) + 1

        grouped.append(
            {
                "id": system.id,
                "name": system.name,
                "label": system.label,
                "description": system.description,
                "system_type": system.system_type.value,
                "uri": system.uri,
                "oid": system.oid,
                "value_count": len(system.values),
                "fhir_count": mapping_counts.get(
                    VocabularySystemType.FHIR.value, 0
                )
                if system.system_type != VocabularySystemType.FHIR
                else len(system.values),
                "hl7_count": mapping_counts.get(
                    VocabularySystemType.HL7V2.value, 0
                ),
                "is_user_defined": system.is_user_defined,
            }
        )

    breadcrumbs = [{"label": "Listes de valeurs", "url": "/vocabularies"}]
    ctx = {
        "request": request,
        "title": "Listes de valeurs (vue IHE)",
        "systems": grouped,
        "breadcrumbs": breadcrumbs,
        "can_create": True,
    }

    return templates.TemplateResponse("vocabularies/list.html", ctx)

@router.get("/{system_id}", response_class=HTMLResponse)
def vocabulary_detail(system_id: int, request: Request, session: Session = Depends(get_session)):
    """Détail d'un système de vocabulaire avec ses valeurs"""
    system = session.get(VocabularySystem, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="Système de vocabulaire non trouvé")

    def _value_entry(value: VocabularyValue) -> Dict[str, Optional[str]]:
        return {
            "code": value.code,
            "display": value.display,
            "definition": value.definition,
            "is_active": value.is_active,
            "order": value.order,
        }

    def _resolve_mapping(
        source_value: VocabularyValue, target_type: VocabularySystemType
    ) -> Optional[Dict[str, Optional[str]]]:
        for mapping in source_value.mappings:
            target_system = mapping.target_system
            if target_system.system_type == target_type:
                target_value = session.exec(
                    select(VocabularyValue)
                    .where(VocabularyValue.system_id == target_system.id)
                    .where(VocabularyValue.code == mapping.target_code)
                ).first()
                if target_value:
                    return _value_entry(target_value)
                return {
                    "code": mapping.target_code,
                    "display": mapping.target_code,
                    "definition": None,
                    "is_active": True,
                    "order": None,
                }
        return None

    rows = []
    for value in sorted(system.values, key=lambda v: v.order):
        canonical = _value_entry(value)
        row = {
            "canonical_id": value.id,
            "ihe": None,
            "fhir": None,
            "hl7": None,
        }

        if system.system_type == VocabularySystemType.LOCAL:
            row["ihe"] = canonical
            row["fhir"] = _resolve_mapping(value, VocabularySystemType.FHIR)
            row["hl7"] = _resolve_mapping(value, VocabularySystemType.HL7V2)
        elif system.system_type == VocabularySystemType.FHIR:
            row["ihe"] = canonical  # Utilisé comme référence IHE/FHIR
            row["fhir"] = canonical
            row["hl7"] = _resolve_mapping(value, VocabularySystemType.HL7V2)
        else:  # HL7 isolé
            row["hl7"] = canonical

        rows.append(row)

    breadcrumbs = [
        {"label": "Listes de valeurs", "url": "/vocabularies"},
        {"label": system.label, "url": f"/vocabularies/{system_id}"},
    ]

    ctx = {
        "request": request,
        "title": f"Liste de valeurs : {system.label}",
        "description": system.description,
        "system": {
            "id": system.id,
            "name": system.name,
            "label": system.label,
            "system_type": system.system_type.value,
            "uri": system.uri,
            "oid": system.oid,
            "is_user_defined": system.is_user_defined,
        },
        "rows": rows,
        "breadcrumbs": breadcrumbs,
        "can_edit": system.is_user_defined,
        "has_fhir": any(row.get("fhir") for row in rows),
        "has_hl7": any(row.get("hl7") for row in rows),
    }

    return templates.TemplateResponse("vocabularies/detail.html", ctx)

@router.get("/new", response_class=HTMLResponse)
def new_vocabulary(request: Request):
    """Formulaire de création d'un nouveau système de vocabulaire"""
    fields = [
        {
            "name": "name",
            "label": "Code technique",
            "type": "text",
            "required": True,
            "help": "Identifiant unique du système (ex: admission-type)"
        },
        {
            "name": "label",
            "label": "Libellé",
            "type": "text",
            "required": True,
            "help": "Nom affiché aux utilisateurs"
        },
        {
            "name": "description",
            "label": "Description",
            "type": "textarea",
            "required": False
        },
        {
            "name": "uri",
            "label": "URI",
            "type": "text",
            "required": False,
            "help": "URI du système (pour FHIR)"
        },
        {
            "name": "oid",
            "label": "OID",
            "type": "text",
            "required": False,
            "help": "OID du système (pour HL7v2)"
        }
    ]
    
    breadcrumbs = [
        {"label": "Listes de valeurs", "url": "/vocabularies"},
        {"label": "Nouvelle liste", "url": "/vocabularies/new"}
    ]
    
    return templates.TemplateResponse(
        request,
        "form.html",
        {
            "request": request,
            "title": "Nouvelle liste de valeurs",
            "fields": fields,
            "breadcrumbs": breadcrumbs,
            "action_url": "/vocabularies/new"
        }
    )

@router.post("/new")
def create_vocabulary(
    name: str = Form(...),
    label: str = Form(...),
    description: str = Form(None),
    uri: str = Form(None),
    oid: str = Form(None),
    session: Session = Depends(get_session)
):
    """Crée un nouveau système de vocabulaire (toujours user-defined)"""
    system = VocabularySystem(
        name=name,
        label=label,
        description=description,
        uri=uri,
        oid=oid,
        system_type=VocabularySystemType.LOCAL,
        is_user_defined=True
    )
    
    session.add(system)
    session.commit()
    
    return RedirectResponse(url=f"/vocabularies/{system.id}", status_code=303)

@router.get("/{system_id}/values/new", response_class=HTMLResponse)
def new_value(system_id: int, request: Request, session: Session = Depends(get_session)):
    """Formulaire d'ajout d'une nouvelle valeur"""
    system = session.get(VocabularySystem, system_id)
    if not system or not system.is_user_defined:
        raise HTTPException(status_code=404, detail="Système non trouvé ou non modifiable")
    
    # Calculer l'ordre par défaut (max + 1)
    max_order = max([v.order for v in system.values], default=0)
    
    fields = [
        {
            "name": "code",
            "label": "Code",
            "type": "text",
            "required": True,
            "help": "Code technique unique dans la liste"
        },
        {
            "name": "display",
            "label": "Libellé",
            "type": "text",
            "required": True,
            "help": "Texte affiché aux utilisateurs"
        },
        {
            "name": "definition",
            "label": "Description",
            "type": "textarea",
            "required": False
        },
        {
            "name": "order",
            "label": "Ordre",
            "type": "number",
            "value": max_order + 1,
            "required": True
        },
        {
            "name": "is_active",
            "label": "Actif",
            "type": "checkbox",
            "value": True
        }
    ]
    
    breadcrumbs = [
        {"label": "Listes de valeurs", "url": "/vocabularies"},
        {"label": system.label, "url": f"/vocabularies/{system_id}"},
        {"label": "Nouvelle valeur", "url": f"/vocabularies/{system_id}/values/new"}
    ]
    
    return templates.TemplateResponse(
        request,
        "form.html",
        {
            "request": request,
            "title": f"Nouvelle valeur - {system.label}",
            "fields": fields,
            "breadcrumbs": breadcrumbs,
            "action_url": f"/vocabularies/{system_id}/values/new"
        }
    )

@router.post("/{system_id}/values/new")
def create_value(
    system_id: int,
    code: str = Form(...),
    display: str = Form(...),
    definition: str = Form(None),
    order: int = Form(...),
    is_active: bool = Form(True),
    session: Session = Depends(get_session)
):
    """Ajoute une nouvelle valeur à un système"""
    system = session.get(VocabularySystem, system_id)
    if not system or not system.is_user_defined:
        raise HTTPException(status_code=404, detail="Système non trouvé ou non modifiable")
    
    value = VocabularyValue(
        system_id=system_id,
        code=code,
        display=display,
        definition=definition,
        order=order,
        is_active=is_active
    )
    
    session.add(value)
    session.commit()
    
    return RedirectResponse(url=f"/vocabularies/{system_id}", status_code=303)

@router.post("/{system_id}/delete")
def delete_vocabulary(system_id: int, session: Session = Depends(get_session)):
    """Supprime un système de vocabulaire (si user-defined)"""
    system = session.get(VocabularySystem, system_id)
    if not system or not system.is_user_defined:
        raise HTTPException(status_code=404, detail="Système non trouvé ou non modifiable")
    
    session.delete(system)
    session.commit()
    
    return RedirectResponse(url="/vocabularies", status_code=303)
