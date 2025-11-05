from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from sqlalchemy import func
from app.db import get_session
from app.models_structure_fhir import (
    EntiteJuridique,
    GHTContext,
    IdentifierNamespace,
    EntiteGeographique,
)
from app.models_structure import (
    Pole,
    Service,
    UniteFonctionnelle,
    UniteHebergement,
    Chambre,
    Lit,
    LocationStatus,
    LocationMode,
    LocationPhysicalType,
    LocationServiceType,
)
from app.utils.flash import flash
from app.services.structure_seed import ensure_demo_structure

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/ght", tags=["ght"])
@router.get("")
@router.get("/")
async def list_ght_contexts(
    request: Request,
    session: Session = Depends(get_session),
):
    """Liste tous les contextes GHT (page de sélection)."""
    contexts = session.exec(select(GHTContext)).all()
    return templates.TemplateResponse(
        "ght_contexts.html",
        {"request": request, "contexts": contexts},
    )

@router.get("/new")
async def new_ght_context_form(request: Request):
    """Affiche le formulaire de création d'un nouveau contexte GHT."""
    return templates.TemplateResponse(
        "ght_form.html",
        {
            "request": request,
            "context": None,
        },
    )

@router.post("/{context_id}/set-ej")
async def set_ej_for_ght(
    request: Request,
    context_id: int,
    ej_id: int = Form(...),
    session: Session = Depends(get_session)
):
    """Enregistre l'entité juridique sélectionnée pour le contexte GHT en session utilisateur."""
    context = _get_context_or_404(session, context_id)
    if ej_id:
        ej = _get_ej_or_404(session, context, ej_id)
        request.session[f"ght_{context_id}_ej_id"] = ej_id
        request.session[f"ght_{context_id}_ej_name"] = ej.name
        # Définir aussi les contextes globaux pour cohérence de l'UI et des filtres
        request.session["ej_context_id"] = ej_id
        request.session["ght_context_id"] = context_id
    else:
        request.session.pop(f"ght_{context_id}_ej_id", None)
        request.session.pop(f"ght_{context_id}_ej_name", None)
        # Si on désélectionne l'EJ, effacer le contexte global EJ mais conserver le GHT courant
        request.session.pop("ej_context_id", None)
    return RedirectResponse(f"/admin/ght/{context_id}", status_code=303)

@router.post("/new")
async def create_ght_context(
    request: Request,
    name: str = Form(...),
    code: str = Form(...),
    description: Optional[str] = Form(None),
    is_active: str = Form("true"),
    session: Session = Depends(get_session),
):
    """Crée un nouveau contexte GHT et initialise des namespaces par défaut."""
    # Uniqueness check for code
    existing = session.exec(select(GHTContext).where(GHTContext.code == code)).first()
    if existing:
        flash(request, "Ce code est déjà utilisé par un autre contexte GHT.", "error")
        return templates.TemplateResponse(
            "ght_form.html",
            {
                "request": request,
                "context": None,
                "form_data": {
                    "name": name,
                    "code": code,
                    "description": description,
                    "is_active": is_active,
                },
            },
            status_code=400,
        )

    context = GHTContext(
        name=name,
        code=code,
        description=description,
        is_active=str(is_active).lower() in ("1", "true", "yes", "on"),
    )
    session.add(context)
    session.commit()
    session.refresh(context)

    # Default namespaces for the new context
    default_namespaces = [
        {
            "name": "IPP",
            "system": f"urn:oid:1.2.250.1.{context.id}.1.0",
            "type": "PI",
            "description": "Identifiant Patient Principal",
        },
        {
            "name": "NDA",
            "system": f"urn:oid:1.2.250.1.{context.id}.1.1",
            "type": "VN",
            "description": "Numéro de Dossier Administratif",
        },
        {
            "name": "FINESS EJ",
            "system": "urn:oid:1.2.250.1.71.4.2.2",
            "type": "XX",
            "description": "FINESS Entité Juridique",
        },
        {
            "name": "FINESS EG",
            "system": "urn:oid:1.2.250.1.71.4.2.1",
            "type": "XX",
            "description": "FINESS Entité Géographique",
        },
    ]

    for ns in default_namespaces:
        namespace = IdentifierNamespace(
            name=ns["name"],
            system=ns["system"],
            type=ns["type"],
            description=ns["description"],
            ght_context_id=context.id,
        )
        session.add(namespace)

    session.commit()

    flash(request, f'Contexte GHT "{context.name}" créé avec succès.', "success")

    accept = request.headers.get("accept", "")
    if "application/json" in accept:
        return {"ok": True, "id": context.id, "redirect": "/admin/ght"}

    return RedirectResponse("/admin/ght", status_code=303)

@router.get("/{context_id}/edit")
async def edit_ght_context_form(
    request: Request,
    context_id: int,
    session: Session = Depends(get_session)
):
    """Affiche le formulaire d'édition d'un contexte GHT."""
    context = session.get(GHTContext, context_id)
    if not context:
        raise HTTPException(status_code=404, detail="Contexte non trouvé")
    
    return templates.TemplateResponse(
        "ght_form.html",
        {
            "request": request,
            "context": context
        }
    )

@router.post("/{context_id}/edit")
async def update_ght_context(
    request: Request,
    context_id: int,
    name: str = Form(...),
    code: str = Form(...),
    description: Optional[str] = Form(None),
    is_active: str = Form("true"),
    session: Session = Depends(get_session)
):
    """Met à jour un contexte GHT existant."""
    context = session.get(GHTContext, context_id)
    if not context:
        raise HTTPException(status_code=404, detail="Contexte non trouvé")
    
    # Vérifier l'unicité du code si modifié
    if code != context.code:
        existing = session.exec(
            select(GHTContext).where(GHTContext.code == code)
        ).first()
        if existing:
            flash(request, "Ce code est déjà utilisé par un autre contexte GHT.", "error")
            accept = request.headers.get("accept", "")
            if "application/json" in accept:
                return {"ok": False, "message": "Ce code est déjà utilisé", "errors": {"code": "Code déjà utilisé"}}

            return templates.TemplateResponse(
                "ght_form.html",
                {
                    "request": request,
                    "context": context,
                    "form_data": {
                        "name": name,
                        "code": code,
                        "description": description,
                        "is_active": is_active,
                    },
                },
                status_code=400,
            )
    
    context.name = name
    context.code = code
    context.description = description
    context.is_active = str(is_active).lower() in ("1", "true", "yes", "on")
    context.updated_at = datetime.utcnow()
    
    session.add(context)
    session.commit()

    flash(request, f'Contexte GHT "{context.name}" mis à jour.', "success")
    accept = request.headers.get("accept", "")
    if "application/json" in accept:
        return {"ok": True, "id": context.id, "redirect": "/admin/ght"}

    return RedirectResponse(
        "/admin/ght",
        status_code=303
    )

@router.get("/{context_id}")
async def view_ght_context(
    request: Request,
    context_id: int,
    session: Session = Depends(get_session)
):
    """Affiche les détails d'un contexte GHT et ses entités."""
    context = session.get(GHTContext, context_id)
    if not context:
        raise HTTPException(status_code=404, detail="Contexte non trouvé")
    
    # Stocker le contexte sélectionné en session
    request.session["ght_context_id"] = context_id
    
    selected_ej_id = request.session.get(f"ght_{context_id}_ej_id")
    selected_ej_name = request.session.get(f"ght_{context_id}_ej_name")
    return templates.TemplateResponse(
        "ght_detail.html",
        {
            "request": request,
            "context": context,
            "namespaces": context.namespaces,
            "entites_juridiques": context.entites_juridiques,
            "selected_ej_id": selected_ej_id,
            "selected_ej_name": selected_ej_name,
        }
    )

@router.post("/{context_id}/seed-demo")
async def seed_demo_structure(
    request: Request,
    context_id: int,
    session: Session = Depends(get_session),
):
    """Génère ou met à jour une structure hospitalière de démonstration pour ce GHT."""
    context = _get_context_or_404(session, context_id)
    stats = ensure_demo_structure(session, context)

    summary_parts = []
    label_map = {
        "entite_juridique": "entité juridique",
        "entite_geographique": "site géographique",
        "pole": "pôle",
        "service": "service",
        "unite_fonctionnelle": "UF",
        "unite_hebergement": "UH",
        "chambre": "chambre",
        "lit": "lit",
    }
    for key, label in label_map.items():
        created = stats["created"].get(key, 0)
        updated = stats["updated"].get(key, 0)
        if created or updated:
            summary_parts.append(f"{label}s +{created}/~{updated}")

    message = "Structure de démonstration générée."
    if summary_parts:
        message += " " + ", ".join(summary_parts) + "."

    flash(request, message, "success")
    return RedirectResponse(f"/admin/ght/{context_id}", status_code=303)


def _get_context_or_404(session: Session, context_id: int) -> GHTContext:
    context = session.get(GHTContext, context_id)
    if not context:
        raise HTTPException(status_code=404, detail="Contexte non trouvé")
    return context


def _get_ej_or_404(
    session: Session, context: GHTContext, ej_id: int
) -> EntiteJuridique:
    entite = session.exec(
        select(EntiteJuridique)
        .where(EntiteJuridique.id == ej_id)
        .where(EntiteJuridique.ght_context_id == context.id)
    ).first()
    if not entite:
        raise HTTPException(status_code=404, detail="Entité juridique non trouvée")
    return entite


def _get_entite_geo_or_404(
    session: Session, entite: EntiteJuridique, eg_id: int
) -> EntiteGeographique:
    entite_geo = session.exec(
        select(EntiteGeographique)
        .where(EntiteGeographique.id == eg_id)
        .where(EntiteGeographique.entite_juridique_id == entite.id)
    ).first()
    if not entite_geo:
        raise HTTPException(status_code=404, detail="Entité géographique non trouvée")
    return entite_geo


def _get_pole_or_404(
    session: Session, entite_geo: EntiteGeographique, pole_id: int
) -> Pole:
    pole = session.exec(
        select(Pole)
        .where(Pole.id == pole_id)
        .where(Pole.entite_geo_id == entite_geo.id)
    ).first()
    if not pole:
        raise HTTPException(status_code=404, detail="Pôle non trouvé")
    return pole


def _get_service_or_404(
    session: Session, pole: Pole, service_id: int
) -> Service:
    service = session.exec(
        select(Service)
        .where(Service.id == service_id)
        .where(Service.pole_id == pole.id)
    ).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service non trouvé")
    return service


def _get_uf_or_404(
    session: Session, service: Service, uf_id: int
) -> UniteFonctionnelle:
    uf = session.exec(
        select(UniteFonctionnelle)
        .where(UniteFonctionnelle.id == uf_id)
        .where(UniteFonctionnelle.service_id == service.id)
    ).first()
    if not uf:
        raise HTTPException(status_code=404, detail="Unité fonctionnelle non trouvée")
    return uf


