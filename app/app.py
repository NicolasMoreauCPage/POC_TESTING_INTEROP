"""
Composition de l'application FastAPI (MedData Bridge)

Rôle de ce module
- Construire l'instance FastAPI et y brancher middlewares, routeurs et admin.
- Gérer le cycle de vie (lifespan): initialisation DB, rechargement des serveurs
    MLLP, arrêt propre en extinction.
- Exposer un `MLLPManager` partagé via `app.state`.

Points clés
- En mode tests (env TESTING=1), on évite l'init DB/serveurs et on laisse les
    fixtures contrôler l'environnement pour des tests isolés.
- Les logs MLLP détaillés s'activent avec `MLLP_TRACE=1`.
"""

import logging, os, secrets

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, APIRouter
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqladmin import Admin, ModelView
from sqlmodel import select

from app.middleware.flash import FlashMessageMiddleware
from app.middleware.ght_context import GHTContextMiddleware

from app.db import init_db, engine, get_session
from app.models import Patient, Dossier, Venue, Mouvement
from app.models_structure_fhir import IdentifierNamespace
from app.models_endpoints import SystemEndpoint, MessageLog
from app import models_scenarios  # ensure scenario models are registered
from app.models_structure import (
    EntiteGeographique, Pole, Service, UniteFonctionnelle,
    UniteHebergement, Chambre, Lit
)
from app.db_session_factory import session_factory
from app.services.transport_inbound import on_message_inbound
from app.services.mllp_manager import MLLPManager
from app.services.entity_events import register_entity_events

