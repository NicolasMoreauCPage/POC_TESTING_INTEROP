"""
Router pour diagnostiquer le système d'événements d'entités.
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.db import get_session
from app.models import Patient
from app.models_endpoints import MessageLog
from app.models_shared import SystemEndpoint

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/entity-events/status")
async def entity_events_status(session: Session = Depends(get_session)):
    """Check if entity event listeners are registered and working."""
    from sqlalchemy import event as sa_event
    from app.models import Patient, Dossier, Venue, Mouvement
    
    # Check if listeners are registered
    # Note: event.contains() returns boolean, not count
    patient_listeners = sa_event.contains(Patient, "after_insert")
    dossier_listeners = sa_event.contains(Dossier, "after_insert")
    venue_listeners = sa_event.contains(Venue, "after_insert")
    mouvement_listeners = sa_event.contains(Mouvement, "after_insert")
    
    # Check senders
    senders = session.exec(select(SystemEndpoint).where(SystemEndpoint.role == "sender")).all()
    
    # Check recent messages
    recent_out = session.exec(
        select(MessageLog)
        .where(MessageLog.direction == "out")
        .order_by(MessageLog.id.desc())
    ).all()[:5]
    
    return {
        "status": "ok" if patient_listeners else "no_listeners",
        "listeners_registered": {
            "Patient": bool(patient_listeners),
            "Dossier": bool(dossier_listeners),
            "Venue": bool(venue_listeners),
            "Mouvement": bool(mouvement_listeners),
        },
        "sender_endpoints": {
            "count": len(senders),
            "endpoints": [
                {
                    "id": s.id,
                    "name": s.name,
                    "enabled": s.is_enabled,
                    "host": s.host,
                    "port": s.port,
                }
                for s in senders
            ],
        },
        "recent_outbound_messages": [
            {
                "id": msg.id,
                "message_type": msg.message_type,
                "status": msg.status,
                "endpoint_id": msg.endpoint_id,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in recent_out
        ],
    }


@router.post("/entity-events/test-create-patient")
async def test_create_patient(session: Session = Depends(get_session)):
    """Test endpoint: create a patient and check if emission happens."""
    import time
    from datetime import datetime
    
    # Count messages before
    before_count = len(session.exec(select(MessageLog).where(MessageLog.direction == "out")).all())
    
    # Create test patient
    patient = Patient(
        identifier=f"TEST_DEBUG_{int(time.time())}",
        external_id=f"TEST_DEBUG_{int(time.time())}",
        family="DEBUGTEST",
        given="AutoEmit",
        birth_date="1990-01-01",
        gender="M"
    )
    session.add(patient)
    session.commit()
    
    # Wait a bit
    time.sleep(2)
    
    # Count messages after
    session.expire_all()
    after_count = len(session.exec(select(MessageLog).where(MessageLog.direction == "out")).all())
    new_messages = after_count - before_count
    
    return {
        "patient_created": {
            "id": patient.id,
            "identifier": patient.identifier,
            "name": f"{patient.family} {patient.given}",
        },
        "messages_before": before_count,
        "messages_after": after_count,
        "new_messages": new_messages,
        "emission_worked": new_messages > 0,
    }
