"""Test manuel du file polling"""
import asyncio
from sqlmodel import Session
from app.db import engine
from app.services.file_poller import FilePollerService

async def test():
    with Session(engine) as s:
        poller = FilePollerService(s)
        result = await poller.scan_all_file_endpoints()
        
        print("=== Résultat du polling ===")
        print(f"Endpoints scannés: {result['endpoints_scanned']}")
        print(f"Fichiers traités: {result['files_processed']}")
        print(f"Messages MFN: {result['mfn_messages']}")
        print(f"Messages ADT: {result['adt_messages']}")
        print(f"Messages inconnus: {result['unknown_messages']}")
        
        if result['errors']:
            print("\nErreurs:")
            for err in result['errors']:
                print(f"  - {err}")
        
        print("\n=== Vérification des répertoires ===")
        import os
        inbox = r"C:\Travail\Fhir_Tester\File_Input\MFN\In"
        archive = r"C:\Travail\Fhir_Tester\File_Input\MFN\Archive"
        error = r"C:\Travail\Fhir_Tester\File_Input\MFN\In\Err"
        
        print(f"Inbox: {len([f for f in os.listdir(inbox) if os.path.isfile(os.path.join(inbox, f))])} fichier(s)")
        if os.path.exists(archive):
            print(f"Archive: {len([f for f in os.listdir(archive) if os.path.isfile(os.path.join(archive, f))])} fichier(s)")
        if os.path.exists(error):
            print(f"Error: {len([f for f in os.listdir(error) if os.path.isfile(os.path.join(error, f))])} fichier(s)")

asyncio.run(test())
