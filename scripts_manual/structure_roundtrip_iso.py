"""Structure roundtrip ISO test (MFN + FHIR).

1. Wipe (optional) / reuse existing DB state.
2. Import example MFN file via tools/test_file_import logic.
3. Export MFN with collapse_virtual=True and compare counts to source.
4. Export FHIR bundle with collapse_virtual=True and print summary.
"""
import sys, json
from pathlib import Path
import shutil
import asyncio
from sqlmodel import select

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db_session_factory import session_factory
from app.services.mfn_structure import generate_mfn_message
from app.services.fhir_structure_export import generate_fhir_bundle_structure
from app.services.file_poller import FilePollerService
from app.models_shared import SystemEndpoint
from app.models_structure_fhir import GHTContext
from app.models_structure import EntiteGeographique, Pole, Service

SOURCE_FILE = Path(__file__).parent.parent / "tests" / "exemples" / "ExempleExtractionStructure.txt"

def _setup_endpoint(session):
    ght = session.exec(select(GHTContext).where(GHTContext.is_active == True)).first()
    if not ght:
        ght = GHTContext(name="GHT ISO", code="GHT-ISO", is_active=True)
        session.add(ght); session.commit(); session.refresh(ght)
    inbox = Path("test_inbox"); archive = Path("test_archive"); error = Path("test_error")
    for p in (inbox, archive, error): p.mkdir(exist_ok=True)
    ep = session.exec(select(SystemEndpoint).where(SystemEndpoint.name == "ISO File Inbox")).first()
    if not ep:
        ep = SystemEndpoint(name="ISO File Inbox", kind="FILE", role="receiver", is_enabled=True,
                            ght_context_id=ght.id, inbox_path=str(inbox), archive_path=str(archive),
                            error_path=str(error), file_extensions=".txt,.hl7")
        session.add(ep); session.commit(); session.refresh(ep)
    return ep

async def _scan(session):
    poller = FilePollerService(session)
    return await poller.scan_all_file_endpoints()

def import_source():
    with session_factory() as session:
        ep = _setup_endpoint(session)
        dest = Path(ep.inbox_path) / "exemple_structure.txt"
        shutil.copy(SOURCE_FILE, dest)
        stats = asyncio.run(_scan(session))
        return stats

def _count_loc_types(source_text: str):
    counts = {}
    for t in ["M","ETBL_GRPQ","P","D","UF","UH","CH","LIT"]:
        key = f"LOC|^^^^^{t}^^^^"
        counts[t] = sum(1 for line in source_text.splitlines() if line.startswith(key))
    return counts

def export_mfn_iso():
    with session_factory() as session:
        mfn = generate_mfn_message(session, collapse_virtual=True)
        seg_counts = {"MFE": sum(1 for l in mfn.splitlines() if l.startswith("MFE|"))}
        # Recompute LOC type counts
        loc_counts = {}
        for t in ["M","ETBL_GRPQ","P","D"]:
            loc_counts[t] = sum(1 for l in mfn.splitlines() if l.startswith(f"LOC|^^^^^{t}^^^^"))
        return mfn, seg_counts, loc_counts

def export_fhir_iso():
    with session_factory() as session:
        bundle = generate_fhir_bundle_structure(session, collapse_virtual=True)
        return bundle

def main():
    if not SOURCE_FILE.exists():
        print("Source MFN file missing", SOURCE_FILE); return 1
    source_text = SOURCE_FILE.read_text(encoding="utf-8")
    src_counts = _count_loc_types(source_text)
    print("Source LOC counts:", src_counts)
    stats = import_source()
    print("Import stats:", stats)
    mfn, seg_counts, loc_counts = export_mfn_iso()
    print("ISO MFN LOC counts:", loc_counts)
    bundle = export_fhir_iso()
    print("FHIR bundle resources:", len(bundle.get("entry", [])))
    # Simple ISO assertion: counts for P must be 0 and D matches source
    iso_ok = (loc_counts.get("D") == src_counts.get("D") and loc_counts.get("P") == 0)
    print("ISO status:", "OK" if iso_ok else "NOT-ISO")
    # Write artifacts
    Path("roundtrip_iso_mfn.txt").write_text(mfn, encoding="utf-8")
    Path("roundtrip_iso_fhir.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return 0 if iso_ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
