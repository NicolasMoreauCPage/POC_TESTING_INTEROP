"""Test des endpoints de demo avec emission automatique Organization.

Verifie que les endpoints crees fonctionnent correctement avec le systeme
d'emission automatique FHIR et MFN.
"""
import asyncio
from datetime import datetime

from sqlmodel import Session, select

from app.db import engine
from app.models_structure_fhir import GHTContext, EntiteJuridique
from app.models_shared import MessageLog, SystemEndpoint
from app.services.entity_events_structure import register_structure_entity_events


async def test_endpoints_emission():
    """Test creation d'EJ avec endpoints de demo."""
    print("=" * 80)
    print("TEST: Endpoints Demo + Emission Organization")
    print("=" * 80)
    
    # Register event listeners
    register_structure_entity_events()
    
    with Session(engine) as session:
        # Get GHT context
        ght = session.exec(select(GHTContext).limit(1)).first()
        if not ght:
            print("Aucun GHT trouve - run tools/init_all.py first")
            return
        
        print(f"\n+ GHT: {ght.name} (id={ght.id})")
        
        # Check endpoints
        endpoints = session.exec(
            select(SystemEndpoint).where(SystemEndpoint.ght_context_id == ght.id)
        ).all()
        
        print(f"\n+ Endpoints configures: {len(endpoints)}")
        for ep in endpoints:
            status = "active" if ep.is_enabled else "disabled"
            if ep.kind == "mllp":
                print(f"  - {ep.name} ({ep.kind} {ep.role}): {ep.host}:{ep.port} [{status}]")
            elif ep.kind == "fhir":
                print(f"  - {ep.name} ({ep.kind} {ep.role}): {ep.base_url} [{status}]")
        
        if len(endpoints) == 0:
            print("\n! Aucun endpoint configure. Les messages seront generes mais pas envoyes.")
            print("  Pour creer les endpoints: python tools/init_all.py --reset")
        
        # Count messages before
        before_count = session.exec(select(MessageLog)).all()
        print(f"\n+ Messages existants: {len(before_count)}")
        
        # Create new EntiteJuridique
        ej = EntiteJuridique(
            ght_context_id=ght.id,
            name="Centre Hospitalier Test Endpoints",
            short_name="CHTE",
            finess_ej="990555444",
            siren="999888777",
            siret="99988877700012",
            start_date=datetime(2024, 1, 1),
        )
        session.add(ej)
        session.commit()
        
        print(f"\n+ EntiteJuridique creee: {ej.name}")
        print(f"  - ID: {ej.id}")
        print(f"  - FINESS: {ej.finess_ej}")
        print(f"  - SIREN: {ej.siren}")
        print("\nAttente emission asynchrone (3 secondes)...")
        
        # Wait for background emissions
        await asyncio.sleep(3)
        
        # Check MessageLog for new emissions
        with Session(engine) as s:
            last_id = before_count[-1].id if before_count else 0
            new_messages = s.exec(
                select(MessageLog).where(MessageLog.id > last_id)
            ).all()
            
            print(f"\n+ Messages emis: {len(new_messages)}")
            
            if len(new_messages) == 0:
                print("\n! Aucun message emis.")
                if len(endpoints) == 0:
                    print("  -> Cause: Pas d'endpoints configures")
                else:
                    print("  -> Verifier que les endpoints sont actifs (is_enabled=True)")
                    print("  -> Verifier les logs pour erreurs d'emission")
            else:
                # Group by endpoint
                by_endpoint = {}
                for msg in new_messages:
                    ep_id = msg.endpoint_id
                    if ep_id not in by_endpoint:
                        by_endpoint[ep_id] = []
                    by_endpoint[ep_id].append(msg)
                
                for ep_id, messages in by_endpoint.items():
                    endpoint = s.get(SystemEndpoint, ep_id)
                    if endpoint:
                        print(f"\n  Endpoint: {endpoint.name} ({endpoint.kind} {endpoint.role})")
                        for msg in messages:
                            status_icon = "+" if msg.status == "sent" else "!"
                            print(f"    {status_icon} {msg.kind} - {msg.status}")
                            if msg.kind == "FHIR":
                                import json
                                try:
                                    payload = json.loads(msg.payload)
                                    if payload.get("resourceType") == "Bundle":
                                        entry = payload.get("entry", [{}])[0]
                                        resource = entry.get("resource", {})
                                        print(f"       Resource: {resource.get('resourceType')}")
                                        print(f"       Name: {resource.get('name')}")
                                except:
                                    pass
                            elif msg.kind == "MLLP":
                                if msg.message_type:
                                    print(f"       Type: {msg.message_type}")
                                lines = msg.payload.split("\\r")
                                mfe = [l for l in lines if l.startswith("MFE")]
                                if mfe:
                                    fields = mfe[0].split("|")
                                    action = fields[1] if len(fields) > 1 else "?"
                                    print(f"       Action: {action}")
                            
                            if msg.status == "error":
                                print(f"       Error: {msg.ack_payload[:100]}")
                
                # Statistics
                fhir_count = sum(1 for m in new_messages if m.kind == "FHIR")
                mllp_count = sum(1 for m in new_messages if m.kind == "MLLP")
                sent_count = sum(1 for m in new_messages if m.status == "sent")
                error_count = sum(1 for m in new_messages if m.status == "error")
                
                print(f"\nStatistiques:")
                print(f"  - FHIR: {fhir_count}")
                print(f"  - MLLP: {mllp_count}")
                print(f"  - Sent: {sent_count}")
                print(f"  - Error: {error_count}")
    
    print("\n" + "="*80)
    print("Test termine")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_endpoints_emission())
