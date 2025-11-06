"""Emission des messages Structure (FHIR Location et HL7 MFN) après modifications.

Cette couche envoie:
- FHIR: Bundle transaction avec PUT/DELETE Location/{id} vers les endpoints FHIR "sender"
- HL7: message MFN^M05 (snapshot complet) vers les endpoints MLLP "sender"

Utilisation:
- await emit_structure_change(entity, session, operation="insert|update")
- await emit_structure_delete(entity_id, session)
"""

from __future__ import annotations

import json
import logging
from typing import Tuple

from sqlmodel import Session, select

from app.models_endpoints import SystemEndpoint, MessageLog
from app.services.fhir_structure import entity_to_fhir_location
from app.services.fhir_organization import organization_to_bundle
from app.services.fhir_transport import post_fhir_bundle
from app.services.mllp import send_mllp
from app.services.mfn_structure import generate_mfn_message
from app.services.mfn_organization import generate_mfn_organization_message, generate_mfn_organization_delete

logger = logging.getLogger(__name__)


def _get_senders(session: Session):
    endpoints = session.exec(select(SystemEndpoint).where(SystemEndpoint.role == "sender")).all()
    fhir_senders = [e for e in endpoints if (e.kind or "").lower() == "fhir" and e.is_enabled]
    mllp_senders = [e for e in endpoints if (e.kind or "").upper() == "MLLP" and e.is_enabled]
    return fhir_senders, mllp_senders


async def _emit_organization_upsert(entity, session: Session) -> None:
    """Émet FHIR Organization vers les endpoints sender."""
    bundle = organization_to_bundle(entity, session, method="PUT")

    fhir_senders, _ = _get_senders(session)
    for endpoint in fhir_senders:
        # Pour FHIR, utiliser base_url au lieu de host
        base = endpoint.base_url or endpoint.host or ""
        if not base:
            log = MessageLog(
                direction="out",
                kind="FHIR",
                endpoint_id=endpoint.id,
                payload=json.dumps(bundle, ensure_ascii=False),
                ack_payload="Endpoint sans host/base_url",
                status="error",
            )
            session.add(log)
            continue
        try:
            status_code, response = await post_fhir_bundle(base, bundle)
            log = MessageLog(
                direction="out",
                kind="FHIR",
                endpoint_id=endpoint.id,
                payload=json.dumps(bundle, ensure_ascii=False),
                ack_payload=json.dumps(response or {}, ensure_ascii=False),
                status="sent" if 200 <= status_code < 300 else "error",
            )
        except Exception as exc:  # noqa: BLE001
            log = MessageLog(
                direction="out",
                kind="FHIR",
                endpoint_id=endpoint.id,
                payload=json.dumps(bundle, ensure_ascii=False),
                ack_payload=str(exc),
                status="error",
            )
        session.add(log)


async def _emit_organization_delete(entity_id: int, finess_ej: str, session: Session) -> None:
    """Émet FHIR Organization DELETE vers les endpoints sender."""
    from app.models_structure_fhir import EntiteJuridique
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {"request": {"method": "DELETE", "url": f"Organization/{entity_id}"}}
        ],
    }
    fhir_senders, _ = _get_senders(session)
    for endpoint in fhir_senders:
        # Pour FHIR, utiliser base_url au lieu de host
        base = endpoint.base_url or endpoint.host or ""
        if not base:
            log = MessageLog(
                direction="out",
                kind="FHIR",
                endpoint_id=endpoint.id,
                payload=json.dumps(bundle, ensure_ascii=False),
                ack_payload="Endpoint sans host/base_url",
                status="error",
            )
            session.add(log)
            continue
        try:
            status_code, response = await post_fhir_bundle(base, bundle)
            log = MessageLog(
                direction="out",
                kind="FHIR",
                endpoint_id=endpoint.id,
                payload=json.dumps(bundle, ensure_ascii=False),
                ack_payload=json.dumps(response or {}, ensure_ascii=False),
                status="sent" if 200 <= status_code < 300 else "error",
            )
        except Exception as exc:  # noqa: BLE001
            log = MessageLog(
                direction="out",
                kind="FHIR",
                endpoint_id=endpoint.id,
                payload=json.dumps(bundle, ensure_ascii=False),
                ack_payload=str(exc),
                status="error",
            )
        session.add(log)


async def _emit_mfn_organization(entity, session: Session) -> None:
    """Génère et envoie un message MFN M05 pour Organization aux endpoints MLLP."""
    mfn = generate_mfn_organization_message(session, ej=entity)
    _, mllp_senders = _get_senders(session)
    for endpoint in mllp_senders:
        ack = ""
        status = "generated"
        try:
            if not (endpoint.host and endpoint.port):
                raise ValueError("Endpoint MLLP incomplet (host/port)")
            ack = await send_mllp(endpoint.host, endpoint.port, mfn)
            status = "sent"
        except Exception as exc:  # noqa: BLE001
            status = "error"
            ack = str(exc)
        log = MessageLog(
            direction="out",
            kind="MLLP",
            endpoint_id=endpoint.id,
            payload=mfn,
            ack_payload=ack,
            status=status,
            message_type="MFN^M05"
        )
        session.add(log)


