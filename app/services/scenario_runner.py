from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Iterable, List, Optional, Tuple

from sqlmodel import Session, select

from app.models_endpoints import FHIRConfig, MessageLog, SystemEndpoint
from app.models_scenarios import InteropScenario, InteropScenarioStep
from app.services.fhir_transport import post_fhir_bundle
from app.services.mllp import parse_msh_fields, send_mllp
from app.services.scenario_date_updater import update_hl7_message_dates
from app.services.scenario_transform import transform_hl7_for_context


class ScenarioExecutionError(Exception):
    """Erreur personnalisée pour l'exécution d'un scénario."""


def _build_fhir_targets(endpoint: SystemEndpoint) -> List[Tuple[str, str, str | None]]:
    targets: List[Tuple[str, str, str | None]] = []
    for cfg in getattr(endpoint, "fhir_configs", []) or []:
        if isinstance(cfg, FHIRConfig) and cfg.is_enabled and cfg.base_url:
            targets.append((cfg.base_url, cfg.auth_kind or "none", cfg.auth_token))
    if targets:
        return targets

    host = (endpoint.host or "").strip()
    if not host:
        return targets

    if host.startswith(("http://", "https://")):
        base_url = host
        if endpoint.port and ":" not in host.split("//", 1)[1]:
            base_url = f"{host}:{endpoint.port}"
    else:
        scheme = "https" if str(endpoint.port) in {"443", "8443"} else "http"
        base_url = f"{scheme}://{host}"
        if endpoint.port:
            base_url = f"{base_url}:{endpoint.port}"
    targets.append((base_url, "none", None))
    return targets


def _extract_trigger(step: InteropScenarioStep) -> Optional[str]:
    if step.message_type:
        parts = step.message_type.split("^")
        if len(parts) > 1 and parts[1]:
            return parts[1]
        return step.message_type
    try:
        fields = parse_msh_fields(step.payload)
        return fields.get("trigger")
    except Exception:
        return None


