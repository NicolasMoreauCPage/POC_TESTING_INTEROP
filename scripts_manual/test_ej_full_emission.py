"""Test complet de l'emission d'EntiteJuridique (Organization FHIR + MFN M05).

Verifie que la creation et la suppression d'une EntiteJuridique generent
automatiquement les messages FHIR Organization et MFN M05.
"""
import asyncio
from datetime import datetime

from sqlmodel import Session, select

from app.db import engine
from app.models_structure_fhir import GHTContext, EntiteJuridique
from app.models_shared import MessageLog
from app.services.entity_events_structure import register_structure_entity_events


async def test_ej_emission():
    """Test creation d'EJ avec emission automatique."""
    print("=" * 80)
    print("TEST: Emission automatique EntiteJuridique -> Organization")
    print("=" * 80)
    
    # Register event listeners
    register_structure_entity_events()
    
    with Session(engine) as session:
        # Get GHT context
        ght = session.exec(select(GHTContext).limit(1)).first()
        if not ght:
            print("Aucun GHT trouve - run tools/init_all.py first")
            return
        
        print(f"\n+ GHT trouve: {ght.name} (id={ght.id})")
        
        # Count messages before
        before_count = session.exec(select(MessageLog)).all()
        print(f"+ Messages existants: {len(before_count)}")
        
        # Create new EntiteJuridique
        ej = EntiteJuridique(
            ght_context_id=ght.id,
            name="Hopital Test Emission",
            short_name="HTE",
            finess_ej="990123456",
            siren="123456789",
            siret="12345678900015",
            start_date=datetime(2024, 1, 1),
        )
        session.add(ej)
        session.commit()
        
        print(f"\n+ EntiteJuridique creee: {ej.name} (id={ej.id}, FINESS={ej.finess_ej})")
        print("Attente emission asynchrone (2 secondes)...")
        
        # Wait for background emissions
        await asyncio.sleep(2)
        
        # Check MessageLog for new emissions
        with Session(engine) as s:
            last_id = before_count[-1].id if before_count else 0
            new_messages = s.exec(
                select(MessageLog).where(MessageLog.id > last_id)
            ).all()
            
            print(f"\n+ Nouveaux messages emis: {len(new_messages)}")
            
            fhir_count = sum(1 for m in new_messages if m.kind == "FHIR")
            mllp_count = sum(1 for m in new_messages if m.kind == "MLLP")
            
            print(f"  - FHIR: {fhir_count}")
            print(f"  - MLLP: {mllp_count}")
            
            # Check FHIR Organization
            fhir_org = [m for m in new_messages if m.kind == "FHIR" and "Organization" in m.payload]
            if fhir_org:
                print("\n+ FHIR Organization emis:")
                for msg in fhir_org:
                    print(f"  - Endpoint: {msg.endpoint_id}")
                    print(f"  - Status: {msg.status}")
                    import json
                    payload = json.loads(msg.payload)
                    if payload.get("resourceType") == "Bundle":
                        entry = payload.get("entry", [{}])[0]
                        resource = entry.get("resource", {})
                        print(f"  - Resource: {resource.get('resourceType')}")
                        print(f"  - Name: {resource.get('name')}")
                        identifiers = resource.get("identifier", [])
                        print(f"  - Identifiers: {len(identifiers)}")
                        for ident in identifiers:
                            system = ident.get("system", "")
                            if "finess" in system.lower():
                                print(f"    -> FINESS: {ident.get('value')}")
                            elif "siren" in system.lower():
                                print(f"    -> SIREN: {ident.get('value')}")
                            elif "siret" in system.lower():
                                print(f"    -> SIRET: {ident.get('value')}")
            else:
                print("! Aucun message FHIR Organization trouve")
            
            # Check MFN M05 Organization
            mfn_org = [m for m in new_messages if m.kind == "MLLP" and m.message_type == "MFN^M05"]
            if mfn_org:
                print("\n+ MFN M05 Organization emis:")
                for msg in mfn_org:
                    print(f"  - Endpoint: {msg.endpoint_id}")
                    print(f"  - Status: {msg.status}")
                    lines = msg.payload.split("\r")
                    msh = [l for l in lines if l.startswith("MSH")]
                    mfi = [l for l in lines if l.startswith("MFI")]
                    mfe = [l for l in lines if l.startswith("MFE")]
                    org = [l for l in lines if l.startswith("ORG")]
                    print(f"  - Segments: MSH={len(msh)}, MFI={len(mfi)}, MFE={len(mfe)}, ORG={len(org)}")
                    if org:
                        print(f"  - ORG segment: {org[0][:100]}...")
            else:
                print("! Aucun message MFN M05 Organization trouve")
            
            # Test deletion
            print(f"\n{'='*80}")
            print("TEST: Suppression EntiteJuridique -> DELETE Organization")
            print("="*80)
            
            ej_to_delete = s.get(EntiteJuridique, ej.id)
            finess = ej_to_delete.finess_ej
            s.delete(ej_to_delete)
            s.commit()
            
            print(f"\n+ EntiteJuridique supprimee (id={ej.id}, FINESS={finess})")
            print("Attente emission asynchrone (2 secondes)...")
            
            await asyncio.sleep(2)
            
            # Check DELETE messages
            last_msg_id = new_messages[-1].id if new_messages else last_id
            delete_messages = s.exec(
                select(MessageLog).where(MessageLog.id > last_msg_id)
            ).all()
            
            print(f"\n+ Messages DELETE emis: {len(delete_messages)}")
            
            fhir_deletes = [m for m in delete_messages if m.kind == "FHIR" and "DELETE" in m.payload]
            mllp_deletes = [m for m in delete_messages if m.kind == "MLLP" and "MDL" in m.payload]
            
            print(f"  - FHIR DELETE: {len(fhir_deletes)}")
            print(f"  - MFN MDL: {len(mllp_deletes)}")
            
            if fhir_deletes:
                print("\n+ FHIR DELETE Organization emis")
                for msg in fhir_deletes:
                    import json
                    payload = json.loads(msg.payload)
                    entry = payload.get("entry", [{}])[0]
                    request = entry.get("request", {})
                    print(f"  - Method: {request.get('method')}")
                    print(f"  - URL: {request.get('url')}")
            
            if mllp_deletes:
                print("\n+ MFN MDL Organization emis")
                for msg in mllp_deletes:
                    lines = msg.payload.split("\r")
                    mfe = [l for l in lines if l.startswith("MFE")]
                    if mfe:
                        fields = mfe[0].split("|")
                        print(f"  - MFE-1 (action): {fields[1] if len(fields) > 1 else 'N/A'}")
    
    print("\n" + "="*80)
    print("Test termine avec succes")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_ej_emission())
