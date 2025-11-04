"""
Test complet : vérifier que chaque type de message IHE génère le même type en sortie.
Test scenarios: A01, A02, A03, A05, A21, A22, A31
"""
import asyncio
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.mllp import send_mllp
from app.db_session_factory import session_factory
from app.models_shared import MessageLog
from sqlmodel import select, desc
import re


# Test messages for different event types
TEST_MESSAGES = {
    "A01": """MSH|^~\\&|SEND_APP|SEND_FAC|RECV_APP|RECV_FAC|20251103090000||ADT^A01^ADT_A01|MSGA01|P|2.5
EVN|A01|20251103090000
PID|1||PAT001^^^HOSP^PI||DOE^JOHN||19800101|M
PV1|1|I|WARD1^BED1^01^HOSP||||^DOC^JOHN^^^DR|||||||||||VISIT001|||||||||||||||||||||||||20251103090000""",
    
    "A02": """MSH|^~\\&|SEND_APP|SEND_FAC|RECV_APP|RECV_FAC|20251103090100||ADT^A02^ADT_A02|MSGA02|P|2.5
EVN|A02|20251103090100
PID|1||PAT001^^^HOSP^PI||DOE^JOHN||19800101|M
PV1|1|I|WARD2^BED2^02^HOSP||||^DOC^JANE^^^DR|||||||||||VISIT001|||||||||||||||||||||||||20251103090100""",
    
    "A03": """MSH|^~\\&|SEND_APP|SEND_FAC|RECV_APP|RECV_FAC|20251103090200||ADT^A03^ADT_A03|MSGA03|P|2.5
EVN|A03|20251103090200
PID|1||PAT001^^^HOSP^PI||DOE^JOHN||19800101|M
PV1|1|I|WARD2^BED2^02^HOSP||||^DOC^JANE^^^DR|||||||||||VISIT001|||||||||||||||||||||||||20251103090200""",
    
    "A05": """MSH|^~\\&|SEND_APP|SEND_FAC|RECV_APP|RECV_FAC|20251103090300||ADT^A05^ADT_A05|MSGA05|P|2.5
EVN|A05|20251103090300
PID|1||PAT002^^^HOSP^PI||SMITH^JANE||19850315|F
PV1|1|E|EMERGENCY^001^01^HOSP||||^DOC^SMITH^^^DR|||||||||||VISIT002|||||||||||||||||||||||||20251103090300""",
    
    "A21": """MSH|^~\\&|SEND_APP|SEND_FAC|RECV_APP|RECV_FAC|20251103090400||ADT^A21^ADT_A21|MSGA21|P|2.5
EVN|A21|20251103090400
PID|1||PAT002^^^HOSP^PI||SMITH^JANE||19850315|F""",
    
    "A22": """MSH|^~\\&|SEND_APP|SEND_FAC|RECV_APP|RECV_FAC|20251103090500||ADT^A22^ADT_A22|MSGA22|P|2.5
EVN|A22|20251103090500
PID|1||PAT002^^^HOSP^PI||SMITH^JANE||19850315|F""",
    
    "A31": """MSH|^~\\&|SEND_APP|SEND_FAC|RECV_APP|RECV_FAC|20251103090600||ADT^A31^ADT_A31|MSGA31|P|2.5
EVN|A31|20251103090600
PID|1||PAT003^^^HOSP^PI||BROWN^MICHAEL||19750520|M""",
}


async def inject_message(event_type: str, message: str) -> bool:
    """Inject one test message via MLLP"""
    try:
        response = await send_mllp("127.0.0.1", 29000, message)
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def main():
    print("🧪 TEST COMPLET - Vérification préservation des types de messages")
    print("=" * 100)
    print()
    
    # Get count before
    with session_factory() as s:
        before_count = s.exec(select(MessageLog)).all()
        max_id_before = max([m.id for m in before_count]) if before_count else 0
    
    print(f"📊 Nombre de messages avant test: {len(before_count)} (max ID={max_id_before})")
    print()
    
    # Inject all test messages
    results = {}
    for event_type, message in TEST_MESSAGES.items():
        print(f"📨 Injection {event_type}...", end=" ")
        success = await inject_message(event_type, message)
        if success:
            print("✅")
        results[event_type] = success
    
    print()
    print("⏳ Attente traitement et émission automatique (5s)...")
    time.sleep(5)
    
    # Check results
    print()
    print("📊 RÉSULTATS:")
    print("=" * 100)
    
    with session_factory() as s:
        # Get new messages
        new_messages = s.exec(
            select(MessageLog)
            .where(MessageLog.id > max_id_before)
            .order_by(MessageLog.id)
        ).all()
        
        # Group by event type
        inbound = {}
        outbound = {}
        
        for m in new_messages:
            match = re.search(r'\|\|ADT\^([A-Z0-9]+)', m.payload or '')
            if match:
                event_code = match.group(1)
                
                if m.direction == "in":
                    inbound[event_code] = inbound.get(event_code, 0) + 1
                else:
                    outbound[event_code] = outbound.get(event_code, 0) + 1
        
        print(f"\n{'Type':6} | {'Reçu':5} | {'Émis':5} | Résultat")
        print("-" * 50)
        
        all_ok = True
        for event_type in TEST_MESSAGES.keys():
            received = inbound.get(event_type, 0)
            emitted = outbound.get(event_type, 0)
            
            # Check if type is preserved
            if received > 0 and emitted > 0:
                status = "✅ OK"
            elif received > 0 and emitted == 0:
                status = "⚠️  Pas d'émission"
                all_ok = False
            elif received == 0:
                status = "❌ Pas reçu"
                all_ok = False
            else:
                status = "?"
                all_ok = False
            
            print(f"{event_type:6} | {received:5} | {emitted:5} | {status}")
        
        print()
        if all_ok:
            print("🎉" * 50)
            print("✅ TOUS LES TYPES DE MESSAGES SONT PRÉSERVÉS !")
            print("🎉" * 50)
        else:
            print("⚠️  Certains types n'ont pas été correctement traités")
        
        return all_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
