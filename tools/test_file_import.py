"""
Test script for file-based message import.

Demonstrates:
1. Creating a FILE endpoint
2. Copying the example MFN file to the inbox
3. Scanning and processing the file
"""
import sys
from pathlib import Path
import shutil
import asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db_session_factory import session_factory
from app.models_shared import SystemEndpoint
from app.models_structure_fhir import GHTContext
from app.services.file_poller import FilePollerService
from sqlmodel import select


def setup_file_endpoint():
    """Create or update a FILE endpoint for testing"""
    with session_factory() as session:
        # Find or create GHT context
        ght = session.exec(select(GHTContext).where(GHTContext.is_active == True)).first()
        if not ght:
            ght = GHTContext(
                name="GHT Test",
                code="TEST01",
                description="Test GHT for file import",
                is_active=True
            )
            session.add(ght)
            session.commit()
            session.refresh(ght)
            print(f"Created GHT context: {ght.name} (ID: {ght.id})")
        
        # Create test directories
        project_root = Path(__file__).parent.parent
        inbox_path = project_root / "test_inbox"
        archive_path = project_root / "test_archive"
        error_path = project_root / "test_error"
        
        inbox_path.mkdir(exist_ok=True)
        archive_path.mkdir(exist_ok=True)
        error_path.mkdir(exist_ok=True)
        
        # Find or create FILE endpoint
        endpoint = session.exec(
            select(SystemEndpoint).where(
                SystemEndpoint.kind == "FILE",
                SystemEndpoint.name == "Test File Inbox"
            )
        ).first()
        
        if not endpoint:
            endpoint = SystemEndpoint(
                name="Test File Inbox",
                kind="FILE",
                role="receiver",
                is_enabled=True,
                ght_context_id=ght.id,
                inbox_path=str(inbox_path),
                archive_path=str(archive_path),
                error_path=str(error_path),
                file_extensions=".txt,.hl7"
            )
            session.add(endpoint)
            session.commit()
            session.refresh(endpoint)
            print(f"Created FILE endpoint: {endpoint.name} (ID: {endpoint.id})")
        else:
            # Update paths
            endpoint.inbox_path = str(inbox_path)
            endpoint.archive_path = str(archive_path)
            endpoint.error_path = str(error_path)
            endpoint.is_enabled = True
            session.add(endpoint)
            session.commit()
            print(f"Updated FILE endpoint: {endpoint.name} (ID: {endpoint.id})")
        
        return {
            'endpoint_id': endpoint.id,
            'inbox_path': inbox_path,
            'archive_path': archive_path,
            'error_path': error_path,
            'ght_id': ght.id
        }


def copy_example_file(inbox_path: Path):
    """Copy the example MFN file to the inbox.

    Preference order for source file:
      1. tests/exemples/ExempleExtractionStructure.txt (user referenced)
      2. Doc/SpecStructureMFN/ExempleExtractionStructure.txt (legacy location)
    """
    project_root = Path(__file__).parent.parent
    source_tests = project_root / "tests" / "exemples" / "ExempleExtractionStructure.txt"
    source_legacy = project_root / "Doc" / "SpecStructureMFN" / "ExempleExtractionStructure.txt"
    source_file = source_tests if source_tests.exists() else source_legacy

    if not source_file.exists():
        print(f"ERROR: Source file not found: {source_file}")
        return False

    dest_file = inbox_path / "exemple_structure.txt"
    shutil.copy(source_file, dest_file)
    print(f"Copied {source_file.name} to {dest_file}")
    return True


async def _scan_async(session):
    poller = FilePollerService(session)
    return await poller.scan_all_file_endpoints()

def scan_and_process():
    """Scan file endpoints and process messages (sync wrapper)."""
    with session_factory() as session:
        print("\nScanning file endpoints (async)...")
        stats = asyncio.run(_scan_async(session))

        print("\n=== Processing Statistics ===")
        print(f"Endpoints scanned: {stats['endpoints_scanned']}")
        print(f"Files processed: {stats['files_processed']}")
        print(f"MFN messages: {stats['mfn_messages']}")
        print(f"ADT messages: {stats['adt_messages']}")
        print(f"Unknown messages: {stats['unknown_messages']}")

        if stats['errors']:
            print(f"\nErrors ({len(stats['errors'])}):")
            for error in stats['errors']:
                print(f"  - {error}")

        # Additional: count imported structure entities for diagnostics
        from app.models_structure import (
            EntiteGeographique, Pole, Service, UniteFonctionnelle,
            UniteHebergement, Chambre, Lit
        )
        counts = {}
        counts['eg'] = len(session.exec(select(EntiteGeographique)).all())
        counts['poles'] = len(session.exec(select(Pole)).all())
        counts['services'] = len(session.exec(select(Service)).all())
        counts['uf'] = len(session.exec(select(UniteFonctionnelle)).all())
        counts['uh'] = len(session.exec(select(UniteHebergement)).all())
        counts['ch'] = len(session.exec(select(Chambre)).all())
        counts['lits'] = len(session.exec(select(Lit)).all())
        print("\n=== Imported Structure Counts ===")
        for k, v in counts.items():
            print(f"  {k}: {v}")
        stats['structure_counts'] = counts
        return stats


def main():
    print("=== File-Based Message Import Test ===\n")
    
    # Step 1: Setup endpoint
    print("Step 1: Setting up FILE endpoint...")
    config = setup_file_endpoint()
    print(f"Inbox: {config['inbox_path']}")
    print(f"Archive: {config['archive_path']}")
    print(f"Error: {config['error_path']}")
    
    # Step 2: Copy example file
    print("\nStep 2: Copying example MFN file to inbox...")
    if not copy_example_file(config['inbox_path']):
        print("Failed to copy example file. Exiting.")
        return
    
    # Step 3: Scan and process
    print("\nStep 3: Processing files...")
    stats = scan_and_process()
    
    # Summary
    print("\n=== Summary ===")
    if stats['files_processed'] > 0:
        print("✓ File processing completed successfully")
        print(f"  Check database for imported structure data (GHT ID: {config['ght_id']})")
        print(f"  Processed files archived to: {config['archive_path']}")
    else:
        print("✗ No files were processed")
        print(f"  Check inbox: {config['inbox_path']}")


if __name__ == "__main__":
    main()