def _get_uh_or_404(
    session: Session, uf: UniteFonctionnelle, uh_id: int
) -> UniteHebergement:
    uh = session.exec(
        select(UniteHebergement)
        .where(UniteHebergement.id == uh_id)
        .where(UniteHebergement.unite_fonctionnelle_id == uf.id)
    ).first()
    if not uh:
        raise HTTPException(status_code=404, detail="Unité d'hébergement non trouvée")
    return uh


def _get_chambre_or_404(
    session: Session, uh: UniteHebergement, chambre_id: int
) -> Chambre:
    chambre = session.exec(
        select(Chambre)
        .where(Chambre.id == chambre_id)
        .where(Chambre.unite_hebergement_id == uh.id)
    ).first()
    if not chambre:
        raise HTTPException(status_code=404, detail="Chambre non trouvée")
    return chambre


def _get_lit_or_404(
    session: Session, chambre: Chambre, lit_id: int
) -> Lit:
    lit = session.exec(
        select(Lit)
        .where(Lit.id == lit_id)
        .where(Lit.chambre_id == chambre.id)
    ).first()
    if not lit:
        raise HTTPException(status_code=404, detail="Lit non trouvé")
    return lit


STATUS_LABELS = {
    LocationStatus.ACTIVE.value: "Actif",
    LocationStatus.SUSPENDED.value: "Suspendu",
    LocationStatus.INACTIVE.value: "Inactif",
}

MODE_LABELS = {
    LocationMode.INSTANCE.value: "Instance",
    LocationMode.KIND.value: "Type",
}

PHYSICAL_TYPE_LABELS = {
    LocationPhysicalType.SI.value: "Site (si)",
    LocationPhysicalType.BU.value: "Bâtiment (bu)",
    LocationPhysicalType.WI.value: "Aile (wi)",
    LocationPhysicalType.FL.value: "Étage (fl)",
    LocationPhysicalType.RO.value: "Chambre (ro)",
    LocationPhysicalType.BD.value: "Lit (bd)",
    LocationPhysicalType.VE.value: "Véhicule (ve)",
    LocationPhysicalType.HO.value: "Domicile (ho)",
    LocationPhysicalType.CA.value: "Cabinet (ca)",
    LocationPhysicalType.RD.value: "Route (rd)",
    LocationPhysicalType.AREA.value: "Zone (area)",
    LocationPhysicalType.JDN.value: "Juridiction (jdn)",
}

SERVICE_TYPE_LABELS = {
    LocationServiceType.MCO.value: "Médecine/Chirurgie/Obstétrique (MCO)",
    LocationServiceType.SSR.value: "Soins de suite et de réadaptation (SSR)",
    LocationServiceType.PSY.value: "Psychiatrie (PSY)",
    LocationServiceType.HAD.value: "Hospitalisation à domicile (HAD)",
    LocationServiceType.EHPAD.value: "EHPAD",
    LocationServiceType.USLD.value: "Unités de soins longue durée (USLD)",
}

PHYSICAL_TYPE_DEFAULTS = {
    "entite_geographique": LocationPhysicalType.SI,
    "pole": LocationPhysicalType.AREA,
    "service": LocationPhysicalType.AREA,
    "uf": LocationPhysicalType.AREA,
    "uh": LocationPhysicalType.FL,
    "chambre": LocationPhysicalType.RO,
    "lit": LocationPhysicalType.BD,
}


def _resolve_physical_type(entity_name: str, current: Optional[str]) -> LocationPhysicalType:
    if current:
        try:
            return LocationPhysicalType(current)
        except ValueError:
            pass
    return PHYSICAL_TYPE_DEFAULTS[entity_name]


def _status_options() -> List[dict]:
    return [
        {"value": status.value, "label": STATUS_LABELS.get(status.value, status.value)}
        for status in LocationStatus
    ]


def _mode_options() -> List[dict]:
    return [
        {"value": mode.value, "label": MODE_LABELS.get(mode.value, mode.value)}
        for mode in LocationMode
    ]


def _physical_type_options() -> List[dict]:
    return [
        {"value": typ.value, "label": PHYSICAL_TYPE_LABELS.get(typ.value, typ.value)}
        for typ in LocationPhysicalType
    ]


def _service_type_options() -> List[dict]:
    return [
        {
            "value": service_type.value,
            "label": SERVICE_TYPE_LABELS.get(service_type.value, service_type.value),
        }
        for service_type in LocationServiceType
    ]