async def _emit_mfn_organization_delete(entity_id: int, finess_ej: str, session: Session) -> None:
    """Génère et envoie un message MFN M05 DELETE pour Organization."""
    mfn = generate_mfn_organization_delete(entity_id, finess_ej)
    _, mllp_senders = _get_senders(session)
    for endpoint in mllp_senders:
        ack = ""
        status = "generated"
        try:
            if not (endpoint.host and endpoint.port):
                raise ValueError("Endpoint MLLP incomplet (host/port)")
            ack = await send_mllp(endpoint.host, endpoint.port, mfn)
            status = "sent"
        except Exception as exc:  # noqa: BLE001
            status = "error"
            ack = str(exc)
        log = MessageLog(
            direction="out",
            kind="MLLP",
            endpoint_id=endpoint.id,
            payload=mfn,
            ack_payload=ack,
            status=status,
            message_type="MFN^M05"
        )
        session.add(log)


async def _emit_fhir_upsert(entity, session: Session) -> None:
    resource = entity_to_fhir_location(entity, session)
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "resource": resource,
                "request": {"method": "PUT", "url": f"Location/{entity.id}"},
            }
        ],
    }

    fhir_senders, _ = _get_senders(session)
    for endpoint in fhir_senders:
        # Pour FHIR, utiliser base_url au lieu de host
        base = endpoint.base_url or endpoint.host or ""
        if not base:
            log = MessageLog(
                direction="out",
                kind="FHIR",
                endpoint_id=endpoint.id,
                payload=json.dumps(bundle, ensure_ascii=False),
                ack_payload="Endpoint sans host/base_url",
                status="error",
            )
            session.add(log)
            continue
        try:
            status_code, response = await post_fhir_bundle(base, bundle)
            log = MessageLog(
                direction="out",
                kind="FHIR",
                endpoint_id=endpoint.id,
                payload=json.dumps(bundle, ensure_ascii=False),
                ack_payload=json.dumps(response or {}, ensure_ascii=False),
                status="sent" if 200 <= status_code < 300 else "error",
            )
        except Exception as exc:  # noqa: BLE001
            log = MessageLog(
                direction="out",
                kind="FHIR",
                endpoint_id=endpoint.id,
                payload=json.dumps(bundle, ensure_ascii=False),
                ack_payload=str(exc),
                status="error",
            )
        session.add(log)


async def _emit_fhir_delete(entity_id: int, session: Session) -> None:
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {"request": {"method": "DELETE", "url": f"Location/{entity_id}"}}
        ],
    }
    fhir_senders, _ = _get_senders(session)
    for endpoint in fhir_senders:
        # Pour FHIR, utiliser base_url au lieu de host
        base = endpoint.base_url or endpoint.host or ""
        if not base:
            log = MessageLog(
                direction="out",
                kind="FHIR",
                endpoint_id=endpoint.id,
                payload=json.dumps(bundle, ensure_ascii=False),
                ack_payload="Endpoint sans host/base_url",
                status="error",
            )
            session.add(log)
            continue
        try:
            status_code, response = await post_fhir_bundle(base, bundle)
            log = MessageLog(
                direction="out",
                kind="FHIR",
                endpoint_id=endpoint.id,
                payload=json.dumps(bundle, ensure_ascii=False),
                ack_payload=json.dumps(response or {}, ensure_ascii=False),
                status="sent" if 200 <= status_code < 300 else "error",
            )
        except Exception as exc:  # noqa: BLE001
            log = MessageLog(
                direction="out",
                kind="FHIR",
                endpoint_id=endpoint.id,
                payload=json.dumps(bundle, ensure_ascii=False),
                ack_payload=str(exc),
                status="error",
            )
        session.add(log)


async def _emit_mfn_snapshot(session: Session) -> None:
    """Génère et envoie un snapshot MFN M05 complet aux endpoints MLLP."""
    mfn = generate_mfn_message(session)
    _, mllp_senders = _get_senders(session)
    for endpoint in mllp_senders:
        ack = ""
        status = "generated"
        try:
            if not (endpoint.host and endpoint.port):
                raise ValueError("Endpoint MLLP incomplet (host/port)")
            ack = await send_mllp(endpoint.host, endpoint.port, mfn)
            status = "sent"
        except Exception as exc:  # noqa: BLE001
            status = "error"
            ack = str(exc)
        log = MessageLog(
            direction="out",
            kind="MLLP",
            endpoint_id=endpoint.id,
            payload=mfn,
            ack_payload=ack,
            status=status,
        )
        session.add(log)


async def emit_structure_change(entity, session: Session, operation: str = "update") -> None:
    """Émet FHIR (PUT) + HL7 MFN snapshot après création/mise à jour d'une entité de structure."""
    from app.models_structure_fhir import EntiteJuridique
    
    # EntiteJuridique doit être émise comme Organization, pas Location
    if isinstance(entity, EntiteJuridique):
        await _emit_organization_upsert(entity, session)
        await _emit_mfn_organization(entity, session)
        session.commit()
        return
    
    await _emit_fhir_upsert(entity, session)
    await _emit_mfn_snapshot(session)
    session.commit()


async def emit_structure_delete(entity_id: int, session: Session, entity_type: str = None, finess_ej: str = None) -> None:
    """Émet FHIR (DELETE) + HL7 MFN snapshot après suppression d'une entité de structure."""
    from app.models_structure_fhir import EntiteJuridique
    
    # Si c'est une EntiteJuridique, émettre Organization DELETE
    if entity_type == "EntiteJuridique":
        await _emit_organization_delete(entity_id, finess_ej, session)
        await _emit_mfn_organization_delete(entity_id, finess_ej, session)
        session.commit()
        return
    
    await _emit_fhir_delete(entity_id, session)
    await _emit_mfn_snapshot(session)
    session.commit()
