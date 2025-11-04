from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from starlette.responses import RedirectResponse

from app.db import get_session
from app.models_structure_fhir import GHTContext, IdentifierNamespace
from app.models_identifiers import Identifier
from app.middleware.ght_context import get_active_ght_context

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/ght", tags=["ght"])

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