def _maybe(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _pole_form_fields(pole: Optional[Pole] = None) -> List[dict]:
    return [
        {
            "name": "identifier",
            "label": "Identifiant global",
            "type": "text",
            "required": True,
            "value": pole.identifier if pole else "",
        },
        {
            "name": "name",
            "label": "Nom",
            "type": "text",
            "required": True,
            "value": pole.name if pole else "",
        },
        {
            "name": "short_name",
            "label": "Nom court",
            "type": "text",
            "value": pole.short_name if pole else "",
        },
        {
            "name": "description",
            "label": "Description",
            "type": "text",
            "value": pole.description if pole else "",
        },
        {
            "name": "status",
            "label": "Statut",
            "type": "select",
            "options": _status_options(),
            "value": (pole.status.value if isinstance(pole.status, LocationStatus) else getattr(pole, "status", LocationStatus.ACTIVE.value))
            if pole
            else LocationStatus.ACTIVE.value,
        },
        {
            "name": "mode",
            "label": "Mode",
            "type": "select",
            "options": _mode_options(),
            "value": (pole.mode.value if isinstance(pole.mode, LocationMode) else getattr(pole, "mode", LocationMode.INSTANCE.value))
            if pole
            else LocationMode.INSTANCE.value,
        },
    ]


def _service_form_fields(service: Optional[Service] = None) -> List[dict]:
    return [
        {
            "name": "identifier",
            "label": "Identifiant global",
            "type": "text",
            "required": True,
            "value": service.identifier if service else "",
        },
        {
            "name": "name",
            "label": "Nom du service",
            "type": "text",
            "required": True,
            "value": service.name if service else "",
        },
        {
            "name": "short_name",
            "label": "Nom court",
            "type": "text",
            "value": service.short_name if service else "",
        },
        {
            "name": "description",
            "label": "Description",
            "type": "text",
            "value": service.description if service else "",
        },
        {
            "name": "status",
            "label": "Statut",
            "type": "select",
            "options": _status_options(),
            "value": (service.status.value if isinstance(service.status, LocationStatus) else getattr(service, "status", LocationStatus.ACTIVE.value))
            if service
            else LocationStatus.ACTIVE.value,
        },
        {
            "name": "mode",
            "label": "Mode",
            "type": "select",
            "options": _mode_options(),
            "value": (service.mode.value if isinstance(service.mode, LocationMode) else getattr(service, "mode", LocationMode.INSTANCE.value))
            if service
            else LocationMode.INSTANCE.value,
        },
        {
            "name": "service_type",
            "label": "Type de service",
            "type": "select",
            "options": _service_type_options(),
            "value": (service.service_type.value if isinstance(service.service_type, LocationServiceType) else getattr(service, "service_type", LocationServiceType.MCO.value))
            if service
            else LocationServiceType.MCO.value,
        },
        {
            "name": "typology",
            "label": "Typologie",
            "type": "text",
            "value": service.typology if service else "",
        },
    ]


def _uf_form_fields(uf: Optional[UniteFonctionnelle] = None) -> List[dict]:
    return [
        {
            "name": "identifier",
            "label": "Identifiant global",
            "type": "text",
            "required": True,
            "value": uf.identifier if uf else "",
        },
        {
            "name": "name",
            "label": "Nom de l'UF",
            "type": "text",
            "required": True,
            "value": uf.name if uf else "",
        },
        {
            "name": "short_name",
            "label": "Nom court",
            "type": "text",
            "value": uf.short_name if uf else "",
        },
        {
            "name": "description",
            "label": "Description",
            "type": "text",
            "value": uf.description if uf else "",
        },
        {
            "name": "status",
            "label": "Statut",
            "type": "select",
            "options": _status_options(),
            "value": (uf.status.value if isinstance(uf.status, LocationStatus) else getattr(uf, "status", LocationStatus.ACTIVE.value))
            if uf
            else LocationStatus.ACTIVE.value,
        },
        {
            "name": "mode",
            "label": "Mode",
            "type": "select",
            "options": _mode_options(),
            "value": (uf.mode.value if isinstance(uf.mode, LocationMode) else getattr(uf, "mode", LocationMode.INSTANCE.value))
            if uf
            else LocationMode.INSTANCE.value,
        },
        {
            "name": "um_code",
            "label": "Code UM",
            "type": "text",
            "value": uf.um_code if uf else "",
        },
        {
            "name": "uf_type",
            "label": "Type d'UF",
            "type": "text",
            "value": uf.uf_type if uf else "",
        },
    ]


def _uh_form_fields(uh: Optional[UniteHebergement] = None) -> List[dict]:
    return [
        {
            "name": "identifier",
            "label": "Identifiant global",
            "type": "text",
            "required": True,
            "value": uh.identifier if uh else "",
        },
        {
            "name": "name",
            "label": "Nom de l'UH",
            "type": "text",
            "required": True,
            "value": uh.name if uh else "",
        },
        {
            "name": "short_name",
            "label": "Nom court",
            "type": "text",
            "value": uh.short_name if uh else "",
        },
        {
            "name": "description",
            "label": "Description",
            "type": "text",
            "value": uh.description if uh else "",
        },
        {
            "name": "status",
            "label": "Statut",
            "type": "select",
            "options": _status_options(),
            "value": (uh.status.value if isinstance(uh.status, LocationStatus) else getattr(uh, "status", LocationStatus.ACTIVE.value))
            if uh
            else LocationStatus.ACTIVE.value,
        },
        {
            "name": "mode",
            "label": "Mode",
            "type": "select",
            "options": _mode_options(),
            "value": (uh.mode.value if isinstance(uh.mode, LocationMode) else getattr(uh, "mode", LocationMode.INSTANCE.value))
            if uh
            else LocationMode.INSTANCE.value,
        },
        {
            "name": "etage",
            "label": "Étage",
            "type": "text",
            "value": uh.etage if uh else "",
        },
        {
            "name": "aile",
            "label": "Aile",
            "type": "text",
            "value": uh.aile if uh else "",
        },
    ]


def _chambre_form_fields(chambre: Optional[Chambre] = None) -> List[dict]:
    return [
        {
            "name": "identifier",
            "label": "Identifiant global",
            "type": "text",
            "required": True,
            "value": chambre.identifier if chambre else "",
        },
        {
            "name": "name",
            "label": "Nom de la chambre",
            "type": "text",
            "required": True,
            "value": chambre.name if chambre else "",
        },
        {
            "name": "short_name",
            "label": "Nom court",
            "type": "text",
            "value": chambre.short_name if chambre else "",
        },
        {
            "name": "description",
            "label": "Description",
            "type": "text",
            "value": chambre.description if chambre else "",
        },
        {
            "name": "status",
            "label": "Statut",
            "type": "select",
            "options": _status_options(),
            "value": (chambre.status.value if isinstance(chambre.status, LocationStatus) else getattr(chambre, "status", LocationStatus.ACTIVE.value))
            if chambre
            else LocationStatus.ACTIVE.value,
        },
        {
            "name": "mode",
            "label": "Mode",
            "type": "select",
            "options": _mode_options(),
            "value": (chambre.mode.value if isinstance(chambre.mode, LocationMode) else getattr(chambre, "mode", LocationMode.INSTANCE.value))
            if chambre
            else LocationMode.INSTANCE.value,
        },
        {
            "name": "type_chambre",
            "label": "Type de chambre",
            "type": "text",
            "value": chambre.type_chambre if chambre else "",
        },
        {
            "name": "gender_usage",
            "label": "Usage (genre)",
            "type": "text",
            "value": chambre.gender_usage if chambre else "",
        },
    ]


def _lit_form_fields(lit: Optional[Lit] = None) -> List[dict]:
    return [
        {
            "name": "identifier",
            "label": "Identifiant global",
            "type": "text",
            "required": True,
            "value": lit.identifier if lit else "",
        },
        {
            "name": "name",
            "label": "Nom du lit",
            "type": "text",
            "required": True,
            "value": lit.name if lit else "",
        },
        {
            "name": "short_name",
            "label": "Nom court",
            "type": "text",
            "value": lit.short_name if lit else "",
        },
        {
            "name": "description",
            "label": "Description",
            "type": "text",
            "value": lit.description if lit else "",
        },
        {
            "name": "status",
            "label": "Statut",
            "type": "select",
            "options": _status_options(),
            "value": (lit.status.value if isinstance(lit.status, LocationStatus) else getattr(lit, "status", LocationStatus.ACTIVE.value))
            if lit
            else LocationStatus.ACTIVE.value,
        },
        {
            "name": "mode",
            "label": "Mode",
            "type": "select",
            "options": _mode_options(),
            "value": (lit.mode.value if isinstance(lit.mode, LocationMode) else getattr(lit, "mode", LocationMode.INSTANCE.value))
            if lit
            else LocationMode.INSTANCE.value,
        },
        {
            "name": "operational_status",
            "label": "Statut opérationnel",
            "type": "text",
            "value": lit.operational_status if lit else "",
        },
    ]


def _with_form_values(fields: List[dict], data: dict) -> List[dict]:
    filled = []
    for field in fields:
        field_copy = field.copy()
        name = field_copy.get("name")
        if name in data:
            field_copy["value"] = data[name]
        filled.append(field_copy)
    return filled


def _render_form(
    request: Request,
    title: str,
    fields: List[dict],
    action_url: str,
    cancel_url: str,
    error: Optional[str] = None,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        "forms.html",
        {
            "request": request,
            "title": title,
            "fields": fields,
            "action_url": action_url,
            "cancel_url": cancel_url,
            "error": error,
        },
        status_code=status_code,
    )


@router.get("/{context_id}/ej/new")
async def new_entite_juridique_form(
    request: Request,
    context_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    return templates.TemplateResponse(
        "ej_form.html",
        {"request": request, "context": context, "entite": None},
    )


@router.post("/{context_id}/ej/new")
async def create_entite_juridique(
    request: Request,
    context_id: int,
    name: str = Form(...),
    finess_ej: str = Form(...),
    short_name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    siren: Optional[str] = Form(None),
    siret: Optional[str] = Form(None),
    address_line: Optional[str] = Form(None),
    postal_code: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    country: Optional[str] = Form("FR"),
    is_active: str = Form("true"),
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)

    existing = session.exec(
        select(EntiteJuridique).where(
            EntiteJuridique.finess_ej == finess_ej
        )
    ).first()
    if existing:
        flash(
            request,
            "Une entité juridique avec ce FINESS existe déjà.",
            "error",
        )
        return templates.TemplateResponse(
            "ej_form.html",
            {
                "request": request,
                "context": context,
                "entite": None,
                "form_data": {
                    "name": name,
                    "finess_ej": finess_ej,
                    "short_name": short_name,
                    "description": description,
                    "siren": siren,
                    "siret": siret,
                    "address_line": address_line,
                    "postal_code": postal_code,
                    "city": city,
                    "country": country,
                    "is_active": is_active,
                },
            },
            status_code=400,
        )

    entite = EntiteJuridique(
        name=name,
        finess_ej=finess_ej,
        short_name=short_name,
        description=description,
        siren=siren,
        siret=siret,
        address_line=address_line,
        postal_code=postal_code,
        city=city,
        country=country or "FR",
        is_active=str(is_active).lower() in ("1", "true", "yes", "on"),
        ght_context_id=context.id,
    )
    session.add(entite)
    session.commit()

    flash(
        request,
        f'Entité juridique "{entite.name}" créée avec succès.',
        "success",
    )
    return RedirectResponse(
        f"/admin/ght/{context.id}",
        status_code=303,
    )


@router.get("/{context_id}/ej/{ej_id}")
async def view_entite_juridique(
    request: Request,
    context_id: int,
    ej_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    # Poser les contextes en session et sur request.state pour l'affichage immédiat
    request.session["ght_context_id"] = context_id
    request.session["ej_context_id"] = ej_id
    # Pour éviter d'attendre la requête suivante, alimenter aussi request.state
    try:
        request.state.ght_context = context
        request.state.ej_context = entite
    except Exception:
        pass

    geo_ids = [geo.id for geo in entite.entites_geographiques]

    pole_ids: List[int] = []
    service_ids: List[int] = []
    uf_ids: List[int] = []
    uh_ids: List[int] = []
    chambre_ids: List[int] = []

    if geo_ids:
        pole_ids = list(
            session.exec(select(Pole.id).where(Pole.entite_geo_id.in_(geo_ids)))
        )
    if pole_ids:
        service_ids = list(
            session.exec(select(Service.id).where(Service.pole_id.in_(pole_ids)))
        )
    if service_ids:
        uf_ids = list(
            session.exec(
                select(UniteFonctionnelle.id).where(
                    UniteFonctionnelle.service_id.in_(service_ids)
                )
            )
        )
    if uf_ids:
        uh_ids = list(
            session.exec(
                select(UniteHebergement.id).where(
                    UniteHebergement.unite_fonctionnelle_id.in_(uf_ids)
                )
            )
        )
    if uh_ids:
        chambre_ids = list(
            session.exec(
                select(Chambre.id).where(Chambre.unite_hebergement_id.in_(uh_ids))
            )
        )

    lit_count = 0
    if chambre_ids:
        lit_count = session.exec(
            select(func.count(Lit.id)).where(Lit.chambre_id.in_(chambre_ids))
        ).one()

    counts = {
        "entites_geo": len(geo_ids),
        "entites_geo_actives": sum(
            1 for geo in entite.entites_geographiques if getattr(geo, "is_active", True)
        ),
        "poles": len(pole_ids),
        "services": len(service_ids),
        "ufs": len(uf_ids),
        "uhs": len(uh_ids),
        "chambres": len(chambre_ids),
        "lits": lit_count,
    }

    # Charger les namespaces de cette EJ
    namespaces = session.exec(
        select(IdentifierNamespace)
        .where(IdentifierNamespace.entite_juridique_id == ej_id)
        .order_by(IdentifierNamespace.type, IdentifierNamespace.name)
    ).all()

    return templates.TemplateResponse(
        "ej_detail.html",
        {
            "request": request,
            "context": context,
            "entite": entite,
            "entites_geographiques": entite.entites_geographiques,
            "namespaces": namespaces,
            "counts": counts,
        },
    )


@router.get("/{context_id}/ej/{ej_id}/edit")
async def edit_entite_juridique_form(
    request: Request,
    context_id: int,
    ej_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)

    return templates.TemplateResponse(
        "ej_form.html",
        {"request": request, "context": context, "entite": entite},
    )


@router.post("/{context_id}/ej/{ej_id}/edit")
async def update_entite_juridique(
    request: Request,
    context_id: int,
    ej_id: int,
    name: str = Form(...),
    finess_ej: str = Form(...),
    short_name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    siren: Optional[str] = Form(None),
    siret: Optional[str] = Form(None),
    address_line: Optional[str] = Form(None),
    postal_code: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    country: Optional[str] = Form("FR"),
    is_active: str = Form("true"),
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)

    if finess_ej != entite.finess_ej:
        exists = session.exec(
            select(EntiteJuridique)
            .where(EntiteJuridique.finess_ej == finess_ej)
            .where(EntiteJuridique.id != entite.id)
        ).first()
        if exists:
            flash(
                request,
                "Une entité juridique avec ce FINESS existe déjà.",
                "error",
            )
            return templates.TemplateResponse(
                "ej_form.html",
                {
                    "request": request,
                    "context": context,
                    "entite": entite,
                    "form_data": {
                        "name": name,
                        "finess_ej": finess_ej,
                        "short_name": short_name,
                        "description": description,
                        "siren": siren,
                        "siret": siret,
                        "address_line": address_line,
                        "postal_code": postal_code,
                        "city": city,
                        "country": country,
                        "is_active": is_active,
                    },
                },
                status_code=400,
            )

    entite.name = name
    entite.finess_ej = finess_ej
    entite.short_name = short_name
    entite.description = description
    entite.siren = siren
    entite.siret = siret
    entite.address_line = address_line
    entite.postal_code = postal_code
    entite.city = city
    entite.country = country or "FR"
    entite.is_active = str(is_active).lower() in ("1", "true", "yes", "on")
    entite.updated_at = datetime.utcnow()

    session.add(entite)
    session.commit()

    flash(
        request,
        f'Entité juridique "{entite.name}" mise à jour.',
        "success",
    )
    return RedirectResponse(
        f"/admin/ght/{context.id}/ej/{entite.id}",
        status_code=303,
    )


@router.post("/{context_id}/ej/{ej_id}/clone")
async def clone_entite_juridique_structure(
    request: Request,
    context_id: int,
    ej_id: int,
    new_name: str = Form(...),
    new_finess_ej: str = Form(...),
    session: Session = Depends(get_session),
):
    """Clone la structure complète d'une EJ (EG, Pôles, Services, UF, UH, Chambres, Lits)."""
    context = _get_context_or_404(session, context_id)
    source_ej = _get_ej_or_404(session, context, ej_id)
    
    # Vérifier que le FINESS n'existe pas déjà
    existing = session.exec(
        select(EntiteJuridique).where(EntiteJuridique.finess_ej == new_finess_ej)
    ).first()
    if existing:
        flash(request, f"Une entité juridique avec le FINESS {new_finess_ej} existe déjà.", "error")
        return RedirectResponse(f"/admin/ght/{context_id}/ej/{ej_id}", status_code=303)
    
    # Créer la nouvelle EJ
    new_ej = EntiteJuridique(
        name=new_name,
        finess_ej=new_finess_ej,
        short_name=f"{source_ej.short_name} (Clonée)" if source_ej.short_name else None,
        description=f"Clone de {source_ej.name}",
        siren=None,  # Ne pas copier les identifiants légaux
        siret=None,
        address_line=source_ej.address_line,
        postal_code=source_ej.postal_code,
        city=source_ej.city,
        country=source_ej.country,
        is_active=source_ej.is_active,
        ght_context_id=context.id,
    )
    session.add(new_ej)
    session.flush()  # Pour obtenir l'ID
    
    # Mappings pour relier les anciennes IDs aux nouvelles
    eg_map = {}
    pole_map = {}
    service_map = {}
    uf_map = {}
    uh_map = {}
    chambre_map = {}
    
    # Cloner les EG
    for source_eg in source_ej.entites_geographiques:
        new_eg = EntiteGeographique(
            name=source_eg.name,
            identifier=f"{source_eg.identifier}_clone",
            finess=f"CLN{source_eg.finess[3:]}" if source_eg.finess else None,  # Modifier FINESS
            short_name=source_eg.short_name,
            description=source_eg.description,
            address_line=source_eg.address_line,
            postal_code=source_eg.postal_code,
            city=source_eg.city,
            country=source_eg.country,
            status=source_eg.status,
            mode=source_eg.mode,
            physical_type=source_eg.physical_type,
            entite_juridique_id=new_ej.id,
        )
        session.add(new_eg)
        session.flush()
        eg_map[source_eg.id] = new_eg.id
        
        # Cloner les Pôles
        for source_pole in source_eg.poles:
            new_pole = Pole(
                name=source_pole.name,
                identifier=f"{source_pole.identifier}_clone",
                short_name=source_pole.short_name,
                description=source_pole.description,
                status=source_pole.status,
                mode=source_pole.mode,
                physical_type=source_pole.physical_type,
                entite_geo_id=new_eg.id,
            )
            session.add(new_pole)
            session.flush()
            pole_map[source_pole.id] = new_pole.id
            
            # Cloner les Services
            for source_service in source_pole.services:
                new_service = Service(
                    name=source_service.name,
                    identifier=f"{source_service.identifier}_clone",
                    short_name=source_service.short_name,
                    description=source_service.description,
                    status=source_service.status,
                    mode=source_service.mode,
                    physical_type=source_service.physical_type,
                    service_type=source_service.service_type,
                    typology=source_service.typology,
                    pole_id=new_pole.id,
                )
                session.add(new_service)
                session.flush()
                service_map[source_service.id] = new_service.id
                
                # Cloner les UF
                for source_uf in source_service.unites_fonctionnelles:
                    new_uf = UniteFonctionnelle(
                        name=source_uf.name,
                        identifier=f"{source_uf.identifier}_clone",
                        short_name=source_uf.short_name,
                        description=source_uf.description,
                        status=source_uf.status,
                        mode=source_uf.mode,
                        physical_type=source_uf.physical_type,
                        um_code=source_uf.um_code,
                        uf_type=source_uf.uf_type,
                        service_id=new_service.id,
                    )
                    session.add(new_uf)
                    session.flush()
                    uf_map[source_uf.id] = new_uf.id
                    
                    # Cloner les UH
                    for source_uh in source_uf.unites_hebergement:
                        new_uh = UniteHebergement(
                            name=source_uh.name,
                            identifier=f"{source_uh.identifier}_clone",
                            short_name=source_uh.short_name,
                            description=source_uh.description,
                            status=source_uh.status,
                            mode=source_uh.mode,
                            physical_type=source_uh.physical_type,
                            etage=source_uh.etage,
                            aile=source_uh.aile,
                            unite_fonctionnelle_id=new_uf.id,
                        )
                        session.add(new_uh)
                        session.flush()
                        uh_map[source_uh.id] = new_uh.id
                        
                        # Cloner les Chambres
                        for source_chambre in source_uh.chambres:
                            new_chambre = Chambre(
                                name=source_chambre.name,
                                identifier=f"{source_chambre.identifier}_clone",
                                short_name=source_chambre.short_name,
                                description=source_chambre.description,
                                status=source_chambre.status,
                                mode=source_chambre.mode,
                                physical_type=source_chambre.physical_type,
                                type_chambre=source_chambre.type_chambre,
                                gender_usage=source_chambre.gender_usage,
                                unite_hebergement_id=new_uh.id,
                            )
                            session.add(new_chambre)
                            session.flush()
                            chambre_map[source_chambre.id] = new_chambre.id
                            
                            # Cloner les Lits
                            for source_lit in source_chambre.lits:
                                new_lit = Lit(
                                    name=source_lit.name,
                                    identifier=f"{source_lit.identifier}_clone",
                                    short_name=source_lit.short_name,
                                    description=source_lit.description,
                                    status=source_lit.status,
                                    mode=source_lit.mode,
                                    physical_type=source_lit.physical_type,
                                    operational_status=source_lit.operational_status,
                                    chambre_id=new_chambre.id,
                                )
                                session.add(new_lit)
    
    session.commit()
    
    # Compter les éléments clonés
    total_eg = len(eg_map)
    total_poles = len(pole_map)
    total_services = len(service_map)
    total_uf = len(uf_map)
    total_uh = len(uh_map)
    total_chambres = len(chambre_map)
    total_lits = session.exec(
        select(func.count(Lit.id))
        .join(Chambre)
        .where(Chambre.id.in_(list(chambre_map.values())))
    ).one()
    
    flash(
        request,
        f'Structure clonée avec succès : {total_eg} EG, {total_poles} pôles, {total_services} services, {total_uf} UF, {total_uh} UH, {total_chambres} chambres, {total_lits} lits.',
        "success",
    )
    return RedirectResponse(f"/admin/ght/{context_id}/ej/{new_ej.id}", status_code=303)


@router.get("/{context_id}/ej/{ej_id}/eg/new")
async def new_entite_geographique_form(
    request: Request,
    context_id: int,
    ej_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)

    return templates.TemplateResponse(
        "eg_form.html",
        {
            "request": request,
            "context": context,
            "entite": entite,
            "geo": None,
        },
    )


@router.post("/{context_id}/ej/{ej_id}/eg/new")
async def create_entite_geographique(
    request: Request,
    context_id: int,
    ej_id: int,
    name: str = Form(...),
    identifier: str = Form(...),
    finess: str = Form(...),
    short_name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    status: str = Form(LocationStatus.ACTIVE.value),
    mode: str = Form(LocationMode.INSTANCE.value),
    physical_type: str = Form(LocationPhysicalType.SI.value),
    is_active: str = Form("true"),
    siren: Optional[str] = Form(None),
    siret: Optional[str] = Form(None),
    address_line1: Optional[str] = Form(None),
    address_line2: Optional[str] = Form(None),
    address_line3: Optional[str] = Form(None),
    address_postalcode: Optional[str] = Form(None),
    address_city: Optional[str] = Form(None),
    latitude: Optional[str] = Form(None),
    longitude: Optional[str] = Form(None),
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)

    wants_json = "application/json" in (request.headers.get("accept") or "")

    form_payload = {
        "name": name,
        "identifier": identifier,
        "finess": finess,
        "short_name": short_name,
        "description": description,
        "status": status,
        "mode": mode,
        "physical_type": physical_type,
        "is_active": is_active,
        "siren": siren,
        "siret": siret,
        "address_line1": address_line1,
        "address_line2": address_line2,
        "address_line3": address_line3,
        "address_postalcode": address_postalcode,
        "address_city": address_city,
        "latitude": latitude,
        "longitude": longitude,
    }

    duplicate_identifier = session.exec(
        select(EntiteGeographique).where(EntiteGeographique.identifier == identifier)
    ).first()
    if duplicate_identifier:
        if wants_json:
            return {
                "ok": False,
                "message": "Un identifiant global identique existe déjà.",
                "errors": {"identifier": "Identifiant déjà utilisé"},
            }
        flash(request, "Un identifiant global identique existe déjà.", "error")
        return templates.TemplateResponse(
            "eg_form.html",
            {
                "request": request,
                "context": context,
                "entite": entite,
                "geo": None,
                "form_data": form_payload,
            },
            status_code=400,
        )

    duplicate_finess = session.exec(
        select(EntiteGeographique)
        .where(EntiteGeographique.finess == finess)
        .where(EntiteGeographique.entite_juridique_id == entite.id)
    ).first()
    if duplicate_finess:
        if wants_json:
            return {
                "ok": False,
                "message": "Une entité géographique possède déjà ce FINESS.",
                "errors": {"finess": "FINESS déjà utilisé"},
            }
        flash(
            request,
            "Une entité géographique de ce GHT possède déjà ce FINESS.",
            "error",
        )
        return templates.TemplateResponse(
            "eg_form.html",
            {
                "request": request,
                "context": context,
                "entite": entite,
                "geo": None,
                "form_data": form_payload,
            },
            status_code=400,
        )

    try:
        latitude_value = float(latitude) if latitude else None
    except ValueError:
        if wants_json:
            return {
                "ok": False,
                "message": "Latitude invalide, merci de saisir un nombre.",
                "errors": {"latitude": "Latitude invalide"},
            }
        flash(request, "Latitude invalide, merci de saisir un nombre.", "error")
        return templates.TemplateResponse(
            "eg_form.html",
            {
                "request": request,
                "context": context,
                "entite": entite,
                "geo": None,
                "form_data": form_payload,
            },
            status_code=400,
        )

    try:
        longitude_value = float(longitude) if longitude else None
    except ValueError:
        if wants_json:
            return {
                "ok": False,
                "message": "Longitude invalide, merci de saisir un nombre.",
                "errors": {"longitude": "Longitude invalide"},
            }
        flash(request, "Longitude invalide, merci de saisir un nombre.", "error")
        return templates.TemplateResponse(
            "eg_form.html",
            {
                "request": request,
                "context": context,
                "entite": entite,
                "geo": None,
                "form_data": form_payload,
            },
            status_code=400,
        )

    try:
        status_value = LocationStatus(status).value
        mode_value = LocationMode(mode).value
    except ValueError:
        if wants_json:
            return {
                "ok": False,
                "message": "Statut ou mode invalide.",
                "errors": {"status": "Valeur invalide"},
            }
        flash(
            request,
            "Statut ou mode invalide.",
            "error",
        )
        return templates.TemplateResponse(
            "eg_form.html",
            {
                "request": request,
                "context": context,
                "entite": entite,
                "geo": None,
                "form_data": form_payload,
            },
            status_code=400,
        )

    physical_value = _resolve_physical_type("entite_geographique", physical_type).value

    geo = EntiteGeographique(
        name=name,
        identifier=identifier,
        short_name=short_name,
        description=description,
        status=status_value,
        mode=mode_value,
        physical_type=physical_value,
        finess=finess,
        siren=siren,
        siret=siret,
        address_line1=address_line1,
        address_line2=address_line2,
        address_line3=address_line3,
        address_postalcode=address_postalcode,
        address_city=address_city,
        latitude=latitude_value,
        longitude=longitude_value,
        is_active=str(is_active).lower() in ("1", "true", "yes", "on"),
        entite_juridique_id=entite.id,
    )
    session.add(geo)
    session.commit()
    session.refresh(geo)

    flash(request, f'Entité géographique "{geo.name}" créée.', "success")
    if wants_json:
        return {
            "ok": True,
            "id": geo.id,
            "redirect": f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}",
        }
    return RedirectResponse(
        f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}",
        status_code=303,
    )


@router.get("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/new")
async def new_pole_form(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)

    fields = _pole_form_fields()
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/new"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"
    return _render_form(
        request,
        "Nouveau pôle",
        fields,
        action_url,
        cancel_url,
    )


@router.post("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/new")
async def create_pole(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)

    form = await request.form()
    data = {key: form.get(key) for key in form.keys()}
    fields = _with_form_values(_pole_form_fields(), data)
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/new"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"

    identifier = _maybe(data.get("identifier"))
    name = _maybe(data.get("name"))
    if not identifier or not name:
        return _render_form(
            request,
            "Nouveau pôle",
            fields,
            action_url,
            cancel_url,
            error="L'identifiant global et le nom sont obligatoires.",
            status_code=400,
        )

    duplicate = session.exec(
        select(Pole).where(Pole.identifier == identifier)
    ).first()
    if duplicate:
        return _render_form(
            request,
            "Nouveau pôle",
            fields,
            action_url,
            cancel_url,
            error="Un pôle avec cet identifiant existe déjà.",
            status_code=400,
        )

    try:
        status_enum = LocationStatus(data.get("status") or LocationStatus.ACTIVE.value)
        mode_enum = LocationMode(data.get("mode") or LocationMode.INSTANCE.value)
    except ValueError:
        return _render_form(
            request,
            "Nouveau pôle",
            fields,
            action_url,
            cancel_url,
            error="Valeur de statut ou de mode invalide.",
            status_code=400,
        )

    physical_type_enum = _resolve_physical_type("pole", None)

    pole = Pole(
        identifier=identifier,
        name=name,
        short_name=_maybe(data.get("short_name")),
        description=_maybe(data.get("description")),
        status=status_enum,
        mode=mode_enum,
        physical_type=physical_type_enum,
        entite_geo_id=geo.id,
    )
    session.add(pole)
    session.commit()

    flash(request, f'Pôle "{pole.name}" créé.', "success")
    return RedirectResponse(cancel_url, status_code=303)


@router.get("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/edit")
async def edit_pole_form(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)

    fields = _pole_form_fields(pole)
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/edit"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"
    return _render_form(
        request,
        f"Modifier le pôle « {pole.name} »",
        fields,
        action_url,
        cancel_url,
    )


@router.post("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/edit")
async def update_pole(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)

    form = await request.form()
    data = {key: form.get(key) for key in form.keys()}
    fields = _with_form_values(_pole_form_fields(pole), data)
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/edit"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"

    identifier = _maybe(data.get("identifier"))
    name = _maybe(data.get("name"))
    if not identifier or not name:
        return _render_form(
            request,
            f"Modifier le pôle « {pole.name} »",
            fields,
            action_url,
            cancel_url,
            error="L'identifiant global et le nom sont obligatoires.",
            status_code=400,
        )

    if identifier != pole.identifier:
        duplicate = session.exec(
            select(Pole)
            .where(Pole.identifier == identifier)
            .where(Pole.id != pole.id)
        ).first()
        if duplicate:
            return _render_form(
                request,
                f"Modifier le pôle « {pole.name} »",
                fields,
                action_url,
                cancel_url,
                error="Un autre pôle utilise déjà cet identifiant.",
                status_code=400,
            )

    try:
        status_enum = LocationStatus(data.get("status") or LocationStatus.ACTIVE.value)
        mode_enum = LocationMode(data.get("mode") or LocationMode.INSTANCE.value)
    except ValueError:
        return _render_form(
            request,
            f"Modifier le pôle « {pole.name} »",
            fields,
            action_url,
            cancel_url,
            error="Valeur de statut ou de mode invalide.",
            status_code=400,
        )

    physical_type_enum = _resolve_physical_type("pole", getattr(pole, "physical_type", None))

    pole.identifier = identifier
    pole.name = name
    pole.short_name = _maybe(data.get("short_name"))
    pole.description = _maybe(data.get("description"))
    pole.status = status_enum
    pole.mode = mode_enum
    pole.physical_type = physical_type_enum

    session.add(pole)
    session.commit()

    flash(request, f'Pôle "{pole.name}" mis à jour.', "success")
    return RedirectResponse(cancel_url, status_code=303)


@router.get("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/new")
async def new_service_form(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)

    fields = _service_form_fields()
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/new"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"
    return _render_form(
        request,
        f"Nouveau service pour {pole.name}",
        fields,
        action_url,
        cancel_url,
    )


@router.post("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/new")
async def create_service(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)

    form = await request.form()
    data = {key: form.get(key) for key in form.keys()}
    fields = _with_form_values(_service_form_fields(), data)
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/new"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"

    identifier = _maybe(data.get("identifier"))
    name = _maybe(data.get("name"))
    if not identifier or not name:
        return _render_form(
            request,
            f"Nouveau service pour {pole.name}",
            fields,
            action_url,
            cancel_url,
            error="L'identifiant global et le nom du service sont obligatoires.",
            status_code=400,
        )

    duplicate = session.exec(
        select(Service).where(Service.identifier == identifier)
    ).first()
    if duplicate:
        return _render_form(
            request,
            f"Nouveau service pour {pole.name}",
            fields,
            action_url,
            cancel_url,
            error="Un service avec cet identifiant existe déjà.",
            status_code=400,
        )

    try:
        status_enum = LocationStatus(data.get("status") or LocationStatus.ACTIVE.value)
        mode_enum = LocationMode(data.get("mode") or LocationMode.INSTANCE.value)
        service_type_enum = LocationServiceType(
            data.get("service_type") or LocationServiceType.MCO.value
        )
    except ValueError:
        return _render_form(
            request,
            f"Nouveau service pour {pole.name}",
            fields,
            action_url,
            cancel_url,
            error="Valeur de statut, mode ou type de service invalide.",
            status_code=400,
        )

    physical_type_enum = _resolve_physical_type("service", None)

    service = Service(
        identifier=identifier,
        name=name,
        short_name=_maybe(data.get("short_name")),
        description=_maybe(data.get("description")),
        status=status_enum,
        mode=mode_enum,
        physical_type=physical_type_enum,
        service_type=service_type_enum,
        typology=_maybe(data.get("typology")),
        pole_id=pole.id,
    )
    session.add(service)
    session.commit()

    flash(request, f'Service "{service.name}" créé.', "success")
    return RedirectResponse(cancel_url, status_code=303)


@router.get("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/edit")
async def edit_service_form(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)

    fields = _service_form_fields(service)
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/{service.id}/edit"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"
    return _render_form(
        request,
        f"Modifier le service « {service.name} »",
        fields,
        action_url,
        cancel_url,
    )


@router.post("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/edit")
async def update_service(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)

    form = await request.form()
    data = {key: form.get(key) for key in form.keys()}
    fields = _with_form_values(_service_form_fields(service), data)
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/{service.id}/edit"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"

    identifier = _maybe(data.get("identifier"))
    name = _maybe(data.get("name"))
    if not identifier or not name:
        return _render_form(
            request,
            f"Modifier le service « {service.name} »",
            fields,
            action_url,
            cancel_url,
            error="L'identifiant global et le nom du service sont obligatoires.",
            status_code=400,
        )

    if identifier != service.identifier:
        duplicate = session.exec(
            select(Service)
            .where(Service.identifier == identifier)
            .where(Service.id != service.id)
        ).first()
        if duplicate:
            return _render_form(
                request,
                f"Modifier le service « {service.name} »",
                fields,
                action_url,
                cancel_url,
                error="Un autre service utilise déjà cet identifiant.",
                status_code=400,
            )

    try:
        status_enum = LocationStatus(data.get("status") or LocationStatus.ACTIVE.value)
        mode_enum = LocationMode(data.get("mode") or LocationMode.INSTANCE.value)
        service_type_enum = LocationServiceType(
            data.get("service_type") or LocationServiceType.MCO.value
        )
    except ValueError:
        return _render_form(
            request,
            f"Modifier le service « {service.name} »",
            fields,
            action_url,
            cancel_url,
            error="Valeur de statut, mode ou type de service invalide.",
            status_code=400,
        )

    physical_type_enum = _resolve_physical_type("service", getattr(service, "physical_type", None))

    service.identifier = identifier
    service.name = name
    service.short_name = _maybe(data.get("short_name"))
    service.description = _maybe(data.get("description"))
    service.status = status_enum
    service.mode = mode_enum
    service.physical_type = physical_type_enum
    service.service_type = service_type_enum
    service.typology = _maybe(data.get("typology"))

    session.add(service)
    session.commit()

    flash(request, f'Service "{service.name}" mis à jour.', "success")
    return RedirectResponse(cancel_url, status_code=303)


@router.get(
    "/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/ufs/{uf_id}"
)
async def view_unite_fonctionnelle(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    uf_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)
    uf = _get_uf_or_404(session, service, uf_id)
    request.session["ght_context_id"] = context_id

    uhs = session.exec(
        select(UniteHebergement).where(UniteHebergement.unite_fonctionnelle_id == uf.id)
    ).all()

    uh_nodes = []
    chambres_total = 0
    lits_total = 0
    lit_operational: Dict[str, int] = {}

    for uh in uhs:
        chambres = session.exec(
            select(Chambre).where(Chambre.unite_hebergement_id == uh.id)
        ).all()
        chambres_total += len(chambres)
        chambre_nodes = []

        for chambre in chambres:
            lits = session.exec(
                select(Lit).where(Lit.chambre_id == chambre.id)
            ).all()
            lits_total += len(lits)
            for lit in lits:
                op = (lit.operational_status or "inconnu").upper()
                lit_operational[op] = lit_operational.get(op, 0) + 1
            chambre_nodes.append({"entity": chambre, "lits": lits})

        uh_nodes.append({"entity": uh, "chambres": chambre_nodes})

    counts = {
        "uhs": len(uhs),
        "chambres": chambres_total,
        "lits": lits_total,
    }

    top_operational = None
    if lit_operational:
        top_operational = max(lit_operational.items(), key=lambda item: item[1])

    return templates.TemplateResponse(
        "uf_detail.html",
        {
            "request": request,
            "context": context,
            "entite": entite,
            "geo": geo,
            "pole": pole,
            "service": service,
            "uf": uf,
            "structure": uh_nodes,
            "counts": counts,
            "lit_operational": lit_operational,
            "top_operational": top_operational,
        },
    )


@router.get("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/ufs/new")
async def new_uf_form(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)

    fields = _uf_form_fields()
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/{service.id}/ufs/new"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"
    return _render_form(
        request,
        f"Nouvelle UF pour {service.name}",
        fields,
        action_url,
        cancel_url,
    )


@router.post("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/ufs/new")
async def create_uf(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)

    form = await request.form()
    data = {key: form.get(key) for key in form.keys()}
    fields = _with_form_values(_uf_form_fields(), data)
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/{service.id}/ufs/new"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"

    identifier = _maybe(data.get("identifier"))
    name = _maybe(data.get("name"))
    if not identifier or not name:
        return _render_form(
            request,
            f"Nouvelle UF pour {service.name}",
            fields,
            action_url,
            cancel_url,
            error="L'identifiant global et le nom de l'UF sont obligatoires.",
            status_code=400,
        )

    duplicate = session.exec(
        select(UniteFonctionnelle).where(UniteFonctionnelle.identifier == identifier)
    ).first()
    if duplicate:
        return _render_form(
            request,
            f"Nouvelle UF pour {service.name}",
            fields,
            action_url,
            cancel_url,
            error="Une unité fonctionnelle avec cet identifiant existe déjà.",
            status_code=400,
        )

    try:
        status_enum = LocationStatus(data.get("status") or LocationStatus.ACTIVE.value)
        mode_enum = LocationMode(data.get("mode") or LocationMode.INSTANCE.value)
    except ValueError:
        return _render_form(
            request,
            f"Nouvelle UF pour {service.name}",
            fields,
            action_url,
            cancel_url,
            error="Valeur de statut ou de mode invalide.",
            status_code=400,
        )

    physical_type_enum = _resolve_physical_type("uf", None)

    uf = UniteFonctionnelle(
        identifier=identifier,
        name=name,
        short_name=_maybe(data.get("short_name")),
        description=_maybe(data.get("description")),
        status=status_enum,
        mode=mode_enum,
        physical_type=physical_type_enum,
        um_code=_maybe(data.get("um_code")),
        uf_type=_maybe(data.get("uf_type")),
        service_id=service.id,
    )
    session.add(uf)
    session.commit()

    flash(request, f'Unité fonctionnelle "{uf.name}" créée.', "success")
    return RedirectResponse(cancel_url, status_code=303)


@router.get("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/ufs/{uf_id}/edit")
async def edit_uf_form(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    uf_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)
    uf = _get_uf_or_404(session, service, uf_id)

    fields = _uf_form_fields(uf)
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/{service.id}/ufs/{uf.id}/edit"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"
    return _render_form(
        request,
        f"Modifier l'UF « {uf.name} »",
        fields,
        action_url,
        cancel_url,
    )


@router.post("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/ufs/{uf_id}/edit")
async def update_uf(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    uf_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)
    uf = _get_uf_or_404(session, service, uf_id)

    form = await request.form()
    data = {key: form.get(key) for key in form.keys()}
    fields = _with_form_values(_uf_form_fields(uf), data)
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/{service.id}/ufs/{uf.id}/edit"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"

    identifier = _maybe(data.get("identifier"))
    name = _maybe(data.get("name"))
    if not identifier or not name:
        return _render_form(
            request,
            f"Modifier l'UF « {uf.name} »",
            fields,
            action_url,
            cancel_url,
            error="L'identifiant global et le nom de l'UF sont obligatoires.",
            status_code=400,
        )

    if identifier != uf.identifier:
        duplicate = session.exec(
            select(UniteFonctionnelle)
            .where(UniteFonctionnelle.identifier == identifier)
            .where(UniteFonctionnelle.id != uf.id)
        ).first()
        if duplicate:
            return _render_form(
                request,
                f"Modifier l'UF « {uf.name} »",
                fields,
                action_url,
                cancel_url,
                error="Une autre UF utilise déjà cet identifiant.",
                status_code=400,
            )

    try:
        status_enum = LocationStatus(data.get("status") or LocationStatus.ACTIVE.value)
        mode_enum = LocationMode(data.get("mode") or LocationMode.INSTANCE.value)
    except ValueError:
        return _render_form(
            request,
            f"Modifier l'UF « {uf.name} »",
            fields,
            action_url,
            cancel_url,
            error="Valeur de statut ou de mode invalide.",
            status_code=400,
        )

    physical_type_enum = _resolve_physical_type("uf", getattr(uf, "physical_type", None))

    uf.identifier = identifier
    uf.name = name
    uf.short_name = _maybe(data.get("short_name"))
    uf.description = _maybe(data.get("description"))
    uf.status = status_enum
    uf.mode = mode_enum
    uf.physical_type = physical_type_enum
    uf.um_code = _maybe(data.get("um_code"))
    uf.uf_type = _maybe(data.get("uf_type"))

    session.add(uf)
    session.commit()

    flash(request, f'Unité fonctionnelle "{uf.name}" mise à jour.', "success")
    return RedirectResponse(cancel_url, status_code=303)


@router.get("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/ufs/{uf_id}/uh/new")
async def new_uh_form(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    uf_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)
    uf = _get_uf_or_404(session, service, uf_id)

    fields = _uh_form_fields()
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/{service.id}/ufs/{uf.id}/uh/new"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"
    return _render_form(
        request,
        f"Nouvelle unité d'hébergement pour {uf.name}",
        fields,
        action_url,
        cancel_url,
    )


@router.post("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/ufs/{uf_id}/uh/new")
async def create_uh(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    uf_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)
    uf = _get_uf_or_404(session, service, uf_id)

    form = await request.form()
    data = {key: form.get(key) for key in form.keys()}
    fields = _with_form_values(_uh_form_fields(), data)
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/{service.id}/ufs/{uf.id}/uh/new"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"

    identifier = _maybe(data.get("identifier"))
    name = _maybe(data.get("name"))
    if not identifier or not name:
        return _render_form(
            request,
            f"Nouvelle unité d'hébergement pour {uf.name}",
            fields,
            action_url,
            cancel_url,
            error="L'identifiant global et le nom de l'unité d'hébergement sont obligatoires.",
            status_code=400,
        )

    duplicate = session.exec(
        select(UniteHebergement).where(UniteHebergement.identifier == identifier)
    ).first()
    if duplicate:
        return _render_form(
            request,
            f"Nouvelle unité d'hébergement pour {uf.name}",
            fields,
            action_url,
            cancel_url,
            error="Une unité d'hébergement avec cet identifiant existe déjà.",
            status_code=400,
        )

    try:
        status_enum = LocationStatus(data.get("status") or LocationStatus.ACTIVE.value)
        mode_enum = LocationMode(data.get("mode") or LocationMode.INSTANCE.value)
    except ValueError:
        return _render_form(
            request,
            f"Nouvelle unité d'hébergement pour {uf.name}",
            fields,
            action_url,
            cancel_url,
            error="Valeur de statut ou de mode invalide.",
            status_code=400,
        )

    physical_type_enum = _resolve_physical_type("uh", None)

    uh = UniteHebergement(
        identifier=identifier,
        name=name,
        short_name=_maybe(data.get("short_name")),
        description=_maybe(data.get("description")),
        status=status_enum,
        mode=mode_enum,
        physical_type=physical_type_enum,
        etage=_maybe(data.get("etage")),
        aile=_maybe(data.get("aile")),
        unite_fonctionnelle_id=uf.id,
    )
    session.add(uh)
    session.commit()

    flash(request, f'Unité d\'hébergement "{uh.name}" créée.', "success")
    return RedirectResponse(cancel_url, status_code=303)


@router.get("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/ufs/{uf_id}/uh/{uh_id}/edit")
async def edit_uh_form(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    uf_id: int,
    uh_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)
    uf = _get_uf_or_404(session, service, uf_id)
    uh = _get_uh_or_404(session, uf, uh_id)

    fields = _uh_form_fields(uh)
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/{service.id}/ufs/{uf.id}/uh/{uh.id}/edit"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"
    return _render_form(
        request,
        f"Modifier l'unité d'hébergement « {uh.name} »",
        fields,
        action_url,
        cancel_url,
    )


@router.post("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/ufs/{uf_id}/uh/{uh_id}/edit")
async def update_uh(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    uf_id: int,
    uh_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)
    uf = _get_uf_or_404(session, service, uf_id)
    uh = _get_uh_or_404(session, uf, uh_id)

    form = await request.form()
    data = {key: form.get(key) for key in form.keys()}
    fields = _with_form_values(_uh_form_fields(uh), data)
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/{service.id}/ufs/{uf.id}/uh/{uh.id}/edit"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"

    identifier = _maybe(data.get("identifier"))
    name = _maybe(data.get("name"))
    if not identifier or not name:
        return _render_form(
            request,
            f"Modifier l'unité d'hébergement « {uh.name} »",
            fields,
            action_url,
            cancel_url,
            error="L'identifiant global et le nom de l'unité d'hébergement sont obligatoires.",
            status_code=400,
        )

    if identifier != uh.identifier:
        duplicate = session.exec(
            select(UniteHebergement)
            .where(UniteHebergement.identifier == identifier)
            .where(UniteHebergement.id != uh.id)
        ).first()
        if duplicate:
            return _render_form(
                request,
                f"Modifier l'unité d'hébergement « {uh.name} »",
                fields,
                action_url,
                cancel_url,
                error="Une autre unité d'hébergement utilise déjà cet identifiant.",
                status_code=400,
            )

    try:
        status_enum = LocationStatus(data.get("status") or LocationStatus.ACTIVE.value)
        mode_enum = LocationMode(data.get("mode") or LocationMode.INSTANCE.value)
    except ValueError:
        return _render_form(
            request,
            f"Modifier l'unité d'hébergement « {uh.name} »",
            fields,
            action_url,
            cancel_url,
            error="Valeur de statut ou de mode invalide.",
            status_code=400,
        )

    physical_type_enum = _resolve_physical_type("uh", getattr(uh, "physical_type", None))

    uh.identifier = identifier
    uh.name = name
    uh.short_name = _maybe(data.get("short_name"))
    uh.description = _maybe(data.get("description"))
    uh.status = status_enum
    uh.mode = mode_enum
    uh.physical_type = physical_type_enum
    uh.etage = _maybe(data.get("etage"))
    uh.aile = _maybe(data.get("aile"))

    session.add(uh)
    session.commit()

    flash(request, f'Unité d\'hébergement "{uh.name}" mise à jour.', "success")
    return RedirectResponse(cancel_url, status_code=303)


@router.get("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/ufs/{uf_id}/uh/{uh_id}/chambres/new")
async def new_chambre_form(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    uf_id: int,
    uh_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)
    uf = _get_uf_or_404(session, service, uf_id)
    uh = _get_uh_or_404(session, uf, uh_id)

    fields = _chambre_form_fields()
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/{service.id}/ufs/{uf.id}/uh/{uh.id}/chambres/new"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"
    return _render_form(
        request,
        f"Nouvelle chambre pour {uh.name}",
        fields,
        action_url,
        cancel_url,
    )


@router.post("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/ufs/{uf_id}/uh/{uh_id}/chambres/new")
async def create_chambre(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    uf_id: int,
    uh_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)
    uf = _get_uf_or_404(session, service, uf_id)
    uh = _get_uh_or_404(session, uf, uh_id)

    form = await request.form()
    data = {key: form.get(key) for key in form.keys()}
    fields = _with_form_values(_chambre_form_fields(), data)
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/{service.id}/ufs/{uf.id}/uh/{uh.id}/chambres/new"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"

    identifier = _maybe(data.get("identifier"))
    name = _maybe(data.get("name"))
    if not identifier or not name:
        return _render_form(
            request,
            f"Nouvelle chambre pour {uh.name}",
            fields,
            action_url,
            cancel_url,
            error="L'identifiant global et le nom de la chambre sont obligatoires.",
            status_code=400,
        )

    duplicate = session.exec(
        select(Chambre).where(Chambre.identifier == identifier)
    ).first()
    if duplicate:
        return _render_form(
            request,
            f"Nouvelle chambre pour {uh.name}",
            fields,
            action_url,
            cancel_url,
            error="Une chambre avec cet identifiant existe déjà.",
            status_code=400,
        )

    try:
        status_enum = LocationStatus(data.get("status") or LocationStatus.ACTIVE.value)
        mode_enum = LocationMode(data.get("mode") or LocationMode.INSTANCE.value)
    except ValueError:
        return _render_form(
            request,
            f"Nouvelle chambre pour {uh.name}",
            fields,
            action_url,
            cancel_url,
            error="Valeur de statut ou de mode invalide.",
            status_code=400,
        )

    physical_type_enum = _resolve_physical_type("chambre", None)

    chambre = Chambre(
        identifier=identifier,
        name=name,
        short_name=_maybe(data.get("short_name")),
        description=_maybe(data.get("description")),
        status=status_enum,
        mode=mode_enum,
        physical_type=physical_type_enum,
        type_chambre=_maybe(data.get("type_chambre")),
        gender_usage=_maybe(data.get("gender_usage")),
        unite_hebergement_id=uh.id,
    )
    session.add(chambre)
    session.commit()

    flash(request, f'Chambre "{chambre.name}" créée.', "success")
    return RedirectResponse(cancel_url, status_code=303)


@router.get("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/ufs/{uf_id}/uh/{uh_id}/chambres/{chambre_id}/edit")
async def edit_chambre_form(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    uf_id: int,
    uh_id: int,
    chambre_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)
    uf = _get_uf_or_404(session, service, uf_id)
    uh = _get_uh_or_404(session, uf, uh_id)
    chambre = _get_chambre_or_404(session, uh, chambre_id)

    fields = _chambre_form_fields(chambre)
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/{service.id}/ufs/{uf.id}/uh/{uh.id}/chambres/{chambre.id}/edit"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"
    return _render_form(
        request,
        f"Modifier la chambre « {chambre.name} »",
        fields,
        action_url,
        cancel_url,
    )


@router.post("/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/ufs/{uf_id}/uh/{uh_id}/chambres/{chambre_id}/edit")
async def update_chambre(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    uf_id: int,
    uh_id: int,
    chambre_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)
    uf = _get_uf_or_404(session, service, uf_id)
    uh = _get_uh_or_404(session, uf, uh_id)
    chambre = _get_chambre_or_404(session, uh, chambre_id)

    form = await request.form()
    data = {key: form.get(key) for key in form.keys()}
    fields = _with_form_values(_chambre_form_fields(chambre), data)
    action_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/{service.id}/ufs/{uf.id}/uh/{uh.id}/chambres/{chambre.id}/edit"
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"

    identifier = _maybe(data.get("identifier"))
    name = _maybe(data.get("name"))
    if not identifier or not name:
        return _render_form(
            request,
            f"Modifier la chambre « {chambre.name} »",
            fields,
            action_url,
            cancel_url,
            error="L'identifiant global et le nom de la chambre sont obligatoires.",
            status_code=400,
        )

    if identifier != chambre.identifier:
        duplicate = session.exec(
            select(Chambre)
            .where(Chambre.identifier == identifier)
            .where(Chambre.id != chambre.id)
        ).first()
        if duplicate:
            return _render_form(
                request,
                f"Modifier la chambre « {chambre.name} »",
                fields,
                action_url,
                cancel_url,
                error="Une autre chambre utilise déjà cet identifiant.",
                status_code=400,
            )

    try:
        status_enum = LocationStatus(data.get("status") or LocationStatus.ACTIVE.value)
        mode_enum = LocationMode(data.get("mode") or LocationMode.INSTANCE.value)
    except ValueError:
        return _render_form(
            request,
            f"Modifier la chambre « {chambre.name} »",
            fields,
            action_url,
            cancel_url,
            error="Valeur de statut ou de mode invalide.",
            status_code=400,
        )

    physical_type_enum = _resolve_physical_type("chambre", getattr(chambre, "physical_type", None))

    chambre.identifier = identifier
    chambre.name = name
    chambre.short_name = _maybe(data.get("short_name"))
    chambre.description = _maybe(data.get("description"))
    chambre.status = status_enum
    chambre.mode = mode_enum
    chambre.physical_type = physical_type_enum
    chambre.type_chambre = _maybe(data.get("type_chambre"))
    chambre.gender_usage = _maybe(data.get("gender_usage"))

    session.add(chambre)
    session.commit()

    flash(request, f'Chambre "{chambre.name}" mise à jour.', "success")
    return RedirectResponse(cancel_url, status_code=303)


@router.get(
    "/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/ufs/{uf_id}/uh/{uh_id}/chambres/{chambre_id}/lits/new"
)
async def new_lit_form(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    uf_id: int,
    uh_id: int,
    chambre_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)
    uf = _get_uf_or_404(session, service, uf_id)
    uh = _get_uh_or_404(session, uf, uh_id)
    chambre = _get_chambre_or_404(session, uh, chambre_id)

    fields = _lit_form_fields()
    action_url = (
        f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/"
        f"{service.id}/ufs/{uf.id}/uh/{uh.id}/chambres/{chambre.id}/lits/new"
    )
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"
    return _render_form(
        request,
        f"Nouveau lit pour {chambre.name}",
        fields,
        action_url,
        cancel_url,
    )


@router.post(
    "/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/ufs/{uf_id}/uh/{uh_id}/chambres/{chambre_id}/lits/new"
)
async def create_lit(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    uf_id: int,
    uh_id: int,
    chambre_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)
    uf = _get_uf_or_404(session, service, uf_id)
    uh = _get_uh_or_404(session, uf, uh_id)
    chambre = _get_chambre_or_404(session, uh, chambre_id)

    form = await request.form()
    data = {key: form.get(key) for key in form.keys()}
    fields = _with_form_values(_lit_form_fields(), data)
    action_url = (
        f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/"
        f"{service.id}/ufs/{uf.id}/uh/{uh.id}/chambres/{chambre.id}/lits/new"
    )
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"

    identifier = _maybe(data.get("identifier"))
    name = _maybe(data.get("name"))
    if not identifier or not name:
        return _render_form(
            request,
            f"Nouveau lit pour {chambre.name}",
            fields,
            action_url,
            cancel_url,
            error="L'identifiant global et le nom du lit sont obligatoires.",
            status_code=400,
        )

    duplicate = session.exec(select(Lit).where(Lit.identifier == identifier)).first()
    if duplicate:
        return _render_form(
            request,
            f"Nouveau lit pour {chambre.name}",
            fields,
            action_url,
            cancel_url,
            error="Un lit avec cet identifiant existe déjà.",
            status_code=400,
        )

    try:
        status_enum = LocationStatus(data.get("status") or LocationStatus.ACTIVE.value)
        mode_enum = LocationMode(data.get("mode") or LocationMode.INSTANCE.value)
    except ValueError:
        return _render_form(
            request,
            f"Nouveau lit pour {chambre.name}",
            fields,
            action_url,
            cancel_url,
            error="Valeur de statut ou de mode invalide.",
            status_code=400,
        )

    physical_type_enum = _resolve_physical_type("lit", None)

    lit = Lit(
        identifier=identifier,
        name=name,
        short_name=_maybe(data.get("short_name")),
        description=_maybe(data.get("description")),
        status=status_enum,
        mode=mode_enum,
        physical_type=physical_type_enum,
        operational_status=_maybe(data.get("operational_status")),
        chambre_id=chambre.id,
    )
    session.add(lit)
    session.commit()

    flash(request, f'Lit "{lit.name}" créé.', "success")
    return RedirectResponse(cancel_url, status_code=303)


@router.get(
    "/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/ufs/{uf_id}/uh/{uh_id}/chambres/{chambre_id}/lits/{lit_id}/edit"
)
async def edit_lit_form(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    uf_id: int,
    uh_id: int,
    chambre_id: int,
    lit_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)
    uf = _get_uf_or_404(session, service, uf_id)
    uh = _get_uh_or_404(session, uf, uh_id)
    chambre = _get_chambre_or_404(session, uh, chambre_id)
    lit = _get_lit_or_404(session, chambre, lit_id)

    fields = _lit_form_fields(lit)
    action_url = (
        f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/"
        f"{service.id}/ufs/{uf.id}/uh/{uh.id}/chambres/{chambre.id}/lits/{lit.id}/edit"
    )
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"
    return _render_form(
        request,
        f"Modifier le lit « {lit.name} »",
        fields,
        action_url,
        cancel_url,
    )


@router.post(
    "/{context_id}/ej/{ej_id}/eg/{eg_id}/poles/{pole_id}/services/{service_id}/ufs/{uf_id}/uh/{uh_id}/chambres/{chambre_id}/lits/{lit_id}/edit"
)
async def update_lit(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    pole_id: int,
    service_id: int,
    uf_id: int,
    uh_id: int,
    chambre_id: int,
    lit_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    pole = _get_pole_or_404(session, geo, pole_id)
    service = _get_service_or_404(session, pole, service_id)
    uf = _get_uf_or_404(session, service, uf_id)
    uh = _get_uh_or_404(session, uf, uh_id)
    chambre = _get_chambre_or_404(session, uh, chambre_id)
    lit = _get_lit_or_404(session, chambre, lit_id)

    form = await request.form()
    data = {key: form.get(key) for key in form.keys()}
    fields = _with_form_values(_lit_form_fields(lit), data)
    action_url = (
        f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}/poles/{pole.id}/services/"
        f"{service.id}/ufs/{uf.id}/uh/{uh.id}/chambres/{chambre.id}/lits/{lit.id}/edit"
    )
    cancel_url = f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}"

    identifier = _maybe(data.get("identifier"))
    name = _maybe(data.get("name"))
    if not identifier or not name:
        return _render_form(
            request,
            f"Modifier le lit « {lit.name} »",
            fields,
            action_url,
            cancel_url,
            error="L'identifiant global et le nom du lit sont obligatoires.",
            status_code=400,
        )

    if identifier != lit.identifier:
        duplicate = session.exec(
            select(Lit).where(Lit.identifier == identifier).where(Lit.id != lit.id)
        ).first()
        if duplicate:
            return _render_form(
                request,
                f"Modifier le lit « {lit.name} »",
                fields,
                action_url,
                cancel_url,
                error="Un autre lit utilise déjà cet identifiant.",
                status_code=400,
            )

    try:
        status_enum = LocationStatus(data.get("status") or LocationStatus.ACTIVE.value)
        mode_enum = LocationMode(data.get("mode") or LocationMode.INSTANCE.value)
    except ValueError:
        return _render_form(
            request,
            f"Modifier le lit « {lit.name} »",
            fields,
            action_url,
            cancel_url,
            error="Valeur de statut ou de mode invalide.",
            status_code=400,
        )

    physical_type_enum = _resolve_physical_type("lit", getattr(lit, "physical_type", None))

    lit.identifier = identifier
    lit.name = name
    lit.short_name = _maybe(data.get("short_name"))
    lit.description = _maybe(data.get("description"))
    lit.status = status_enum
    lit.mode = mode_enum
    lit.physical_type = physical_type_enum
    lit.operational_status = _maybe(data.get("operational_status"))

    session.add(lit)
    session.commit()

    flash(request, f'Lit "{lit.name}" mis à jour.', "success")
    return RedirectResponse(cancel_url, status_code=303)


