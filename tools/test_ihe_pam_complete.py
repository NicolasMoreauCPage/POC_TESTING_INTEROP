"""
Test complet des événements IHE PAM implémentés.
Teste l'injection de tous les types de messages et vérifie l'émission automatique.
"""
import asyncio
import time
from pathlib import Path
import sys
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.mllp import send_mllp
from app.db_session_factory import session_factory
from app.models_shared import MessageLog
from sqlmodel import select, desc
import re


def add_zbe_segment_to_message(message: str, trigger: str, movement_seq: int) -> str:
    """
    Ajoute un segment ZBE conforme IHE PAM à un message HL7 existant.
    
    IMPORTANT : Le segment ZBE est UNIQUEMENT pour les messages de MOUVEMENTS,
    PAS pour les messages d'identité (A28, A31, A40, A47).
    
    Selon IHE PAM France :
    - Messages de mouvements (avec ZBE) : A01-A07, A11-A13, A21-A23, A38, A52-A55
    - Messages d'identité (SANS ZBE) : A28, A31, A40, A47
    """
    # Messages d'identité : PAS de segment ZBE
    if trigger in ["A28", "A31", "A40", "A47"]:
        return message  # Retourner le message inchangé
    
    # Messages de mouvements : segment ZBE obligatoire
    now = datetime.now()
    movement_dt = (now + timedelta(minutes=5)).strftime("%Y%m%d%H%M%S")
    
    # Déterminer l'action ZBE-4 selon le trigger
    if trigger in ["A11", "A12", "A13", "A23", "A38", "A52", "A53", "A55"]:
        action_type = "CANCEL"
        cancel_flag = "Y"
        mode = "C"
        origin_map = {
            "A11": "A01", "A23": "A01", "A38": "A05",
            "A12": "A02", "A13": "A03",
            "A52": "A21", "A53": "A22", "A55": "A54"
        }
        origin_event = origin_map.get(trigger, "")
    elif trigger in ["A06", "A07"]:
        action_type = "UPDATE"
        cancel_flag = "N"
        origin_event = ""
        mode = "HMS"
    else:
        action_type = "INSERT"
        cancel_flag = "N"
        origin_event = ""
        mode = "L" if trigger in ["A21", "A52"] else "HMS"
    
    uf_code = "NEURO" if trigger in ["A02", "A12"] else "CARDIO"
    
    zbe = (
        f"ZBE|{movement_seq}^MOVEMENT^1.2.250.1.213.1.1.9^ISO|"
        f"{movement_dt}||{action_type}|{cancel_flag}|{origin_event}|"
        f"^^^^^^UF^^^{uf_code}||{mode}"
    )
    
    # Ajouter le segment ZBE à la fin du message (après le dernier segment)
    return message.strip() + "\r" + zbe


