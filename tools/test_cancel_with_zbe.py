#!/usr/bin/env python3
"""
Test des messages d'annulation avec segment ZBE-1
"""
import asyncio
import time
import httpx
from sqlmodel import Session, create_engine, select

from app.db import engine as app_engine
from app.models_shared import MessageLog
from app.models import Mouvement

async def inject_message(message: str) -> bool:
    """Injecte un message via MLLP direct"""
    try:
        from app.services.mllp import send_mllp
        ack = await send_mllp("127.0.0.1", 29000, message)
        return "AA" in ack  # ACK accepté
    except Exception as e:
        print(f"❌ Erreur injection: {e}")
        return False

async def main():
    print("🧪 TEST ANNULATIONS AVEC ZBE-1")
    print("=" * 70)
    print()
    
    # 1. Créer une admission (A01)
    print("📨 Étape 1: Créer une admission...")
    msg_a01 = """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103120000||ADT^A01^ADT_A01|MSG_A01|P|2.5
EVN|A01|20251103120000
PID|1||TESTZBE001^^^HOSP^PI||TEST^PATIENT||19900101|M
PV1|1|I|WARD1^BED1^01^HOSP||||^DR^SMITH^^^MD|||||||||||VIS_TEST|||||||||||||||||||||||||20251103120000"""
    
    success = await inject_message(msg_a01)
    if not success:
        print("❌ Échec injection A01")
        return
    print("✅ A01 injecté")
    
    time.sleep(2)
    
    # Récupérer l'ID du mouvement créé
    with Session(app_engine) as session:
        mouvement = session.exec(
            select(Mouvement)
            .where(Mouvement.type == "ADT^A01")
            .order_by(Mouvement.id.desc())
        ).first()
        
        if not mouvement:
            print("❌ Mouvement A01 non trouvé")
            return
        
        movement_seq = mouvement.mouvement_seq
        print(f"✅ Mouvement créé: seq={movement_seq}, id={mouvement.id}")
    
    print()
    print("📨 Étape 2: Annuler l'admission avec ZBE-1...")
    
    # 2. Annuler avec A11 + ZBE-1 pointant vers le movement_seq
    msg_a11 = f"""MSH|^~\\&|SEND|FAC|RECV|FAC|20251103120100||ADT^A11^ADT_A11|MSG_A11|P|2.5
EVN|A11|20251103120100
PID|1||TESTZBE001^^^HOSP^PI||TEST^PATIENT||19900101|M
PV1|1|I|WARD1^BED1^01^HOSP||||^DR^SMITH^^^MD|||||||||||VIS_TEST|||||||||||||||||||||||||20251103120100
ZBE|{movement_seq}^HOSP^1.2.250.1.213.1.4.2^ISO|20251103120000||CANCEL|Y"""
    
    success = await inject_message(msg_a11)
    if not success:
        print("❌ Échec injection A11")
        return
    print(f"✅ A11 injecté avec ZBE-1={movement_seq}")
    
    time.sleep(2)
    
    # 3. Vérifier résultats
    print()
    print("📊 RÉSULTATS:")
    print("=" * 70)
    
    with Session(app_engine) as session:
        # Compter mouvements par type
        mouvements = session.exec(
            select(Mouvement)
            .where(Mouvement.mouvement_seq >= movement_seq)
            .order_by(Mouvement.mouvement_seq)
        ).all()
        
        print(f"\n📋 Mouvements créés:")
        for m in mouvements:
            status_icon = "❌" if m.status == "cancelled" else "✅"
            print(f"  {status_icon} seq={m.mouvement_seq} | type={m.type} | status={m.status} | movement_type={m.movement_type}")
        
        # Compter messages émis
        messages = session.exec(
            select(MessageLog)
            .where(MessageLog.direction == "out")
            .order_by(MessageLog.id.desc())
        ).all()[:5]
        
        print(f"\n📤 Derniers messages émis:")
        for msg in messages:
            print(f"  • {msg.kind} | status={msg.status}")
            if "ADT^A" in (msg.payload or ""):
                import re
                match = re.search(r'ADT\^(A\d+)', msg.payload)
                if match:
                    print(f"    Type: ADT^{match.group(1)}")
    
    print()
    print("=" * 70)
    print("✅ Test terminé")

if __name__ == "__main__":
    asyncio.run(main())
