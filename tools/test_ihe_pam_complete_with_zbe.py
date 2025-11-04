#!/usr/bin/env python3
"""
Test complet des événements IHE PAM avec segments ZBE conformes.
Teste l'injection de tous les types de messages avec ZBE et vérifie l'émission automatique.
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


def build_zbe_segment(trigger: str, movement_seq: int) -> str:
    """Construit un segment ZBE conforme IHE PAM France"""
    now = datetime.now()
    # Movement datetime = quelques minutes après le MSH timestamp
    movement_dt = (now + timedelta(minutes=5)).strftime("%Y%m%d%H%M%S")
    
    # Déterminer l'action ZBE-4 selon le trigger
    if trigger in ["A11", "A12", "A13", "A23", "A38", "A52", "A53", "A55"]:
        action_type = "CANCEL"
        cancel_flag = "Y"
        mode = "C"  # Cancelled
        # Événement d'origine
        origin_map = {
            "A11": "A01", "A23": "A01", "A38": "A05",
            "A12": "A02", "A13": "A03",
            "A52": "A21", "A53": "A22", "A55": "A54"
        }
        origin_event = origin_map.get(trigger, "")
    elif trigger in ["A06", "A07", "A31"]:
        action_type = "UPDATE"
        cancel_flag = "N"
        origin_event = ""
        mode = "HMS"
    else:
        action_type = "INSERT"
        cancel_flag = "N"
        origin_event = ""
        mode = "L" if trigger in ["A21", "A52"] else "HMS"
    
    # UF selon le type
    uf_code = "CARDIO"
    if trigger in ["A02", "A12"]:
        uf_code = "NEURO"  # Transfert vers neurologie
    
    # Segment ZBE complet conforme IHE PAM France
    zbe = (
        f"ZBE|"  # ZBE-0
        f"{movement_seq}^MOVEMENT^1.2.250.1.213.1.1.9^ISO|"  # ZBE-1: Movement ID
        f"{movement_dt}|"  # ZBE-2: Movement datetime
        f"|"  # ZBE-3: empty
        f"{action_type}|"  # ZBE-4: INSERT/UPDATE/CANCEL
        f"{cancel_flag}|"  # ZBE-5: Cancel indicator
        f"{origin_event}|"  # ZBE-6: Original event
        f"^^^^^^UF^^^{uf_code}|"  # ZBE-7: UF responsabilité (code en position 10)
        f"|"  # ZBE-8: empty
        f"{mode}"  # ZBE-9: Processing mode (HMS/L/C)
    )
    return zbe


# Messages de test pour tous les événements IHE PAM avec segments ZBE
def get_ihe_pam_messages_with_zbe():
    """Génère les messages IHE PAM avec segments ZBE"""
    base_seq = 7000
    messages = {}
    
    # Pattern de base pour construire les messages
    test_cases = [
        ("A01", "PAT001", "MARTIN^PIERRE", "19800101", "M", "I", "WARD1^BED1^01^HOSP^^^^CARDIO", "VIS001"),
        ("A04", "PAT002", "DUPONT^MARIE", "19850315", "F", "I", "WARD2^BED2^02^HOSP^^^^CARDIO", "VIS002"),
        ("A05", "PAT003", "BERNARD^JEAN", "19750520", "M", "I", "WARD3^BED3^03^HOSP^^^^CARDIO", "VIS003"),
        ("A06", "PAT001", "MARTIN^PIERRE", "19800101", "M", "O", "WARD1^BED1^01^HOSP^^^^CARDIO", "VIS001"),
        ("A07", "PAT001", "MARTIN^PIERRE", "19800101", "M", "I", "WARD1^BED1^01^HOSP^^^^CARDIO", "VIS001"),
        ("A02", "PAT001", "MARTIN^PIERRE", "19800101", "M", "I", "WARD4^BED4^04^HOSP^^^^NEURO", "VIS001"),
        ("A03", "PAT001", "MARTIN^PIERRE", "19800101", "M", "I", "WARD4^BED4^04^HOSP^^^^CARDIO", "VIS001"),
        ("A11", "PAT004", "PETIT^ALICE", "19900210", "F", "I", "WARD5^BED5^05^HOSP^^^^CARDIO", "VIS004"),
        ("A12", "PAT001", "MARTIN^PIERRE", "19800101", "M", "I", "WARD1^BED1^01^HOSP^^^^CARDIO", "VIS001"),
        ("A13", "PAT001", "MARTIN^PIERRE", "19800101", "M", "I", "WARD1^BED1^01^HOSP^^^^CARDIO", "VIS001"),
        ("A21", "PAT001", "MARTIN^PIERRE", "19800101", "M", "I", "WARD1^BED1^01^HOSP^^^^CARDIO", "VIS001"),
        ("A22", "PAT001", "MARTIN^PIERRE", "19800101", "M", "I", "WARD1^BED1^01^HOSP^^^^CARDIO", "VIS001"),
        ("A52", "PAT001", "MARTIN^PIERRE", "19800101", "M", "I", "WARD1^BED1^01^HOSP^^^^CARDIO", "VIS001"),
        ("A53", "PAT001", "MARTIN^PIERRE", "19800101", "M", "I", "WARD1^BED1^01^HOSP^^^^CARDIO", "VIS001"),
        ("A54", "PAT001", "MARTIN^PIERRE", "19800101", "M", "I", "WARD1^BED1^01^HOSP^^^^CARDIO", "VIS001"),
        ("A55", "PAT001", "MARTIN^PIERRE", "19800101", "M", "I", "WARD1^BED1^01^HOSP^^^^CARDIO", "VIS001"),
        ("A28", "PAT005", "NOUVEAU^PATIENT", "19950615", "M", None, None, None),
        ("A31", "PAT001", "MARTIN^PIERRE-UPDATED", "19800101", "M", None, None, None),
    ]
    
    for idx, (trigger, pat_id, name, dob, sex, pat_class, location, visit_num) in enumerate(test_cases):
        movement_seq = base_seq + idx + 1
        now = datetime.now()
        msh_timestamp = now.strftime("%Y%m%d%H%M%S")
        
        # Segment ZBE
        zbe = build_zbe_segment(trigger, movement_seq)
        
        # Construire le message
        msh = f"MSH|^~\\&|SEND|FAC|RECV|FAC|{msh_timestamp}||ADT^{trigger}^ADT_{trigger}|MSG_{trigger}_{movement_seq}|P|2.5"
        evn = f"EVN|{trigger}|{msh_timestamp}"
        pid = f"PID|1||{pat_id}^^^HOSP^PI||{name}||{dob}|{sex}"
        
        # PV1 si applicable
        if pat_class and location:
            pv1 = f"PV1|1|{pat_class}|{location}|||123456^DR^SMITH|||CARDIO|||||||{visit_num}^^^HOSP^VN|||||||||||||||||HOSP||||{msh_timestamp}"
            message = "\r".join([msh, evn, pid, pv1, zbe])
        else:
            message = "\r".join([msh, evn, pid, zbe])
        
        messages[trigger] = message
    
    return messages


async def inject_message(event_type: str, message: str) -> bool:
    """Inject one test message via MLLP"""
    try:
        ack = await send_mllp("localhost", 2575, message)
        # Vérifier si l'ACK est positif (AA ou CA)
        return b"AA" in ack or b"CA" in ack if isinstance(ack, bytes) else ("AA" in ack or "CA" in ack)
    except Exception as e:
        print(f"❌ Erreur injection {event_type}: {e}")
        return False


async def main():
    print("\n" + "="*80)
    print("TEST COMPLET IHE PAM AVEC SEGMENTS ZBE")
    print("="*80)
    
    # Générer les messages avec ZBE
    messages = get_ihe_pam_messages_with_zbe()
    
    print(f"\n📋 Injection de {len(messages)} types de messages IHE PAM avec segments ZBE...\n")
    
    # Injecter tous les messages
    for event_type in sorted(messages.keys()):
        message = messages[event_type]
        print(f"📨 Injection {event_type}...", end=" ")
        
        success = await inject_message(event_type, message)
        if success:
            print("✅")
        else:
            print("❌")
        
        await asyncio.sleep(0.3)  # Petit délai entre messages
    
    # Attendre que les messages soient traités et émis
    print(f"\n⏳ Attente traitement et émission automatique (8s)...")
    await asyncio.sleep(8)
    
    # Analyser les résultats
    print(f"\n📊 RÉSULTATS PAR TYPE:")
    print("="*80)
    print(f"{'Type':<7}| {'Catégorie':<20} | {'Reçu':<5} | {'Émis':<5} | Résultat")
    print("-"*80)
    
    # Catégories de messages
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
    
    success_count = 0
    total_types = len(messages)
    
    with session_factory() as session:
        for event_type in sorted(messages.keys()):
            category = categories.get(event_type, "Unknown")
            
            # Compter les messages reçus (inbound)
            inbound = session.exec(
                select(MessageLog)
                .where(MessageLog.direction == "inbound")
                .where(MessageLog.kind.like(f"%{event_type}%"))
            ).all()
            
            # Compter les messages émis (outbound)
            outbound = session.exec(
                select(MessageLog)
                .where(MessageLog.direction == "outbound")
                .where(MessageLog.kind.like(f"%{event_type}%"))
            ).all()
            
            inbound_count = len(inbound)
            outbound_count = len(outbound)
            
            # Déterminer le résultat
            if outbound_count > 0:
                status = "✅ OK"
                success_count += 1
            elif inbound_count > 0:
                status = "⚠️  Pas d'émission"
            else:
                status = "❌ Pas reçu"
            
            print(f"{event_type:<7}| {category:<20} | {inbound_count:>5} | {outbound_count:>5} | {status}")
    
    print("="*80)
    percentage = (success_count * 100) // total_types if total_types > 0 else 0
    print(f"📈 Résumé: {success_count}/{total_types} types OK ({percentage}%)")
    
    if success_count < total_types:
        print(f"\n⚠️  Certains types n'ont pas été correctement traités")
        print(f"    Vérifiez les logs du serveur pour plus de détails")
    else:
        print(f"\n🎉 Tous les types de messages ont été traités avec succès!")
    
    print()


if __name__ == "__main__":
    asyncio.run(main())
