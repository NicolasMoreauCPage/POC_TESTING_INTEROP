"""
Script de test pour vérifier l'émission automatique de messages.

Ce script crée manuellement des entités et vérifie si des messages sont émis.
"""

import asyncio
import time
from sqlmodel import Session, select
from app.db import engine
from app.models import Patient, Dossier, Venue, Mouvement
from app.models_endpoints import MessageLog
from app.models_shared import SystemEndpoint
from app.services.entity_events import register_entity_events

async def main():
    print("🧪 TEST MANUEL D'ÉMISSION AUTOMATIQUE")
    print("=" * 80)
    
    # Register event listeners
    print("\n1️⃣  Enregistrement des event listeners...")
    register_entity_events()
    print("   ✓ Event listeners enregistrés")
    
    # Check senders
    with Session(engine) as s:
        senders = s.exec(select(SystemEndpoint).where(SystemEndpoint.role == "sender")).all()
        print(f"\n2️⃣  Endpoints 'sender' disponibles: {len(senders)}")
        for sender in senders:
            print(f"   • ID={sender.id} | {sender.name} | {sender.host}:{sender.port}")
    
    # Count messages before
    with Session(engine) as s:
        before_count = len(s.exec(select(MessageLog).where(MessageLog.direction == "out")).all())
        print(f"\n3️⃣  Messages OUT avant test: {before_count}")
    
    # Create a patient
    print(f"\n4️⃣  Création d'un patient de test...")
    with Session(engine) as s:
        patient = Patient(
            identifier=f"TEST_MANUAL_{int(time.time())}",
            external_id=f"TEST_MANUAL_{int(time.time())}",
            family="MANUALTEST",
            given="EmissionTest",
            birth_date="1995-05-15",
            gender="F"
        )
        s.add(patient)
        s.commit()  # This should trigger after_commit
        
        patient_id = patient.id
        print(f"   ✓ Patient créé: id={patient_id}, {patient.family} {patient.given}")
    
    # Wait for background emission
    print(f"\n5️⃣  Attente émission en arrière-plan (5s)...")
    await asyncio.sleep(5)
    
    # Check messages after
    with Session(engine) as s:
        after_count = len(s.exec(select(MessageLog).where(MessageLog.direction == "out")).all())
        new_messages = after_count - before_count
        
        print(f"\n6️⃣  Messages OUT après test: {after_count}")
        print(f"   🆕 Nouveaux messages: {new_messages}")
        
        if new_messages > 0:
            print("\n" + "🎉" * 30)
            print("✅ ÉMISSION AUTOMATIQUE FONCTIONNE!")
            print("🎉" * 30)
            
            # Show new messages
            new_logs = s.exec(
                select(MessageLog)
                .where(MessageLog.direction == "out")
                .order_by(MessageLog.id.desc())
            ).all()[:new_messages]
            
            print(f"\n📤 Messages émis:")
            for msg in new_logs:
                print(f"\n   Message ID={msg.id}:")
                print(f"   • Type: {msg.message_type}")
                print(f"   • Status: {msg.status}")
                print(f"   • Endpoint: {msg.endpoint_id}")
                print(f"   • Taille: {len(msg.payload) if msg.payload else 0} bytes")
                
                if msg.payload:
                    lines = msg.payload.split("\r")
                    pid = next((l for l in lines if l.startswith("PID")), "")
                    if pid:
                        fields = pid.split("|")
                        if len(fields) > 5:
                            print(f"   • Patient: {fields[5]}")
        else:
            print("\n❌ AUCUN MESSAGE ÉMIS")
            print("\n💡 Raisons possibles:")
            print("   • Event listeners pas encore actifs dans le serveur FastAPI")
            print("   • Ce script utilise sa propre instance d'engine")
            print("   • Les listeners doivent être enregistrés AU DÉMARRAGE du serveur")

if __name__ == "__main__":
    asyncio.run(main())
