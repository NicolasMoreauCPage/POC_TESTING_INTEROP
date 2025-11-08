"""Batch import of IHE PAM HL7 messages from tests/exemples/Fichier_test_pam.

Features:
  - Creates/updates a FILE endpoint dedicated to PAM batch import.
  - Copies a limited number of .hl7 files (alphabetical) into the inbox.
  - Runs asynchronous file poller to ingest messages.
  - Reports processing stats and entity counts (patients / dossiers / venues / mouvements).
  - Lists first N errors with context for diagnosis.

Usage:
    PYTHONPATH=. python tools/import_pam_batch.py --limit 50
    PYTHONPATH=. python tools/import_pam_batch.py --limit 200 --reset-inbox

Arguments:
    --limit <N>          : Number of files to copy (default: 50)
    --source <PATH>      : Source directory (default: tests/exemples/Fichier_test_pam)
    --reset-inbox        : Clears inbox/archive/error directories before copying
    --chronological      : Sort source files by HL7 timestamp (MSH-7 or ZBE-2) instead of filename
    --relax-transitions  : Disable strict IHE PAM transition validation (imports historical sequences)
"""
import sys
import argparse
import asyncio
from pathlib import Path
import shutil
from typing import List, Optional, Tuple
import re, datetime, os

# Ensure project root import
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlmodel import select
from app.db_session_factory import session_factory
from app.models_shared import SystemEndpoint
from app.models_structure_fhir import GHTContext, EntiteJuridique
from app.models import Patient, Dossier, Venue, Mouvement
from app.services.file_poller import FilePollerService

PAM_ENDPOINT_NAME = "PAM Batch Inbox"


def _ensure_ght_ej(session) -> EntiteJuridique:
    """Ensure a GHT + EJ exist to attach imported messages (receiver context)."""
    ght = session.exec(select(GHTContext).where(GHTContext.code == "GHT-PAM")).first()
    if not ght:
        ght = GHTContext(name="GHT PAM", code="GHT-PAM", description="GHT pour import PAM", is_active=True)
        session.add(ght); session.commit(); session.refresh(ght)
        print(f"✓ GHT créé (code={ght.code})")
    ej = session.exec(select(EntiteJuridique).where(EntiteJuridique.finess_ej == "700PAM001")).first()
    if not ej:
        ej = EntiteJuridique(name="EJ PAM", finess_ej="700PAM001", ght_context_id=ght.id)
        session.add(ej); session.commit(); session.refresh(ej)
        print("✓ EJ créée")
    return ej


def _ensure_endpoint(session, inbox: Path, archive: Path, error: Path) -> SystemEndpoint:
    endpoint = session.exec(
        select(SystemEndpoint).where(SystemEndpoint.name == PAM_ENDPOINT_NAME)
    ).first()
    if not endpoint:
        endpoint = SystemEndpoint(
            name=PAM_ENDPOINT_NAME,
            kind="FILE",
            role="receiver",
            is_enabled=True,
            ght_context_id=session.exec(select(GHTContext).where(GHTContext.code == "GHT-PAM")).first().id,
            inbox_path=str(inbox),
            archive_path=str(archive),
            error_path=str(error),
            file_extensions=".hl7,.txt"
        )
        session.add(endpoint); session.commit(); session.refresh(endpoint)
        print(f"✓ Endpoint créé (id={endpoint.id})")
    else:
        changed = False
        for attr, val in [
            ("inbox_path", str(inbox)),
            ("archive_path", str(archive)),
            ("error_path", str(error)),
        ]:
            if getattr(endpoint, attr) != val:
                setattr(endpoint, attr, val); changed = True
        if not endpoint.is_enabled:
            endpoint.is_enabled = True; changed = True
        if changed:
            session.add(endpoint); session.commit()
            print("✓ Endpoint mis à jour")
        else:
            print("✓ Endpoint déjà configuré")
    return endpoint


_MSH_REGEX = re.compile(r"^MSH\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|(?P<dt>\d{14})")
_ZBE_REGEX = re.compile(r"^ZBE\|[^|]*\|(?P<dt>\d{14})")