from app.routers import (
    home, patients, dossiers, venues, mouvements, structure_hl7,
    endpoints, transport, transport_views, fhir_inbox, messages, interop,
    generate, structure, workflow, fhir_structure, vocabularies, ght, namespaces,
    health, scenarios, guide, docs, ihe, dossier_type, structure_select
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
if os.getenv("MLLP_TRACE", "0") in ("1","true","True"):
    logging.getLogger("mllp").setLevel(logging.DEBUG)

# Instance unique du manager et publication via app.state
# - `session_factory` fournit des sessions DB courtes et sûres côté workers.
# - `on_message_inbound` est appelé pour chaque message entrant HL7.
mllp_manager = MLLPManager(session_factory=session_factory, on_message=on_message_inbound)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # En tests, on ne veut pas initialiser la DB de prod (poc.db) ni démarrer
    # des serveurs MLLP en arrière-plan. Les tests surchargent l'accès DB via
    # des overrides, on saute donc init/reload quand TESTING est présent.
    testing = os.getenv("TESTING", "0") in ("1", "true", "True")
    if not testing:
        init_db()
        # Register entity event listeners for automatic message emission
        register_entity_events()
        logging.info("Entity event listeners registered for automatic emission")
        
        # Démarrage idempotent
        sess = next(get_session())
        try:
            # Initialiser les vocabulaires si demandé
            if os.getenv("INIT_VOCAB", "0") in ("1", "true", "True"):
                from app.vocabulary_init import init_vocabularies
                init_vocabularies(sess)
                logging.info("Vocabulaires initialisés")
            
            await mllp_manager.reload_all(sess)
        finally:
            sess.close()

    try:
        yield
    finally:
        if not testing:
            await mllp_manager.stop_all()

# Admin auto (CRUD) via SQLAdmin
class PatientAdmin(ModelView, model=Patient):
    # Vue d'admin pour Patient
    name = "Patient"
    name_plural = "Patients"

class VenueAdmin(ModelView, model=Venue):
    name = "Venue"
    name_plural = "Venues"

class DossierAdmin(ModelView, model=Dossier):
    name = "Dossier"
    name_plural = "Dossiers"

class MouvementAdmin(ModelView, model=Mouvement):
    name = "Mouvement"
    name_plural = "Mouvements"

class SystemEndpointAdmin(ModelView, model=SystemEndpoint):
    name = "Point d'accès système"
    name_plural = "Points d'accès systèmes"
    icon = "fa-solid fa-network-wired"
    column_list = [
        SystemEndpoint.id, SystemEndpoint.name, SystemEndpoint.role,
        SystemEndpoint.is_enabled, SystemEndpoint.created_at,
        SystemEndpoint.forced_identifier_system, SystemEndpoint.forced_identifier_oid
    ]
    column_searchable_list = [SystemEndpoint.name, SystemEndpoint.forced_identifier_system]
    column_sortable_list = [SystemEndpoint.id, SystemEndpoint.name, SystemEndpoint.is_enabled]
    # Afficher payload / ack en lecture (onglets "Detail")
    details_template = None  # on garde le template par défaut

class MessageLogAdmin(ModelView, model=MessageLog):
    name = "Message"
    name_plural = "Messages"
    icon = "fa-solid fa-envelope"
    column_list = [
        MessageLog.id, MessageLog.direction, MessageLog.kind, MessageLog.endpoint_id,
        MessageLog.status, MessageLog.correlation_id, MessageLog.created_at,
    ]
    column_searchable_list = [MessageLog.status, MessageLog.correlation_id]
    column_sortable_list = [MessageLog.id, MessageLog.created_at, MessageLog.status]
    can_create = False   # journal en lecture seule
    can_edit = False

class NamespaceAdmin(ModelView, model=IdentifierNamespace):
    name = "Espace de noms"
    name_plural = "Espaces de noms"
    icon = "fa-solid fa-tag"
    column_list = [
        IdentifierNamespace.id, IdentifierNamespace.name, IdentifierNamespace.system, IdentifierNamespace.type,
        IdentifierNamespace.is_active, IdentifierNamespace.ght_context_id
    ]
    column_searchable_list = [IdentifierNamespace.name, IdentifierNamespace.system, IdentifierNamespace.type]
    column_sortable_list = [IdentifierNamespace.id, IdentifierNamespace.name, IdentifierNamespace.is_active]
    can_delete = False
    # Afficher payload / ack en lecture (onglets "Detail")
    details_template = None  # on garde le template par défaut

    # Admin pour la structure
class EntiteGeographiqueAdmin(ModelView, model=EntiteGeographique):
    name = "Entité Géographique"
    name_plural = "Entités Géographiques"
    icon = "fa-solid fa-hospital"
    column_list = [EntiteGeographique.id, EntiteGeographique.name, EntiteGeographique.finess]

class PoleAdmin(ModelView, model=Pole):
    name = "Pôle"
    name_plural = "Pôles"
    icon = "fa-solid fa-sitemap"
    column_list = [Pole.id, Pole.name, Pole.identifier]

class ServiceAdmin(ModelView, model=Service):
    name = "Service"
    name_plural = "Services"
    icon = "fa-solid fa-building"
    column_list = [Service.id, Service.name, Service.identifier, Service.service_type]

class UniteFonctionnelleAdmin(ModelView, model=UniteFonctionnelle):
    name = "Unité Fonctionnelle"
    name_plural = "Unités Fonctionnelles"
    icon = "fa-solid fa-folder"
    column_list = [UniteFonctionnelle.id, UniteFonctionnelle.name, UniteFonctionnelle.identifier, UniteFonctionnelle.service_id]

class UniteHebergementAdmin(ModelView, model=UniteHebergement):
    name = "Unité d'Hébergement"
    name_plural = "Unités d'Hébergement"
    icon = "fa-solid fa-bed"
    column_list = [UniteHebergement.id, UniteHebergement.name, UniteHebergement.identifier]

class ChambreAdmin(ModelView, model=Chambre):
    name = "Chambre"
    name_plural = "Chambres"
    icon = "fa-solid fa-door-open"
    column_list = [Chambre.id, Chambre.name, Chambre.identifier]

class LitAdmin(ModelView, model=Lit):
    name = "Lit"
    name_plural = "Lits"
    icon = "fa-solid fa-bed"
    column_list = [Lit.id, Lit.name, Lit.identifier, Lit.status, Lit.operational_status]

def create_app() -> FastAPI:
    app = FastAPI(
        title="FHIR PAM POC UI",
        version="0.2.0",
        lifespan=lifespan
    )

    print("\nFastAPI app initialization")

    # Filtre Jinja2 global pour masquer None ou 'None' par '—'
    def none_to_dash(value):
        if value is None or value == "None":
            return "—"
        return value
    # Ajout du filtre au moteur de templates Jinja2
    from fastapi.templating import Jinja2Templates
    templates_dir = str(Path(__file__).parent / "templates")
    templates = Jinja2Templates(directory=templates_dir)
    templates.env.filters["none_to_dash"] = none_to_dash
    # Stocker dans app.state pour accès dans les routes si besoin
    app.state.templates = templates

    # Servir les fichiers statiques (CSS/JS)
    static_dir = str(Path(__file__).parent / "static")
    app.mount("/static", StaticFiles(directory=static_dir, html=True, check_dir=True), name="static")

    # Session et contexte GHT: IMPORTANT - dans Starlette, le dernier middleware
    # ajouté est exécuté en premier. Nous voulons que SessionMiddleware s'exécute
    # AVANT FlashMessageMiddleware et GHTContextMiddleware pour que request.session
    # soit disponible dans ces middlewares. Donc on ajoute d'abord Flash/GHT,
    # PUIS SessionMiddleware en dernier.
    app.add_middleware(FlashMessageMiddleware)
    app.add_middleware(GHTContextMiddleware)

    session_secret = (
        os.getenv("SESSION_SECRET_KEY")
        or os.getenv("SESSION_SECRET")
        or os.getenv("SECRET_KEY")
    )
    if not session_secret:
        session_secret = secrets.token_urlsafe(32)
        logging.getLogger(__name__).warning(
            "SESSION_SECRET_KEY non défini - utilisation d'un secret éphémère pour cette instance"
        )
    app.add_middleware(SessionMiddleware, secret_key=session_secret)

    # exposer le manager aux routeurs
    app.state.mllp_manager = mllp_manager

    # Note: admin interface (SQLAdmin) will be created after route
    # registration to avoid catching /admin/* routes before our own
    # admin-related pages (like /admin/ght). The Admin instance is
    # created later just before returning the app.

    # Core application routes in dependency order
    # Routes are registered in logical dependency order
    # Some routers have their own prefix defined in their router creation
    
    # Register routes in order with correct prefixes
    print("\nRegistering routes:")
    
    # 1. Basic UI routes 
    app.include_router(home.router)
    print(" - Home router mounted at /")
    
    # 2. Entity and core data routes - all have their own prefixes
    app.include_router(patients.router)
    app.include_router(dossiers.router)
    app.include_router(venues.router)
    app.include_router(mouvements.router)
    print(" - Core entity routers mounted with their prefixes")
    
    # 3. Structure management
    app.include_router(structure.router)  # Has prefix /structure
    app.include_router(structure.api_router)  # Has prefix /api/structure
    app.include_router(structure_hl7.router)  # Has prefix /structure
    app.include_router(fhir_structure.router)  # Has prefix /fhir
    app.include_router(structure_select.router)  # Has prefix /structure
    print(" - Structure routers mounted")
    
    # 4. Admin interfaces (mount under /admin so templates/redirects using
    # /admin/ght work as expected)
    app.include_router(ght.router, prefix="/admin")
    app.include_router(namespaces.router, prefix="/admin")
    print(" - Admin routers mounted under /admin")
    
    # 5. Integration and transport
    app.include_router(messages.router)
    app.include_router(fhir_inbox.router)
    app.include_router(transport_views.router, prefix="/transport")
    app.include_router(transport.router)  # Has own prefix
    app.include_router(endpoints.router)  # Has own prefix
    app.include_router(ihe.router)  # Has own prefix /ihe
    print(" - Integration routers mounted")
    
    # 6. Utilities and workflow
    app.include_router(workflow.router)
    app.include_router(generate.router)
    app.include_router(interop.router)
    app.include_router(vocabularies.router)
    # Context management (patient/dossier quick set/clear)
    try:
        from app.routers import context
        app.include_router(context.router, prefix="/context", tags=["context"])
        print(" - Context router mounted")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Context router not available: {e}")
    app.include_router(guide.router)
    app.include_router(docs.router)
    app.include_router(scenarios.router)
    print(" - Utility routers mounted")
    
    # 7. Test helpers
    app.include_router(health.router)
    print(" - Test helpers mounted")
    
    # 8. Debug endpoints (dev only)
    try:
        from app.routers import debug_events
        app.include_router(debug_events.router)
        print(" - Debug router mounted at /debug")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Debug router not available: {e}")
    
    print("All routes registered.")

    # Initialize the admin interface (SQLAdmin) only when not running
    # tests. In test runs a separate test engine/session is used and
    # creating Admin against the production engine can cause Operational
    # errors when the production DB file is absent or schema differs.
    testing = os.getenv("TESTING", "0") in ("1", "true", "True")
    if not testing:
        # We do this after route registration so SQLAdmin's mounting at
        # /admin doesn't intercept our custom /admin/ght pages.
        # Mount SQLAdmin under /sqladmin to avoid conflict with our admin pages.
        admin = Admin(app, engine, base_url="/sqladmin")

        # Entités de base
        admin.add_view(PatientAdmin)
        admin.add_view(DossierAdmin)
        admin.add_view(VenueAdmin)
        admin.add_view(MouvementAdmin)

        # Structure (hiérarchie des locations)
        admin.add_view(EntiteGeographiqueAdmin)
        admin.add_view(PoleAdmin)
        admin.add_view(ServiceAdmin)
        admin.add_view(UniteFonctionnelleAdmin)
        admin.add_view(UniteHebergementAdmin)
        admin.add_view(ChambreAdmin)
        admin.add_view(LitAdmin)

        # Connectivité et messages
        admin.add_view(SystemEndpointAdmin)
        admin.add_view(MessageLogAdmin)

        # Espaces de noms
        admin.add_view(NamespaceAdmin)

    return app

# Create module-level `app` only when not running tests. Tests call
# `create_app()` directly after preparing the test database so we avoid
# side-effects (like initializing the production DB or starting MLLP
# managers) at import time which can interfere with test setup.
if os.getenv("TESTING", "0") not in ("1", "true", "True"):
    app = create_app()
else:
    # Tests will call create_app() explicitly; keep a placeholder to
    # avoid AttributeError in environments that import `app.app`.
    app = None
# reload trigger lun. 03 nov. 2025 08:00:19 CET
