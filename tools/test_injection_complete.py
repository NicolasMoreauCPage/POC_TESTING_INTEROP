"""
Test final: injecter un message A01 via MLLP et vérifier l'émission automatique.
"""
import time
from sqlmodel import Session, select
from app.db import engine
from app.models_endpoints import MessageLog

# Exemple de message A01 simple
HL7_A01 = """MSH|^~\\&|SEND_APP|SEND_FAC|RECV_APP|RECV_FAC|20251103080000||ADT^A01^ADT_A01|MSG12345|P|2.5
EVN|A01|20251103080000
PID|1||TESTPAT123^^^HOSP^PI||TESTFAM^TESTGIVEN||19850315|M
PV1|1|I|0001^001^01^HOSP||||^SMITH^JOHN^^^DR|||||||||||12345678|||||||||||||||||||||||||20251103080000"""

print("🧪 TEST FINAL - Injection message A01 + Vérification émission")
print("=" * 80)

# Count messages before
with Session(engine) as s:
    before_in = len(s.exec(select(MessageLog).where(MessageLog.direction == "in")).all())
    before_out = len(s.exec(select(MessageLog).where(MessageLog.direction == "out")).all())
    
    print(f"\n📊 AVANT injection:")
    print(f"   Messages IN: {before_in}")
    print(f"   Messages OUT: {before_out}")

# Inject via tools/post_hl7.py
print(f"\n📨 Injection message A01 vers MLLP (127.0.0.1:29000)...")
print(f"   Patient: TESTFAM TESTGIVEN (ID: TESTPAT123)")
print(f"   Event: A01 (admission)")

import subprocess
try:
    # Use post_hl7.py tool
    result = subprocess.run(
        [
            ".venv/bin/python",
            "tools/post_hl7.py",
            "--host", "127.0.0.1",
            "--port", "29000",
            "--message", HL7_A01.replace("\n", "\r")
        ],
        capture_output=True,
        text=True,
        timeout=10,
        cwd="/home/nico/Travail/Fhir_MedBridgeData/MedData_Bridge"
    )
    
    if result.returncode == 0:
        print(f"   ✅ Injection réussie!")
        if result.stdout:
            print(f"   ACK: {result.stdout[:100]}")
    else:
        print(f"   ⚠️  Erreur injection: {result.stderr[:200]}")
except Exception as e:
    print(f"   ❌ Exception: {e}")

# Wait for processing and emission
print(f"\n⏳ Attente traitement + émission automatique (5s)...")
time.sleep(5)

# Count messages after
with Session(engine) as s:
    after_in = len(s.exec(select(MessageLog).where(MessageLog.direction == "in")).all())
    after_out = len(s.exec(select(MessageLog).where(MessageLog.direction == "out")).all())
    
    new_in = after_in - before_in
    new_out = after_out - before_out
    
    print(f"\n📊 APRÈS injection:")
    print(f"   Messages IN: {after_in} (+{new_in})")
    print(f"   Messages OUT: {after_out} (+{new_out})")
    
    if new_in > 0 and new_out > new_in:
        auto_emitted = new_out - new_in
        print(f"\n" + "🎉" * 40)
        print(f"✅ ÉMISSION AUTOMATIQUE FONCTIONNE!")
        print(f"   Messages reçus: {new_in}")
        print(f"   Messages auto-émis: {auto_emitted}")
        print("🎉" * 40)
        
        # Get latest messages
        msg_in = s.exec(
            select(MessageLog)
            .where(MessageLog.direction == "in")
            .order_by(MessageLog.id.desc())
        ).first()
        
        msgs_out = s.exec(
            select(MessageLog)
            .where(MessageLog.direction == "out")
            .order_by(MessageLog.id.desc())
        ).all()[:new_out]
        
        print(f"\n📥 Message entrant (ID={msg_in.id}):")
        print(f"   Type: {msg_in.message_type}")
        print(f"   Status: {msg_in.status}")
        
        print(f"\n📤 Messages sortants auto-émis:")
        for msg in msgs_out:
            print(f"   • ID={msg.id} | Endpoint={msg.endpoint_id} | Status={msg.status} | Type={msg.message_type}")
        
        # Compare
        print(f"\n🔍 COMPARAISON:")
        if msg_in.payload:
            in_lines = [l for l in msg_in.payload.split("\r") if l]
            print(f"\n   Message ENTRANT (extrait):")
            for line in in_lines[:3]:
                print(f"      {line[:80]}")
        
        auto_msg = next((m for m in msgs_out if m.endpoint_id == 3), None)
        if auto_msg and auto_msg.payload:
            out_lines = [l for l in auto_msg.payload.split("\r") if l]
            print(f"\n   Message AUTO-ÉMIS (endpoint 3, extrait):")
            for line in out_lines[:3]:
                print(f"      {line[:80]}")
    else:
        print(f"\n⚠️  Résultat inattendu:")
        print(f"   • new_in={new_in}, new_out={new_out}")
        if new_in == 0:
            print(f"   ❌ Aucun message reçu (serveur MLLP ne répond pas?)")
        elif new_out == 0:
            print(f"   ❌ Aucun message émis (event listeners inactifs?)")