def _extract_datetime(content: str) -> Optional[datetime.datetime]:
    """Extract HL7 datetime from MSH-7 (primary) or ZBE-2 (fallback)."""
    for line in content.splitlines():
        if line.startswith("MSH"):
            m = _MSH_REGEX.match(line)
            if m:
                try:
                    return datetime.datetime.strptime(m.group("dt"), "%Y%m%d%H%M%S")
                except Exception:
                    pass
        if line.startswith("ZBE"):
            z = _ZBE_REGEX.match(line)
            if z:
                try:
                    return datetime.datetime.strptime(z.group("dt"), "%Y%m%d%H%M%S")
                except Exception:
                    pass
    return None

def _copy_files(source_dir: Path, dest_dir: Path, limit: int, chronological: bool) -> List[Path]:
    files = [p for p in source_dir.iterdir() if p.is_file() and p.suffix.lower() == ".hl7"]
    if chronological:
        enriched: List[Tuple[Path, datetime.datetime]] = []
        for p in files:
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                content = ""
            dt = _extract_datetime(content) or datetime.datetime.max  # Place unknown at end
            enriched.append((p, dt))
        enriched.sort(key=lambda x: x[1])
        files = [e[0] for e in enriched]
    else:
        files = sorted(files)
    selected = files[:limit]
    for f in selected:
        shutil.copy(f, dest_dir / f.name)
    return selected


async def _scan(session):
    poller = FilePollerService(session)
    return await poller.scan_all_file_endpoints()


def _entity_counts(session):
    return {
        "patients": session.exec(select(Patient)).all().__len__(),
        "dossiers": session.exec(select(Dossier)).all().__len__(),
        "venues": session.exec(select(Venue)).all().__len__(),
        "mouvements": session.exec(select(Mouvement)).all().__len__(),
    }


def main():
    parser = argparse.ArgumentParser(description="Import batch messages PAM")
    parser.add_argument("--limit", type=int, default=50, help="Nombre de fichiers à importer")
    parser.add_argument("--source", type=str, default="tests/exemples/Fichier_test_pam", help="Répertoire source des messages PAM")
    parser.add_argument("--reset-inbox", action="store_true", help="Nettoie les dossiers avant import")
    parser.add_argument("--chronological", action="store_true", help="Trie les fichiers sur la date HL7 (MSH-7/ZBE-2)")
    parser.add_argument("--relax-transitions", action="store_true", help="Désactive validation stricte des transitions IHE PAM")
    args = parser.parse_args()

    source_dir = PROJECT_ROOT / args.source
    if not source_dir.exists():
        print(f"❌ Source introuvable: {source_dir}")
        return 2

    inbox = PROJECT_ROOT / "pam_inbox"
    archive = PROJECT_ROOT / "pam_archive"
    error = PROJECT_ROOT / "pam_error"
    for d in (inbox, archive, error):
        d.mkdir(exist_ok=True)
        if args.reset_inbox:
            for f in d.iterdir():
                if f.is_file():
                    f.unlink()
    if args.reset_inbox:
        print("✓ Inbox/Archive/Error nettoyés")

    with session_factory() as session:
        _ensure_ght_ej(session)
        _ensure_endpoint(session, inbox, archive, error)

        if args.relax_transitions:
            os.environ["PAM_RELAX_TRANSITIONS"] = "1"
        selected = _copy_files(source_dir, inbox, args.limit, chronological=args.chronological)
        print(f"✓ {len(selected)} fichiers copiés vers {inbox}")

        print("→ Scan & import…")
        stats = asyncio.run(_scan(session))

        print("\n=== Résultats import PAM ===")
        print(f"Endpoints scannés : {stats.get('endpoints_scanned')}\nFichiers traités   : {stats.get('files_processed')}\nMessages ADT       : {stats.get('adt_messages')}\nMessages MFN       : {stats.get('mfn_messages')}\nMessages inconnus  : {stats.get('unknown_messages')}")
        if stats.get('errors'):
            print(f"\n⚠️  Erreurs ({len(stats['errors'])}) – premières 10:")
            for e in stats['errors'][:10]:
                print(f"  - {e}")

        counts = _entity_counts(session)
        print("\n=== Entités importées (global DB) ===")
        for k, v in counts.items():
            print(f"  {k}: {v}")

        print("\nTerminé.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