async def _send_hl7_step(
    session: Session,
    step: InteropScenarioStep,
    endpoint: SystemEndpoint,
    update_dates: bool = True
) -> MessageLog:
    """
    Envoie une étape HL7 via MLLP.
    
    Args:
        session: Session de base de données
        step: Étape du scénario à envoyer
        endpoint: Endpoint cible
        update_dates: Si True, met à jour les dates du message pour qu'elles soient récentes
    """
    if not endpoint.host or not endpoint.port:
        raise ScenarioExecutionError("Endpoint MLLP incomplet (host/port manquant)")

    # Adapter le message au contexte local (MSH, namespaces PID-3)
    try:
        # Privilégier le contexte du scénario, sinon celui de l'endpoint
        ght_context_id = None
        try:
            # Relationship lazy; safe in this session
            if step.scenario and step.scenario.ght_context_id:
                ght_context_id = step.scenario.ght_context_id
        except Exception:
            ght_context_id = None
        if not ght_context_id:
            ght_context_id = getattr(endpoint, "ght_context_id", None)
        payload_to_send = transform_hl7_for_context(
            session,
            step.payload,
            endpoint=endpoint,
            ght_context_id=ght_context_id,
            remap_pid3=True,
        )
    except Exception:
        # En cas d'erreur transformation, fallback au payload original
        payload_to_send = step.payload

    # Mettre à jour les dates du message si demandé
    if update_dates:
        try:
            payload_to_send = update_hl7_message_dates(payload_to_send, datetime.utcnow())
        except Exception:
            # En cas d'erreur de mise à jour, utiliser le payload original
            payload_to_send = payload_to_send

    ack_payload = ""
    status = "error"
    try:
        ack_payload = await send_mllp(endpoint.host, endpoint.port, payload_to_send)
        status = "sent" if ack_payload else "unknown"
    except Exception as exc:
        ack_payload = str(exc)
        status = "error"
        raise ScenarioExecutionError(str(exc))

    msh_fields = parse_msh_fields(payload_to_send)
    log = MessageLog(
        direction="out",
        kind="MLLP",
        endpoint_id=endpoint.id,
        payload=payload_to_send,  # Logger le message avec dates mises à jour
        ack_payload=ack_payload or "",
        status=status,
        correlation_id=msh_fields.get("control_id"),
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


async def _send_fhir_step(session: Session, step: InteropScenarioStep, endpoint: SystemEndpoint) -> MessageLog:
    try:
        payload_obj = json.loads(step.payload)
    except json.JSONDecodeError as exc:
        raise ScenarioExecutionError(f"Payload FHIR invalide: {exc}") from exc

    targets = _build_fhir_targets(endpoint)
    if not targets:
        raise ScenarioExecutionError("Endpoint FHIR sans configuration d'URL")

    status = "error"
    ack_payload = ""
    last_status_code = None

    for base_url, auth_kind, auth_token in targets:
        try:
            status_code, response = await post_fhir_bundle(
                base_url,
                payload_obj,
                auth_kind=auth_kind,
                auth_token=auth_token,
            )
            last_status_code = status_code
            ack_payload = json.dumps(response or {}, default=str)
            status = "sent" if 200 <= status_code < 300 else "error"
            if status == "sent":
                break
        except Exception as exc:
            ack_payload = str(exc)
            status = "error"
            raise ScenarioExecutionError(str(exc))

    log = MessageLog(
        direction="out",
        kind="FHIR",
        endpoint_id=endpoint.id,
        payload=json.dumps(payload_obj, default=str),
        ack_payload=ack_payload,
        status=status,
        correlation_id=str(last_status_code) if last_status_code is not None else None,
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


async def send_step(
    session: Session,
    step: InteropScenarioStep,
    endpoint: SystemEndpoint,
    update_dates: bool = True,
) -> MessageLog:
    """
    Envoie une étape de scénario au système cible.
    
    Args:
        session: Session de base de données
        step: Étape du scénario à envoyer
        endpoint: Endpoint cible
        update_dates: Si True, met à jour automatiquement les dates HL7 pour qu'elles soient récentes
    """
    trigger = _extract_trigger(step)

    if step.message_format.lower() == "hl7" and trigger and trigger.startswith("Z") and trigger != "Z99":
        log = MessageLog(
            direction="out",
            kind="MLLP",
            endpoint_id=endpoint.id,
            payload=step.payload,
            ack_payload="Message Zxx obsolète (non émis)",
            status="skipped",
            correlation_id=None,
        )
        session.add(log)
        session.commit()
        session.refresh(log)
        return log

    if endpoint.kind == "MLLP":
        return await _send_hl7_step(session, step, endpoint, update_dates=update_dates)
    if endpoint.kind == "FHIR":
        return await _send_fhir_step(session, step, endpoint)
    raise ScenarioExecutionError(f"Type d'endpoint non supporté: {endpoint.kind}")


async def send_scenario(
    session: Session,
    scenario: InteropScenario,
    endpoint: SystemEndpoint,
    *,
    step_ids: Iterable[int] | None = None,
    update_dates: bool = True,
) -> List[MessageLog]:
    """
    Envoie tout ou partie d'un scénario dans l'ordre des steps.
    
    Args:
        session: Session de base de données
        scenario: Scénario à envoyer
        endpoint: Endpoint cible
        step_ids: IDs des étapes spécifiques à envoyer (None = toutes)
        update_dates: Si True, met à jour automatiquement les dates HL7 pour qu'elles soient récentes
    """
    logs: List[MessageLog] = []
    steps = scenario.steps
    if step_ids:
        ids = set(step_ids)
        steps = [step for step in steps if step.id in ids]

    steps = sorted(steps, key=lambda s: s.order_index)

    for step in steps:
        log = await send_step(session, step, endpoint, update_dates=update_dates)
        logs.append(log)
        if step.delay_seconds:
            await asyncio.sleep(step.delay_seconds)

    return logs


def list_scenarios(session: Session) -> List[InteropScenario]:
    return session.exec(select(InteropScenario).order_by(InteropScenario.name)).all()


def get_scenario(session: Session, scenario_id: int) -> Optional[InteropScenario]:
    return session.get(InteropScenario, scenario_id)
