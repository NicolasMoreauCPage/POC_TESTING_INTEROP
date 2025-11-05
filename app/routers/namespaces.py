from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from starlette.responses import RedirectResponse

from app.db import get_session
from app.models_structure_fhir import GHTContext, IdentifierNamespace, EntiteJuridique
from app.models_identifiers import Identifier
from app.middleware.ght_context import get_active_ght_context

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/ght", tags=["ght"])


def _get_ej_or_404(session: Session, context: GHTContext, ej_id: int) -> EntiteJuridique:
    """Helper pour récupérer une EJ ou lever 404"""
    ej = session.exec(
        select(EntiteJuridique)
        .where(EntiteJuridique.id == ej_id)
        .where(EntiteJuridique.ght_context_id == context.id)
    ).first()
    if not ej:
        raise HTTPException(status_code=404, detail="Entité juridique not found")
    return ej

@router.get("/{ght_id}/namespaces/new")
async def new_namespace(
    request: Request,
    ght_id: int,
    session: Session = Depends(get_session),
    context: GHTContext = Depends(get_active_ght_context)
):
    """Formulaire création namespace"""
    if not context or context.id != ght_id:
        raise HTTPException(status_code=404, detail="GHT context not found")

    return templates.TemplateResponse(
        "namespace_form.html",
        {
            "request": request,
            "context": context,
            "namespace": None,
        },
    )

@router.post("/{ght_id}/namespaces/new")
async def create_namespace(
    request: Request,
    ght_id: int,
    session: Session = Depends(get_session),
    context: GHTContext = Depends(get_active_ght_context)
):
    """Création namespace"""
    if not context or context.id != ght_id:
        raise HTTPException(status_code=404, detail="GHT context not found")

    form = await request.form()
    
    # Validation basique
    if not form.get("name") or not form.get("system"):
        raise HTTPException(status_code=400, detail="Name and system are required")
    
    # Check system uniqueness
    exists = session.exec(
        select(IdentifierNamespace).where(IdentifierNamespace.system == form["system"])
    ).first()
    if exists:
        raise HTTPException(
            status_code=400, 
            detail=f"System URI {form['system']} already exists"
        )

    namespace = IdentifierNamespace(
        name=form["name"],
        system=form["system"],
        oid=form.get("oid"),
        type=form.get("type", "PI"),
        description=form.get("description"),
        is_active=form.get("is_active", "true") == "true",
        ght_context_id=context.id
    )
    session.add(namespace)
    session.commit()
    
    return RedirectResponse(
        f"/admin/ght/{ght_id}/namespaces/{namespace.id}",
        status_code=302
    )

@router.get("/{ght_id}/namespaces/{namespace_id}")
async def view_namespace(
    request: Request,
    ght_id: int,  
    namespace_id: int,
    session: Session = Depends(get_session),
    context: GHTContext = Depends(get_active_ght_context)
):
    """Vue détaillée namespace"""
    if not context or context.id != ght_id:
        raise HTTPException(status_code=404, detail="GHT context not found")
        
    namespace = session.exec(
        select(IdentifierNamespace)
        .where(IdentifierNamespace.id == namespace_id)
        .where(IdentifierNamespace.ght_context_id == context.id)
    ).first()
    if not namespace:
        raise HTTPException(status_code=404, detail="Namespace not found")
        
    # Récupérer les identifiants utilisant ce namespace
    identifiers = session.exec(
        select(Identifier).where(Identifier.system == namespace.system)
    ).all()
    
    return templates.TemplateResponse(
        "namespace_detail.html",
        {
            "request": request,
            "context": context,
            "namespace": namespace,
            "identifiers": identifiers,
        },
    )

@router.get("/{ght_id}/namespaces/{namespace_id}/edit")
async def edit_namespace(
    request: Request,
    ght_id: int,
    namespace_id: int, 
    session: Session = Depends(get_session),
    context: GHTContext = Depends(get_active_ght_context)
):
    """Formulaire édition namespace"""
    if not context or context.id != ght_id:
        raise HTTPException(status_code=404, detail="GHT context not found")

    namespace = session.exec(
        select(IdentifierNamespace)
        .where(IdentifierNamespace.id == namespace_id)
        .where(IdentifierNamespace.ght_context_id == context.id)
    ).first()
    if not namespace:
        raise HTTPException(status_code=404, detail="Namespace not found")

    return templates.TemplateResponse(
        "namespace_form.html",
        {
            "request": request,
            "context": context,
            "namespace": namespace,
        },
    )

@router.post("/{ght_id}/namespaces/{namespace_id}/edit")
async def update_namespace(
    request: Request,
    ght_id: int,
    namespace_id: int,
    session: Session = Depends(get_session),
    context: GHTContext = Depends(get_active_ght_context)
):
    """Mise à jour namespace"""
    if not context or context.id != ght_id:
        raise HTTPException(status_code=404, detail="GHT context not found")

    namespace = session.exec(
        select(IdentifierNamespace)
        .where(IdentifierNamespace.id == namespace_id)
        .where(IdentifierNamespace.ght_context_id == context.id)
    ).first()
    if not namespace:
        raise HTTPException(status_code=404, detail="Namespace not found")

    form = await request.form()
    
    # Validation basique
    if not form.get("name") or not form.get("system"):
        raise HTTPException(
            status_code=400,
            detail="Name and system are required"
        )

    # Check system uniqueness (sauf pour le même namespace)
    exists = session.exec(
        select(IdentifierNamespace)
        .where(IdentifierNamespace.system == form["system"])
        .where(IdentifierNamespace.id != namespace_id)
    ).first()
    if exists:
        raise HTTPException(
            status_code=400,
            detail=f"System URI {form['system']} already exists"
        )
    
    # Mise à jour
    namespace.name = form["name"]
    namespace.system = form["system"]
    namespace.oid = form.get("oid")
    namespace.type = form.get("type", namespace.type)
    namespace.description = form.get("description")
    namespace.is_active = form.get("is_active", "true") == "true"
    
    session.add(namespace)
    session.commit()
    
    return RedirectResponse(
        f"/admin/ght/{ght_id}/namespaces/{namespace.id}",
        status_code=302
    )


