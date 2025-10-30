import logging, os

from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqlmodel import select

from app.db import init_db, engine, get_session
from app.models import Patient, Dossier, Venue, Mouvement
from app.models_endpoints import SystemEndpoint, MessageLog
from app.db_session_factory import session_factory
from app.services.transport_inbound import on_message_inbound
from app.services.mllp_manager import MLLPManager

from app.routers import (
    home, patients, dossiers, venues, mouvements,
    endpoints, transport, fhir_inbox, messages, interop,
    generate
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
if os.getenv("MLLP_TRACE", "0") in ("1","true","True"):
    logging.getLogger("mllp").setLevel(logging.DEBUG)

# Instance unique du manager et publication via app.state
mllp_manager = MLLPManager(session_factory=session_factory, on_message=on_message_inbound)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # démarrage idempotent
    sess = next(get_session())
    try:
        await mllp_manager.reload_all(sess)
    finally:
        sess.close()
    try:
        yield
    finally:
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
    name = "Système"
    name_plural = "Systèmes"
    icon = "fa-solid fa-plug"
    column_list = [
        SystemEndpoint.id, SystemEndpoint.name, SystemEndpoint.kind, SystemEndpoint.role,
        SystemEndpoint.is_enabled, SystemEndpoint.host, SystemEndpoint.port,
        SystemEndpoint.base_url, SystemEndpoint.updated_at,
    ]
    column_searchable_list = [SystemEndpoint.name, SystemEndpoint.kind, SystemEndpoint.base_url]
    column_sortable_list = [SystemEndpoint.id, SystemEndpoint.updated_at, SystemEndpoint.is_enabled]
    form_columns = [
        SystemEndpoint.name, SystemEndpoint.kind, SystemEndpoint.role, SystemEndpoint.is_enabled,
        SystemEndpoint.host, SystemEndpoint.port,
        SystemEndpoint.sending_app, SystemEndpoint.sending_facility,
        SystemEndpoint.receiving_app, SystemEndpoint.receiving_facility,
        SystemEndpoint.base_url, SystemEndpoint.auth_kind, SystemEndpoint.auth_token,
    ]

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
    can_delete = False
    # Afficher payload / ack en lecture (onglets "Detail")
    details_template = None  # on garde le template par défaut


def create_app() -> FastAPI:
    app = FastAPI(title="FHIR PAM POC UI", version="0.2.0", lifespan=lifespan)

    # exposer le manager aux routeurs
    app.state.mllp_manager = mllp_manager

    admin = Admin(app, engine)
    admin.add_view(PatientAdmin)
    admin.add_view(VenueAdmin)
    admin.add_view(DossierAdmin)
    admin.add_view(MouvementAdmin)
    admin.add_view(SystemEndpointAdmin)
    admin.add_view(MessageLogAdmin)

    app.include_router(home.router)
    app.include_router(endpoints.router)
    app.include_router(transport.router)
    app.include_router(fhir_inbox.router)
    app.include_router(messages.router)
    app.include_router(patients.router)
    app.include_router(dossiers.router)
    app.include_router(venues.router)
    app.include_router(mouvements.router)
    app.include_router(generate.router)
    app.include_router(interop.router)

    return app

app = create_app()
