#!/usr/bin/env python3
"""Stepwise roundtrip for PAM ADT messages.

Process each outbound ADT message (generated earlier and stored in pam_export/),
rewrite patient primary identifier to avoid collision in destination GHT, add original
as secondary identifier, then reinject into a destination FILE endpoint under new GHT/EJ.

Identifier rewrite strategy:
  - Original first PID-3 value V becomes V-DST as the first repetition (new patient.identifier)
  - Original CX kept as second repetition so mapping retained.

Destination context:
  GHT code: GHT-DST
  EJ finess: 700DST001
  Endpoint: PAM Roundtrip Destination (FILE role=receiver)

Usage:
  PYTHONPATH=. python tools/roundtrip_pam_stepwise.py --limit 10
  PYTHONPATH=. python tools/roundtrip_pam_stepwise.py --all
"""
import argparse, sys, os, re
from pathlib import Path
from typing import List
from sqlmodel import select, Session

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db import engine
from app.db_session_factory import session_factory
from app.models_structure_fhir import GHTContext, EntiteJuridique
from app.models_shared import SystemEndpoint
from app.services.file_poller import FilePollerService
from app.models import Patient, Dossier, Venue, Mouvement

EXPORT_DIR = PROJECT_ROOT / "pam_export"
DST_INBOX = PROJECT_ROOT / "pam_inbox_dst"
DST_ARCHIVE = PROJECT_ROOT / "pam_archive_dst"
DST_ERROR = PROJECT_ROOT / "pam_error_dst"
DST_ENDPOINT_NAME = "PAM Roundtrip Destination"

PID_REGEX = re.compile(r"^PID\|")

def ensure_destination_context(session) -> SystemEndpoint:
    ght = session.exec(select(GHTContext).where(GHTContext.code == "GHT-DST")).first()
    if not ght:
        ght = GHTContext(name="GHT Destination", code="GHT-DST", description="Contexte destination roundtrip", is_active=True)
        session.add(ght); session.commit(); session.refresh(ght)
        print(f"✓ GHT-DST créé")
    ej = session.exec(select(EntiteJuridique).where(EntiteJuridique.finess_ej == "700DST001")).first()
    if not ej:
        ej = EntiteJuridique(name="EJ Destination", finess_ej="700DST001", ght_context_id=ght.id)
        session.add(ej); session.commit(); session.refresh(ej)
        print("✓ EJ destination créée")
    endpoint = session.exec(select(SystemEndpoint).where(SystemEndpoint.name == DST_ENDPOINT_NAME)).first()
    if not endpoint:
        endpoint = SystemEndpoint(
            name=DST_ENDPOINT_NAME,
            kind="FILE",
            role="receiver",
            is_enabled=True,
            ght_context_id=ght.id,
            inbox_path=str(DST_INBOX),
            archive_path=str(DST_ARCHIVE),
            error_path=str(DST_ERROR),
            file_extensions=".hl7,.txt"
        )
        session.add(endpoint); session.commit(); session.refresh(endpoint)
        print(f"✓ Endpoint destination créé id={endpoint.id}")
    else:
        changed = False
        for attr, val in [
            ("inbox_path", str(DST_INBOX)),
            ("archive_path", str(DST_ARCHIVE)),
            ("error_path", str(DST_ERROR)),
        ]:
            if getattr(endpoint, attr) != val:
                setattr(endpoint, attr, val); changed = True
        if not endpoint.is_enabled:
            endpoint.is_enabled = True; changed = True
        if changed:
            session.add(endpoint); session.commit()
            print("✓ Endpoint destination mis à jour")
        else:
            print("✓ Endpoint destination déjà configuré")
    return endpoint

def rewrite_pid_identifiers(message: str) -> str:
    lines = message.splitlines()
    new_lines: List[str] = []
    for line in lines:
        if PID_REGEX.match(line):
            parts = line.split("|")
            if len(parts) > 3:
                original_field = parts[3] or "UNDEF"
                repetitions = original_field.split("~") if original_field else [original_field]
                original = repetitions[0]
                value = original.split("^")[0] if original else "UNDEF"
                if value in ("None", "", "UNDEF"):
                    # Synthesize a value based on control id (MSH-10) or file fallback
                    control_id = None
                    msh_line = next((l for l in lines if l.startswith("MSH")), None)
                    if msh_line:
                        msh_parts = msh_line.split("|")
                        if len(msh_parts) > 9:
                            control_id = msh_parts[9]
                    base = control_id or f"GEN{os.urandom(3).hex()}"
                    value = base
                new_value = f"{value}-DST"
                new_cx = f"{new_value}^^^ROUNDTRIP-DST&1.2.250.999.1&ISO^PI"
                parts[3] = "~".join([new_cx, original] + repetitions[1:])
                line = "|".join(parts)
        new_lines.append(line)
    return "\r".join(new_lines)

def process_messages(limit: int | None, all_mode: bool):
    DST_INBOX.mkdir(exist_ok=True)
    DST_ARCHIVE.mkdir(exist_ok=True)
    DST_ERROR.mkdir(exist_ok=True)

    with session_factory() as session:
        ensure_destination_context(session)

    files = sorted([p for p in EXPORT_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".hl7"])
    if not all_mode and limit is not None:
        files = files[:limit]

    total_injected = 0
    mapping = []  # (original, new)

    for f in files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        rewritten = rewrite_pid_identifiers(content)
        # Write to destination inbox
        dst_file = DST_INBOX / f.name
        dst_file.write_text(rewritten, encoding="utf-8")

        # Scan just after writing (stepwise)
        with session_factory() as session:
            poller = FilePollerService(session)
            from app.models_shared import SystemEndpoint as _SE
            dest_ep = session.exec(select(_SE).where(_SE.name == DST_ENDPOINT_NAME)).first()
            import asyncio
            if dest_ep:
                asyncio.run(poller._scan_endpoint(dest_ep))
            # Retrieve newest patient (assumes scan only destination endpoint)
            patient = session.exec(select(Patient).order_by(Patient.id.desc())).first()
            if patient:
                # Extract original value (value without -DST) from first repetition
                # Extract original identifier from PID repetitions; handle cases where base was 'None'
                pid_line = next((l for l in rewritten.split("\r") if l.startswith("PID")), None)
                orig_value = "?"
                if pid_line:
                    pid_parts = pid_line.split("|")
                    if len(pid_parts) > 3 and pid_parts[3]:
                        reps = pid_parts[3].split("~")
                        if len(reps) > 1:
                            orig_value = reps[1].split("^")[0]
                        else:
                            orig_value = reps[0].split("^")[0]
                mapping.append((orig_value, patient.identifier))

        total_injected += 1
        print(f"✓ Reinjection {f.name} -> patient identifier={mapping[-1][1]}")

    print("\n=== Roundtrip Résumé ===")
    print(f"Messages réinjectés: {total_injected}")
    print("Mapping original -> nouveau (limite 10):")
    for orig, new in mapping[:10]:
        print(f"  {orig} -> {new}")

def main():
    ap = argparse.ArgumentParser(description="Roundtrip stepwise PAM")
    ap.add_argument("--limit", type=int, default=5, help="Nombre de messages à réinjecter (ignoré si --all)")
    ap.add_argument("--all", action="store_true", help="Traiter tous les messages exportés")
    args = ap.parse_args()
    process_messages(args.limit, args.all)

if __name__ == "__main__":
    sys.exit(main())
