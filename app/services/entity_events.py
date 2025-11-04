"""
Système d'événements pour l'émission automatique de messages HL7/FHIR.

Écoute les modifications d'entités (Patient, Dossier, Venue, Mouvement)
et émet automatiquement des messages vers les endpoints configurés en "sender".

Fonctionne pour TOUTES les sources de modification:
- Messages MLLP entrants (via handlers PAM)
- Saisie via IHM web (via routers FastAPI)
- Scripts/outils (via accès direct à la DB)
"""

import asyncio
import logging
import threading
from typing import Any, Dict, Set
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models import Patient, Dossier, Venue, Mouvement
from app.services.emit_on_create import emit_to_senders_async

logger = logging.getLogger(__name__)

# Track entities to emit after flush (avoid duplicates)
_pending_emissions: Dict[int, Set[tuple]] = {}

# Thread-local flag to prevent recursive emissions (emission triggering new entities)
_emission_context = threading.local()

# Semaphore to limit concurrent emissions (prevent pool exhaustion)
_emission_semaphore = asyncio.Semaphore(5)  # Max 5 concurrent emissions


def _get_session_id(session: Session) -> int:
    """Get unique ID for session to track pending emissions."""
    return id(session)


def _schedule_emission(session: Session, entity: Any, entity_type: str, operation: str):
    """Schedule an emission after the current transaction flush."""
    # Check if we're currently inside an emission (prevent recursive loop)
    if getattr(_emission_context, 'active', False):
        logger.debug(f"[entity_events] Skipping emission during emission: {entity_type} id={entity.id}")
        return
    
    session_id = _get_session_id(session)
    
    if session_id not in _pending_emissions:
        _pending_emissions[session_id] = set()
    
    # Use (entity_id, entity_type) as key to avoid duplicate emissions
    entity_id = entity.id
    emission_key = (entity_id, entity_type, operation)
    
    if emission_key not in _pending_emissions[session_id]:
        _pending_emissions[session_id].add(emission_key)
        logger.debug(f"[entity_events] Scheduled emission: {entity_type} id={entity_id} op={operation}")


@event.listens_for(Session, "after_commit")
def after_commit(session: Session):
    """
    Triggered after transaction commit.
    Emit messages for all entities that were created/updated in this transaction.
    
    Note: We use after_commit instead of after_flush to ensure all data is persisted
    before attempting to emit messages.
    """
    session_id = _get_session_id(session)
    
    if session_id not in _pending_emissions:
        return
    
    pending = _pending_emissions.pop(session_id)
    
    if not pending:
        return
    
    logger.info(f"[entity_events] Processing {len(pending)} pending emission(s)")
    
    # Process emissions - we need to handle async in a sync context
    # We'll schedule emissions to run in background without blocking the commit
    for entity_id, entity_type, operation in pending:
        try:
            # Retrieve fresh entity from NEW session (old session is closed after commit)
            entity_class = {
                "patient": Patient,
                "dossier": Dossier,
                "venue": Venue,
                "mouvement": Mouvement,
            }.get(entity_type)
            
            if not entity_class:
                logger.error(f"[entity_events] Unknown entity type: {entity_type}")
                continue
            
            # Schedule emission in background using asyncio
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context (FastAPI), schedule the emission
                loop.create_task(_emit_in_new_session(entity_class, entity_id, entity_type, operation))
            except RuntimeError:
                # No event loop running, skip emission
                logger.warning(f"[entity_events] No event loop available, skipping emission for {entity_type} id={entity_id}")
        
        except Exception as exc:
            logger.error(f"[entity_events] Failed to schedule emission {entity_type} id={entity_id}: {exc}")


async def _emit_in_new_session(entity_class: type, entity_id: int, entity_type: str, operation: str):
    """
    Emit messages for an entity using a fresh session.
    This is called in background after the original transaction commits.
    
    IMPORTANT: 
    - Set emission flag to prevent recursive emissions (emission → new entity → emission loop).
    - Use semaphore to limit concurrent emissions and prevent pool exhaustion.
    """
    from app.db import engine
    from sqlmodel import Session as SQLModelSession
    
    # Acquire semaphore to limit concurrent emissions
    async with _emission_semaphore:
        # Mark that we're currently emitting (prevent recursive loop)
        _emission_context.active = True
        
        try:
            with SQLModelSession(engine) as emit_session:
                entity = emit_session.get(entity_class, entity_id)
                if not entity:
                    logger.warning(f"[entity_events] Entity not found in new session: {entity_type} id={entity_id}")
                    return
                
                await emit_to_senders_async(entity, entity_type, emit_session, operation)
            
            logger.info(f"[entity_events] ✓ Emitted {entity_type} id={entity_id} op={operation}")
        except Exception as exc:
            logger.error(f"[entity_events] ✗ Emission failed for {entity_type} id={entity_id}: {exc}", exc_info=True)
        finally:
            # Always clear emission flag
            _emission_context.active = False


# Listener callbacks

def _entity_after_insert(mapper, connection, target):
    """Generic handler for entity inserts."""
    session = Session.object_session(target)
    if not session:
        return
    
    entity_type = {
        Patient: "patient",
        Dossier: "dossier",
        Venue: "venue",
        Mouvement: "mouvement",
    }.get(type(target))
    
    if entity_type:
        _schedule_emission(session, target, entity_type, "insert")


def _entity_after_update(mapper, connection, target):
    """Generic handler for entity updates."""
    session = Session.object_session(target)
    if not session:
        return
    
    entity_type = {
        Patient: "patient",
        Dossier: "dossier",
        Venue: "venue",
        Mouvement: "mouvement",
    }.get(type(target))
    
    if entity_type:
        _schedule_emission(session, target, entity_type, "update")


def register_entity_events():
    """
    Register all entity event listeners.
    Call this at application startup to enable automatic message emission.
    """
    # Register insert listeners
    event.listen(Patient, "after_insert", _entity_after_insert)
    event.listen(Dossier, "after_insert", _entity_after_insert)
    event.listen(Venue, "after_insert", _entity_after_insert)
    event.listen(Mouvement, "after_insert", _entity_after_insert)
    
    # Register update listeners
    event.listen(Patient, "after_update", _entity_after_update)
    event.listen(Dossier, "after_update", _entity_after_update)
    event.listen(Venue, "after_update", _entity_after_update)
    event.listen(Mouvement, "after_update", _entity_after_update)
    
    logger.info("[entity_events] ✓ Entity event listeners registered (Patient, Dossier, Venue, Mouvement)")