# Messages de test pour tous les événements IHE PAM implémentés
IHE_PAM_MESSAGES = {
    # Admissions/Enregistrements
    "A01": """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103100000||ADT^A01^ADT_A01|MSG_A01|P|2.5
EVN|A01|20251103100000
PID|1||PAT001^^^HOSP^PI||MARTIN^PIERRE||19800101|M
PV1|1|I|WARD1^BED1^01^HOSP||||^DR^SMITH^^^MD|||||||||||VIS001|||||||||||||||||||||||||20251103100000""",
    
    "A04": """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103100100||ADT^A04^ADT_A04|MSG_A04|P|2.5
EVN|A04|20251103100100
PID|1||PAT002^^^HOSP^PI||DUPONT^MARIE||19850315|F""",
    
    "A05": """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103100200||ADT^A05^ADT_A05|MSG_A05|P|2.5
EVN|A05|20251103100200
PID|1||PAT003^^^HOSP^PI||BERNARD^JEAN||19750520|M
PV1|1|I|WARD2^BED2^02^HOSP||||^DR^JONES^^^MD|||||||||||VIS003|||||||||||||||||||||||||20251103100200""",
    
    # Changements de classe
    "A06": """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103100300||ADT^A06^ADT_A06|MSG_A06|P|2.5
EVN|A06|20251103100300
PID|1||PAT001^^^HOSP^PI||MARTIN^PIERRE||19800101|M
PV1|1|O|WARD1^BED1^01^HOSP||||^DR^SMITH^^^MD|||||||||||VIS001|||||||||||||||||||||||||20251103100300""",
    
    "A07": """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103100400||ADT^A07^ADT_A07|MSG_A07|P|2.5
EVN|A07|20251103100400
PID|1||PAT001^^^HOSP^PI||MARTIN^PIERRE||19800101|M
PV1|1|I|WARD1^BED1^01^HOSP||||^DR^SMITH^^^MD|||||||||||VIS001|||||||||||||||||||||||||20251103100400""",
    
    # Transferts
    "A02": """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103100500||ADT^A02^ADT_A02|MSG_A02|P|2.5
EVN|A02|20251103100500
PID|1||PAT001^^^HOSP^PI||MARTIN^PIERRE||19800101|M
PV1|1|I|WARD3^BED3^03^HOSP||||^DR^BROWN^^^MD|||||||||||VIS001|||||||||||||||||||||||||20251103100500""",
    
    # Sorties
    "A03": """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103100600||ADT^A03^ADT_A03|MSG_A03|P|2.5
EVN|A03|20251103100600
PID|1||PAT001^^^HOSP^PI||MARTIN^PIERRE||19800101|M
PV1|1|I|WARD3^BED3^03^HOSP||||^DR^BROWN^^^MD|||||||||||VIS001|||||||||||||||||||||||||20251103100600""",
    
    # Annulations
    "A11": """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103100700||ADT^A11^ADT_A11|MSG_A11|P|2.5
EVN|A11|20251103100700
PID|1||PAT001^^^HOSP^PI||MARTIN^PIERRE||19800101|M
PV1|1|I|WARD1^BED1^01^HOSP||||^DR^SMITH^^^MD|||||||||||VIS001|||||||||||||||||||||||||20251103100700""",
    
    "A12": """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103100800||ADT^A12^ADT_A12|MSG_A12|P|2.5
EVN|A12|20251103100800
PID|1||PAT001^^^HOSP^PI||MARTIN^PIERRE||19800101|M
PV1|1|I|WARD1^BED1^01^HOSP||||^DR^SMITH^^^MD|||||||||||VIS001|||||||||||||||||||||||||20251103100800""",
    
    "A13": """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103100900||ADT^A13^ADT_A13|MSG_A13|P|2.5
EVN|A13|20251103100900
PID|1||PAT001^^^HOSP^PI||MARTIN^PIERRE||19800101|M
PV1|1|I|WARD1^BED1^01^HOSP||||^DR^SMITH^^^MD|||||||||||VIS001|||||||||||||||||||||||||20251103100900""",
    
    # Permissions (Leave of absence)
    "A21": """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103101000||ADT^A21^ADT_A21|MSG_A21|P|2.5
EVN|A21|20251103101000
PID|1||PAT001^^^HOSP^PI||MARTIN^PIERRE||19800101|M
PV1|1|I|WARD1^BED1^01^HOSP||||^DR^SMITH^^^MD|||||||||||VIS001|||||||||||||||||||||||||20251103101000""",
    
    "A22": """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103101100||ADT^A22^ADT_A22|MSG_A22|P|2.5
EVN|A22|20251103101100
PID|1||PAT001^^^HOSP^PI||MARTIN^PIERRE||19800101|M
PV1|1|I|WARD1^BED1^01^HOSP||||^DR^SMITH^^^MD|||||||||||VIS001|||||||||||||||||||||||||20251103101100""",
    
    "A52": """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103101200||ADT^A52^ADT_A52|MSG_A52|P|2.5
EVN|A52|20251103101200
PID|1||PAT001^^^HOSP^PI||MARTIN^PIERRE||19800101|M
PV1|1|I|WARD1^BED1^01^HOSP||||^DR^SMITH^^^MD|||||||||||VIS001|||||||||||||||||||||||||20251103101200""",
    
    "A53": """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103101300||ADT^A53^ADT_A53|MSG_A53|P|2.5
EVN|A53|20251103101300
PID|1||PAT001^^^HOSP^PI||MARTIN^PIERRE||19800101|M
PV1|1|I|WARD1^BED1^01^HOSP||||^DR^SMITH^^^MD|||||||||||VIS001|||||||||||||||||||||||||20251103101300""",
    
    # Changement de médecin
    "A54": """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103101400||ADT^A54^ADT_A54|MSG_A54|P|2.5
EVN|A54|20251103101400
PID|1||PAT001^^^HOSP^PI||MARTIN^PIERRE||19800101|M
PV1|1|I|WARD1^BED1^01^HOSP||||^DR^GREEN^^^MD|||||||||||VIS001|||||||||||||||||||||||||20251103101400""",
    
    "A55": """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103101500||ADT^A55^ADT_A55|MSG_A55|P|2.5
EVN|A55|20251103101500
PID|1||PAT001^^^HOSP^PI||MARTIN^PIERRE||19800101|M
PV1|1|I|WARD1^BED1^01^HOSP||||^DR^SMITH^^^MD|||||||||||VIS001|||||||||||||||||||||||||20251103101500""",
    
    # Mises à jour patient
    "A28": """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103101600||ADT^A28^ADT_A28|MSG_A28|P|2.5
EVN|A28|20251103101600
PID|1||PAT005^^^HOSP^PI||NOUVEAU^PATIENT||19950615|M""",
    
    "A31": """MSH|^~\\&|SEND|FAC|RECV|FAC|20251103101700||ADT^A31^ADT_A31|MSG_A31|P|2.5
EVN|A31|20251103101700
PID|1||PAT001^^^HOSP^PI||MARTIN^PIERRE-UPDATED||19800101|M""",
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
    print("🧪 TEST COMPLET IHE PAM - Tous les événements implémentés")
    print("=" * 100)
    print()
    
    # Get count before
    with session_factory() as s:
        before_count = s.exec(select(MessageLog)).all()
        max_id_before = max([m.id for m in before_count]) if before_count else 0
    
    print(f"📊 Nombre de messages avant test: {len(before_count)} (max ID={max_id_before})")
    print()
    
    # Inject all test messages (avec segments ZBE)
    results = {}
    movement_seq = 8000
    for event_type, message in IHE_PAM_MESSAGES.items():
        movement_seq += 1
        # Ajouter segment ZBE au message
        message_with_zbe = add_zbe_segment_to_message(message, event_type, movement_seq)
        
        print(f"📨 Injection {event_type}...", end=" ", flush=True)
        success = await inject_message(event_type, message_with_zbe)
        if success:
            print("✅")
        results[event_type] = success
        await asyncio.sleep(0.2)  # Petit délai entre messages
    
    print()
    print("⏳ Attente traitement et émission automatique (8s)...")
    time.sleep(8)
    
    # Check results
    print()
    print("📊 RÉSULTATS PAR TYPE:")
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
        
        print(f"\n{'Type':6} | {'Catégorie':20} | {'Reçu':5} | {'Émis':5} | Résultat")
        print("-" * 80)
        
        categories = {
            "A01": "Admission",
            "A04": "Registration",
            "A05": "Pre-admission",
            "A06": "Class change",
            "A07": "Class change",
            "A02": "Transfer",
            "A03": "Discharge",
            "A11": "Cancel admission",
            "A12": "Cancel transfer",
            "A13": "Cancel discharge",
            "A21": "Leave out",
            "A22": "Leave return",
            "A52": "Leave out (ext)",
            "A53": "Leave return (ext)",
            "A54": "Change doctor",
            "A55": "Cancel change doc",
            "A28": "Add person",
            "A31": "Update person",
        }
        
        all_ok = True
        tested_count = 0
        success_count = 0
        
        for event_type in sorted(IHE_PAM_MESSAGES.keys()):
            received = inbound.get(event_type, 0)
            emitted = outbound.get(event_type, 0)
            category = categories.get(event_type, "Unknown")
            
            tested_count += 1
            
            # Check if type is preserved
            if received > 0 and emitted > 0:
                status = "✅ OK"
                success_count += 1
            elif received > 0 and emitted == 0:
                status = "⚠️  Pas d'émission"
                all_ok = False
            elif received == 0:
                status = "❌ Pas reçu"
                all_ok = False
            else:
                status = "?"
                all_ok = False
            
            print(f"{event_type:6} | {category:20} | {received:5} | {emitted:5} | {status}")
        
        print()
        print("=" * 100)
        print(f"📈 Résumé: {success_count}/{tested_count} types OK ({success_count*100//tested_count}%)")
        print()
        
        if all_ok:
            print("🎉" * 50)
            print("✅ TOUS LES TYPES DE MESSAGES IHE PAM SONT PRÉSERVÉS ET ÉMIS !")
            print("🎉" * 50)
        else:
            print("⚠️  Certains types n'ont pas été correctement traités")
            print("    Vérifiez les logs du serveur pour plus de détails")
        
        return all_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
