from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional, Sequence, Union

from app.models_structure import BaseLocation, LocationStatus

HL7_FORMATS: Sequence[str] = ("%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y%m%d")


def parse_hl7_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse an HL7 date/time string (YYYYMMDD[HH[MM[SS]]]) into a datetime."""
    if not value:
        return None
    raw = value.strip()
    for fmt in HL7_FORMATS:
        try:
            return datetime.strptime(raw[: len(fmt)], fmt)
        except ValueError:
            continue
    return None


def form_datetime_to_hl7(value: Optional[str]) -> Optional[str]:
    """
    Convert a HTML datetime-local value (YYYY-MM-DDTHH:MM) to HL7 format.
    Returns None if parsing fails or value is empty.
    """
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return dt.strftime("%Y%m%d%H%M%S")


def hl7_to_form_datetime(value: Optional[str]) -> Optional[str]:
    """Convert HL7 date/time to value usable by datetime-local input."""
    dt = parse_hl7_datetime(value)
    if not dt:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M")


def _desired_status(entity: BaseLocation, *, now: Optional[datetime] = None) -> LocationStatus:
    now = now or datetime.utcnow()
    activation = parse_hl7_datetime(getattr(entity, "activation_date", None))
    deactivation = parse_hl7_datetime(getattr(entity, "deactivation_date", None))

    if activation and activation > now:
        return LocationStatus.INACTIVE
    if deactivation and deactivation <= now:
        return LocationStatus.INACTIVE
    return LocationStatus.ACTIVE


def apply_scheduled_status(
    entities: Union[BaseLocation, Iterable[BaseLocation]],
    *,
    now: Optional[datetime] = None,
) -> bool:
    """
    Ensure entities respect their scheduled activation/deactivation dates.
    Returns True when at least one status was updated.
    """
    if not entities:
        return False

    if isinstance(entities, BaseLocation):
        iterable: Iterable[BaseLocation] = (entities,)
    else:
        iterable = entities

    changed = False
    for entity in iterable:
        if not isinstance(entity, BaseLocation):
            continue
        current_status = getattr(entity, "status", None)
        try:
            current_status = LocationStatus(current_status)
        except (ValueError, TypeError):
            pass
        # Respect manual suspension
        if current_status == LocationStatus.SUSPENDED:
            continue
        desired = _desired_status(entity, now=now)
        if current_status != desired:
            entity.status = desired
            changed = True
    return changed
