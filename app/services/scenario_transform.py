"""
Helpers to adapt imported IHE/HL7 scenario payloads to a local test context.

Goals
- Normalize/override MSH sending/receiving application/facility using the
  selected SystemEndpoint fields (sending_app, sending_facility, receiving_app,
  receiving_facility).
- Optionally remap PID-3 assigning authority (CX-4) to a namespace configured
  in the GHTContext (typically the IPP namespace) so identifiers match the
  local sandbox expectations.

The transformation is conservative: only present fields are changed, other
segments and values are left untouched.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from app.models_structure_fhir import IdentifierNamespace, GHTContext
from app.models_shared import SystemEndpoint


def _remap_msh(msh_line: str, endpoint: SystemEndpoint) -> str:
    parts = msh_line.split("|")
    # Ensure minimal MSH skeleton
    while len(parts) < 12:
        parts.append("")

    # MSH-3..MSH-6 overrides when provided on endpoint
    if endpoint.sending_app:
        parts[2] = endpoint.sending_app
    if endpoint.sending_facility:
        parts[3] = endpoint.sending_facility
    if endpoint.receiving_app:
        parts[4] = endpoint.receiving_app
    if endpoint.receiving_facility:
        parts[5] = endpoint.receiving_facility

    return "|".join(parts)


def _remap_pid_identifiers(pid_line: str, new_system: Optional[str]) -> str:
    if not new_system:
        return pid_line
    parts = pid_line.split("|")
    if len(parts) <= 3 or not parts[3]:
        return pid_line

    reps = parts[3].split("~")
    new_reps = []
    for cx in reps:
        if not cx:
            new_reps.append(cx)
            continue
        cx_parts = cx.split("^")
        # Ensure at least 5 components up to CX-5 (Identifier Type Code)
        while len(cx_parts) < 5:
            cx_parts.append("")
        # CX-4 assigning authority becomes the configured system/namespace
        cx_parts[3] = new_system
        new_reps.append("^".join(cx_parts))

    parts[3] = "~".join(new_reps)
    return "|".join(parts)


def _select_namespace_system(session: Session, ght_context_id: Optional[int]) -> Optional[str]:
    if not ght_context_id:
        return None
    # Prefer IPP-type namespace; else first active namespace
    ns = session.exec(
        select(IdentifierNamespace)
        .where(IdentifierNamespace.ght_context_id == ght_context_id)
        .where(IdentifierNamespace.is_active == True)
        .order_by(IdentifierNamespace.type == "IPP").order_by(IdentifierNamespace.id)
    ).all()
    if not ns:
        return None
    # Try to find IPP first
    for n in ns:
        if (n.type or "").upper() == "IPP":
            return n.system or n.oid
    # Fallback: first namespace system/oid
    n0 = ns[0]
    return n0.system or n0.oid


def transform_hl7_for_context(
    session: Session,
    payload: str,
    *,
    endpoint: SystemEndpoint,
    ght_context_id: Optional[int] = None,
    remap_pid3: bool = True,
) -> str:
    """
    Apply light-touch transformations to an HL7 message so it matches
    the local sandbox configuration.

    - Override MSH-3..6 with endpoint settings (when provided)
    - Remap PID-3 assigning authority to the GHT namespace system (optional)
    """
    lines = payload.split("\r")
    out_lines = []
    new_system = _select_namespace_system(session, ght_context_id) if remap_pid3 else None
    for line in lines:
        if line.startswith("MSH|"):
            out_lines.append(_remap_msh(line, endpoint))
        elif remap_pid3 and line.startswith("PID|"):
            out_lines.append(_remap_pid_identifiers(line, new_system))
        else:
            out_lines.append(line)
    return "\r".join(out_lines)