@router.get("/{context_id}/ej/{ej_id}/eg/{eg_id}")
async def view_entite_geographique(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    request.session["ght_context_id"] = context_id

    poles = session.exec(
        select(Pole).where(Pole.entite_geo_id == geo.id)
    ).all()

    services_by_pole = {}
    ufs_by_service = {}
    uhs_by_uf = {}
    chambres_by_uh = {}
    lits_by_chambre = {}
    lit_operational: Dict[str, int] = {}
    active_lits = 0

    for pole in poles:
        services = session.exec(
            select(Service).where(Service.pole_id == pole.id)
        ).all()
        services_by_pole[pole.id] = services

        for service in services:
            ufs = session.exec(
                select(UniteFonctionnelle).where(UniteFonctionnelle.service_id == service.id)
            ).all()
            ufs_by_service[service.id] = ufs

            for uf in ufs:
                uhs = session.exec(
                    select(UniteHebergement).where(UniteHebergement.unite_fonctionnelle_id == uf.id)
                ).all()
                uhs_by_uf[uf.id] = uhs

                for uh in uhs:
                    chambres = session.exec(
                        select(Chambre).where(Chambre.unite_hebergement_id == uh.id)
                    ).all()
                    chambres_by_uh[uh.id] = chambres

                    for chambre in chambres:
                        lits = session.exec(
                            select(Lit).where(Lit.chambre_id == chambre.id)
                        ).all()
                        lits_by_chambre[chambre.id] = lits
                        for lit in lits:
                            status_value = (
                                lit.status.value
                                if isinstance(lit.status, LocationStatus)
                                else (lit.status or "inactif")
                            )
                            if str(status_value).lower() == "active":
                                active_lits += 1
                            op_key = (lit.operational_status or "inconnu").upper()
                            lit_operational[op_key] = lit_operational.get(op_key, 0) + 1

    structure_tree: List[dict] = []
    for pole in poles:
        services = services_by_pole.get(pole.id, [])
        service_nodes = []
        for service in services:
            ufs = ufs_by_service.get(service.id, [])
            uf_nodes = []
            for uf in ufs:
                uhs = uhs_by_uf.get(uf.id, [])
                uh_nodes = []
                for uh in uhs:
                    chambres = chambres_by_uh.get(uh.id, [])
                    chambre_nodes = []
                    for chambre in chambres:
                        chambre_nodes.append(
                            {
                                "entity": chambre,
                                "lits": lits_by_chambre.get(chambre.id, []),
                            }
                        )
                    uh_nodes.append({"entity": uh, "chambres": chambre_nodes})
                uf_nodes.append({"entity": uf, "uhs": uh_nodes})
            service_nodes.append({"entity": service, "ufs": uf_nodes})
        structure_tree.append({"entity": pole, "services": service_nodes})

    counts = {
        "poles": len(poles),
        "services": sum(len(v) for v in services_by_pole.values()),
        "ufs": sum(len(v) for v in ufs_by_service.values()),
        "uhs": sum(len(v) for v in uhs_by_uf.values()),
        "chambres": sum(len(v) for v in chambres_by_uh.values()),
        "lits": sum(len(v) for v in lits_by_chambre.values()),
        "lits_actifs": active_lits,
    }

    return templates.TemplateResponse(
        "eg_detail.html",
        {
            "request": request,
            "context": context,
            "entite": entite,
            "geo": geo,
            "structure_tree": structure_tree,
            "counts": counts,
            "lit_operational": lit_operational,
        },
    )


@router.get("/{context_id}/ej/{ej_id}/eg/{eg_id}/edit")
async def edit_entite_geographique_form(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)

    return templates.TemplateResponse(
        "eg_form.html",
        {
            "request": request,
            "context": context,
            "entite": entite,
            "geo": geo,
        },
    )


@router.post("/{context_id}/ej/{ej_id}/eg/{eg_id}/edit")
async def update_entite_geographique(
    request: Request,
    context_id: int,
    ej_id: int,
    eg_id: int,
    name: str = Form(...),
    identifier: str = Form(...),
    finess: str = Form(...),
    short_name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    status: str = Form(LocationStatus.ACTIVE.value),
    mode: str = Form(LocationMode.INSTANCE.value),
    physical_type: str = Form(LocationPhysicalType.SI.value),
    is_active: str = Form("true"),
    siren: Optional[str] = Form(None),
    siret: Optional[str] = Form(None),
    address_line1: Optional[str] = Form(None),
    address_line2: Optional[str] = Form(None),
    address_line3: Optional[str] = Form(None),
    address_postalcode: Optional[str] = Form(None),
    address_city: Optional[str] = Form(None),
    latitude: Optional[str] = Form(None),
    longitude: Optional[str] = Form(None),
    session: Session = Depends(get_session),
):
    context = _get_context_or_404(session, context_id)
    entite = _get_ej_or_404(session, context, ej_id)
    geo = _get_entite_geo_or_404(session, entite, eg_id)
    wants_json = "application/json" in (request.headers.get("accept") or "")

    form_payload = {
        "name": name,
        "identifier": identifier,
        "finess": finess,
        "short_name": short_name,
        "description": description,
        "status": status,
        "mode": mode,
        "physical_type": physical_type,
        "is_active": is_active,
        "siren": siren,
        "siret": siret,
        "address_line1": address_line1,
        "address_line2": address_line2,
        "address_line3": address_line3,
        "address_postalcode": address_postalcode,
        "address_city": address_city,
        "latitude": latitude,
        "longitude": longitude,
    }

    if identifier != geo.identifier:
        duplicate_identifier = session.exec(
            select(EntiteGeographique).where(EntiteGeographique.identifier == identifier)
        ).first()
        if duplicate_identifier:
            if wants_json:
                return {
                    "ok": False,
                    "message": "Un identifiant global identique existe déjà.",
                    "errors": {"identifier": "Identifiant déjà utilisé"},
                }
            flash(request, "Un identifiant global identique existe déjà.", "error")
            return templates.TemplateResponse(
                "eg_form.html",
                {
                    "request": request,
                    "context": context,
                    "entite": entite,
                    "geo": geo,
                    "form_data": form_payload,
                },
                status_code=400,
            )

    if finess != geo.finess:
        duplicate_finess = session.exec(
            select(EntiteGeographique)
            .where(EntiteGeographique.finess == finess)
            .where(EntiteGeographique.id != geo.id)
            .where(EntiteGeographique.entite_juridique_id == entite.id)
        ).first()
        if duplicate_finess:
            if wants_json:
                return {
                    "ok": False,
                    "message": "Une entité géographique possède déjà ce FINESS.",
                    "errors": {"finess": "FINESS déjà utilisé"},
                }
            flash(
                request,
                "Une entité géographique de ce GHT possède déjà ce FINESS.",
                "error",
            )
            return templates.TemplateResponse(
                "eg_form.html",
                {
                    "request": request,
                    "context": context,
                    "entite": entite,
                    "geo": geo,
                    "form_data": form_payload,
                },
                status_code=400,
            )

    try:
        latitude_value = float(latitude) if latitude else None
    except ValueError:
        if wants_json:
            return {
                "ok": False,
                "message": "Latitude invalide, merci de saisir un nombre.",
                "errors": {"latitude": "Latitude invalide"},
            }
        flash(request, "Latitude invalide, merci de saisir un nombre.", "error")
        return templates.TemplateResponse(
            "eg_form.html",
            {
                "request": request,
                "context": context,
                "entite": entite,
                "geo": geo,
                "form_data": form_payload,
            },
            status_code=400,
        )

    try:
        longitude_value = float(longitude) if longitude else None
    except ValueError:
        if wants_json:
            return {
                "ok": False,
                "message": "Longitude invalide, merci de saisir un nombre.",
                "errors": {"longitude": "Longitude invalide"},
            }
        flash(request, "Longitude invalide, merci de saisir un nombre.", "error")
        return templates.TemplateResponse(
            "eg_form.html",
            {
                "request": request,
                "context": context,
                "entite": entite,
                "geo": geo,
                "form_data": form_payload,
            },
            status_code=400,
        )

    try:
        status_value = LocationStatus(status).value
        mode_value = LocationMode(mode).value
    except ValueError:
        if wants_json:
            return {
                "ok": False,
                "message": "Statut ou mode invalide.",
                "errors": {"status": "Valeur invalide"},
            }
        flash(
            request,
            "Statut ou mode invalide.",
            "error",
        )
        return templates.TemplateResponse(
            "eg_form.html",
            {
                "request": request,
                "context": context,
                "entite": entite,
                "geo": geo,
                "form_data": form_payload,
            },
            status_code=400,
        )

    physical_value = _resolve_physical_type(
        "entite_geographique", physical_type or getattr(geo, "physical_type", None)
    ).value

    geo.name = name
    geo.identifier = identifier
    geo.short_name = short_name
    geo.description = description
    geo.status = status_value
    geo.mode = mode_value
    geo.physical_type = physical_value
    geo.finess = finess
    geo.siren = siren
    geo.siret = siret
    geo.address_line1 = address_line1
    geo.address_line2 = address_line2
    geo.address_line3 = address_line3
    geo.address_postalcode = address_postalcode
    geo.address_city = address_city
    geo.latitude = latitude_value
    geo.longitude = longitude_value
    geo.is_active = str(is_active).lower() in ("1", "true", "yes", "on")
    geo.updated_at = datetime.utcnow()

    session.add(geo)
    session.commit()

    flash(request, f'Entité géographique "{geo.name}" mise à jour.', "success")
    if wants_json:
        return {
            "ok": True,
            "id": geo.id,
            "redirect": f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}",
        }
    return RedirectResponse(
        f"/admin/ght/{context.id}/ej/{entite.id}/eg/{geo.id}",
        status_code=303,
    )