# ============================================================================
# Routes pour les namespaces au niveau EJ (IPP, NDA, etc.)
# ============================================================================

@router.get("/{ght_id}/ej/{ej_id}/namespaces/new")
async def new_ej_namespace(
    request: Request,
    ght_id: int,
    ej_id: int,
    session: Session = Depends(get_session),
    context: GHTContext = Depends(get_active_ght_context)
):
    """Formulaire création namespace pour une EJ"""
    if not context or context.id != ght_id:
        raise HTTPException(status_code=404, detail="GHT context not found")
    
    ej = _get_ej_or_404(session, context, ej_id)

    return templates.TemplateResponse(
        "namespace_form.html",
        {
            "request": request,
            "context": context,
            "entite": ej,
            "namespace": None,
        },
    )


@router.post("/{ght_id}/ej/{ej_id}/namespaces/new")
async def create_ej_namespace(
    request: Request,
    ght_id: int,
    ej_id: int,
    session: Session = Depends(get_session),
    context: GHTContext = Depends(get_active_ght_context)
):
    """Création namespace pour une EJ"""
    if not context or context.id != ght_id:
        raise HTTPException(status_code=404, detail="GHT context not found")
    
    ej = _get_ej_or_404(session, context, ej_id)
    form = await request.form()
    
    # Validation basique
    if not form.get("name") or not form.get("system"):
        raise HTTPException(status_code=400, detail="Name and system are required")
    
    # Check system uniqueness dans le contexte GHT
    exists = session.exec(
        select(IdentifierNamespace)
        .where(IdentifierNamespace.system == form["system"])
        .where(IdentifierNamespace.ght_context_id == context.id)
    ).first()
    if exists:
        raise HTTPException(
            status_code=400, 
            detail=f"System URI {form['system']} already exists in this GHT"
        )

    namespace = IdentifierNamespace(
        name=form["name"],
        system=form["system"],
        oid=form.get("oid"),
        type=form.get("type", "PI"),
        description=form.get("description"),
        is_active=form.get("is_active", "true") == "true",
        ght_context_id=context.id,
        entite_juridique_id=ej.id  # Lié à l'EJ
    )
    session.add(namespace)
    session.commit()
    
    return RedirectResponse(
        f"/admin/ght/{ght_id}/ej/{ej_id}",
        status_code=302
    )


@router.get("/{ght_id}/ej/{ej_id}/namespaces/{namespace_id}/edit")
async def edit_ej_namespace(
    request: Request,
    ght_id: int,
    ej_id: int,
    namespace_id: int, 
    session: Session = Depends(get_session),
    context: GHTContext = Depends(get_active_ght_context)
):
    """Formulaire édition namespace EJ"""
    if not context or context.id != ght_id:
        raise HTTPException(status_code=404, detail="GHT context not found")

    ej = _get_ej_or_404(session, context, ej_id)
    
    namespace = session.exec(
        select(IdentifierNamespace)
        .where(IdentifierNamespace.id == namespace_id)
        .where(IdentifierNamespace.entite_juridique_id == ej_id)
    ).first()
    if not namespace:
        raise HTTPException(status_code=404, detail="Namespace not found")

    return templates.TemplateResponse(
        "namespace_form.html",
        {
            "request": request,
            "context": context,
            "entite": ej,
            "namespace": namespace,
        },
    )


@router.post("/{ght_id}/ej/{ej_id}/namespaces/{namespace_id}/edit")
async def update_ej_namespace(
    request: Request,
    ght_id: int,
    ej_id: int,
    namespace_id: int,
    session: Session = Depends(get_session),
    context: GHTContext = Depends(get_active_ght_context)
):
    """Mise à jour namespace EJ"""
    if not context or context.id != ght_id:
        raise HTTPException(status_code=404, detail="GHT context not found")

    ej = _get_ej_or_404(session, context, ej_id)
    
    namespace = session.exec(
        select(IdentifierNamespace)
        .where(IdentifierNamespace.id == namespace_id)
        .where(IdentifierNamespace.entite_juridique_id == ej_id)
    ).first()
    if not namespace:
        raise HTTPException(status_code=404, detail="Namespace not found")

    form = await request.form()
    
    # Validation basique
    if not form.get("name") or not form.get("system"):
        raise HTTPException(
            status_code=400,
            detail="Name and system are required"
        )

    # Check system uniqueness (sauf pour le même namespace)
    exists = session.exec(
        select(IdentifierNamespace)
        .where(IdentifierNamespace.system == form["system"])
        .where(IdentifierNamespace.ght_context_id == context.id)
        .where(IdentifierNamespace.id != namespace_id)
    ).first()
    if exists:
        raise HTTPException(
            status_code=400,
            detail=f"System URI {form['system']} already exists in this GHT"
        )
    
    # Mise à jour
    namespace.name = form["name"]
    namespace.system = form["system"]
    namespace.oid = form.get("oid")
    namespace.type = form.get("type", namespace.type)
    namespace.description = form.get("description")
    namespace.is_active = form.get("is_active", "true") == "true"
    
    session.add(namespace)
    session.commit()
    
    return RedirectResponse(
        f"/admin/ght/{ght_id}/ej/{ej_id}",
        status_code=302
    )
