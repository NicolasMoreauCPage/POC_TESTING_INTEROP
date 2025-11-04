#!/usr/bin/env python3
"""
Test COMPLET des 18 types de messages IHE PAM avec segments ZBE corrects
"""
import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
import socket
from app.services.mllp import frame_hl7


def build_ihe_pam_message_with_zbe(trigger: str, patient_id: str, movement_seq: int) -> str:
    """Construit un message IHE PAM complet avec segment ZBE"""
    now = datetime.now()
    msh_timestamp = now.strftime("%Y%m%d%H%M%S")
    # Movement datetime = quelques minutes plus tard
    movement_dt = (now + timedelta(minutes=5)).strftime("%Y%m%d%H%M%S")
    
    # Déterminer l'action ZBE-4 selon le trigger
    if trigger in ["A11", "A12", "A13", "A23", "A38", "A52", "A53", "A55"]:
        action_type = "CANCEL"
        cancel_flag = "Y"
        # Pour les annulations, ZBE-6 contient l'événement d'origine
        if trigger == "A11":
            origin_event = "A01"  # Annule une admission
        elif trigger == "A12":
            origin_event = "A02"  # Annule un transfert
        elif trigger == "A13":
            origin_event = "A03"  # Annule une sortie
        elif trigger == "A23":
            origin_event = "A01"  # Annule une admission
        elif trigger == "A38":
            origin_event = "A01"  # Annule une admission
        elif trigger == "A52":
            origin_event = "A21"  # Annule une permission
        elif trigger == "A53":
            origin_event = "A22"  # Annule un retour de permission
        elif trigger == "A55":
            origin_event = "A54"  # Annule un changement de médecin
        else:
            origin_event = ""
    elif trigger in ["A06", "A07", "A31"]:
        action_type = "UPDATE"
        cancel_flag = "N"
        origin_event = ""
    else:
        action_type = "INSERT"
        cancel_flag = "N"
        origin_event = ""
    
    # Mode de traitement
    if trigger in ["A21", "A52"]:
        mode = "L"  # Leave
    elif trigger in ["A11", "A12", "A13", "A23", "A38", "A52", "A53", "A55"]:
        mode = "C"  # Cancelled
    else:
        mode = "HMS"  # Normal
    
    # UF selon le type
    uf_code = "CARDIO"
    if trigger in ["A02", "A12"]:
        uf_code = "NEURO"  # Transfert vers neurologie
    
    # Segment ZBE complet conforme IHE PAM France
    zbe_segment = (
        f"ZBE|"  # ZBE-0
        f"{movement_seq}^MOVEMENT^1.2.250.1.213.1.1.9^ISO|"  # ZBE-1: Movement ID
        f"{movement_dt}|"  # ZBE-2: Movement datetime (NOT message time!)
        f"|"  # ZBE-3: empty
        f"{action_type}|"  # ZBE-4: INSERT/UPDATE/CANCEL
        f"{cancel_flag}|"  # ZBE-5: Cancel indicator
        f"{origin_event}|"  # ZBE-6: Original event (for cancellations)
        f"^^^^^^UF^^^{uf_code}|"  # ZBE-7: UF responsabilité (code en position 10)
        f"|"  # ZBE-8: empty
        f"{mode}"  # ZBE-9: Processing mode (HMS/L/C)
    )
    
    # Construire le message selon le type
    # Base commune
    msh = f"MSH|^~\\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|{msh_timestamp}||ADT^{trigger}|MSG{movement_seq}|P|2.5|||AL|NE|FRA"
    evn = f"EVN|{trigger}|{msh_timestamp}"
    pid = f"PID|1||{patient_id}^^^HOSPITAL^PI||DOE^JOHN||19800101|M"
    
    # PV1 varie selon le type de message
    if trigger in ["A01", "A04", "A05"]:
        # Admission
        pv1 = f"PV1|1|I|WARD1^101^01^HOSPITAL^^^^{uf_code}|||123456^DR^SMITH|||{uf_code}|||||||654321^^^HOSPITAL^VN|||||||||||||||||HOSPITAL||||{msh_timestamp}"
    elif trigger in ["A02", "A12"]:
        # Transfert
        pv1 = f"PV1|1|I|WARD2^201^01^HOSPITAL^^^^{uf_code}|||123456^DR^SMITH|||{uf_code}|||||||654321^^^HOSPITAL^VN||||||||||||||||||||HOSPITAL||||{msh_timestamp}|||||WARD1^101^01"
    elif trigger in ["A03", "A13"]:
        # Sortie
        pv1 = f"PV1|1|I|WARD1^101^01^HOSPITAL^^^^{uf_code}|||123456^DR^SMITH|||{uf_code}|||||||654321^^^HOSPITAL^VN|||||||||||||||||HOSPITAL||||{msh_timestamp}|||{msh_timestamp}"
    elif trigger in ["A21", "A22", "A52", "A53"]:
        # Permission
        pv1 = f"PV1|1|I|WARD1^101^01^HOSPITAL^^^^{uf_code}|||123456^DR^SMITH|||{uf_code}|||||||654321^^^HOSPITAL^VN|||||||||||||||||HOSPITAL||||{msh_timestamp}"
    elif trigger in ["A54", "A55"]:
        # Changement médecin
        pv1 = f"PV1|1|I|WARD1^101^01^HOSPITAL^^^^{uf_code}|||789012^DR^JONES^^^MD|||{uf_code}|||||||654321^^^HOSPITAL^VN|||||||||||||||||HOSPITAL||||{msh_timestamp}"
    else:
        # Défaut
        pv1 = f"PV1|1|I|WARD1^101^01^HOSPITAL^^^^{uf_code}|||123456^DR^SMITH|||{uf_code}|||||||654321^^^HOSPITAL^VN|||||||||||||||||HOSPITAL||||{msh_timestamp}"
    
    message = "\r".join([msh, evn, pid, pv1, zbe_segment])
    return message


async def test_all_ihe_pam_with_zbe():
    """Test tous les 18 types de messages IHE PAM avec segments ZBE"""
    print("\n" + "="*80)
    print("TEST: Tous les messages IHE PAM avec segments ZBE conformes")
    print("="*80)
    
    # Messages IHE PAM par catégorie
    test_cases = [
        # Admissions
        ("A01", "Admit/Visit notification", "admission"),
        ("A04", "Register a patient", "admission"),
        ("A05", "Pre-admit a patient", "admission"),
        
        # Changements de type
        ("A06", "Change an outpatient to an inpatient", "admission"),
        ("A07", "Change an inpatient to an outpatient", "admission"),
        
        # Transferts
        ("A02", "Transfer a patient", "transfer"),
        
        # Sorties
        ("A03", "Discharge/end visit", "discharge"),
        
        # Annulations
        ("A11", "Cancel admit/visit notification", "cancel-admission"),
        ("A12", "Cancel transfer", "cancel-transfer"),
        ("A13", "Cancel discharge", "cancel-discharge"),
        ("A23", "Delete a patient record", "cancel-admission"),
        ("A38", "Cancel pre-admit", "cancel-admission"),
        
        # Permissions
        ("A21", "Patient goes on leave of absence", "leave"),
        ("A22", "Patient returns from leave of absence", "leave"),
        ("A52", "Cancel leave of absence", "leave"),
        ("A53", "Cancel patient returns from leave", "leave"),
        
        # Médecin
        ("A54", "Change attending doctor", "doctor"),
        ("A55", "Cancel change attending doctor", "doctor"),
        
        # Demographics
        ("A28", "Add person information", "admission"),
        ("A31", "Update person information", "admission"),
    ]
    
    results = []
    movement_seq = 6000
    
    for trigger, description, category in test_cases:
        movement_seq += 1
        patient_id = f"PAT_{trigger}"
        
        print(f"\n{'─'*80}")
        print(f"Test {movement_seq-6000}/18: {trigger} - {description}")
        print(f"Category: {category}")
        print(f"{'─'*80}")
        
        # Nouvelle connexion pour chaque message
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("localhost", 2575))
            sock.settimeout(5.0)
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            results.append((trigger, False, "Connection failed"))
            continue
        
        try:
            # Construire le message
            message = build_ihe_pam_message_with_zbe(trigger, patient_id, movement_seq)
            
            # Montrer le segment ZBE
            zbe_line = [line for line in message.split("\r") if line.startswith("ZBE")]
            if zbe_line:
                print(f"ZBE: {zbe_line[0][:100]}...")
            
            # Framer et envoyer
            framed = frame_hl7(message)
            sock.sendall(framed)
            
            # Recevoir ACK
            ack_data = sock.recv(4096)
            if b"AA" in ack_data or b"CA" in ack_data:
                print(f"✅ ACK received")
                results.append((trigger, True, None))
            elif b"AE" in ack_data or b"AR" in ack_data:
                print(f"⚠️  NACK received")
                results.append((trigger, False, "NACK"))
            else:
                print(f"❌ Unknown response")
                results.append((trigger, False, "Unknown"))
        
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append((trigger, False, str(e)))
        
        finally:
            sock.close()
        
        # Petit délai entre messages
        await asyncio.sleep(0.5)
    
    # Résumé final
    print(f"\n{'='*80}")
    print(f"SUMMARY: IHE PAM Messages Test Results")
    print(f"{'='*80}")
    
    success_count = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"\nSuccess rate: {success_count}/{total} ({100*success_count//total}%)")
    print(f"\n{'─'*80}")
    
    for trigger, success, error in results:
        status = "✅" if success else "❌"
        desc = [d for t, d, _ in test_cases if t == trigger][0]
        error_msg = f" ({error})" if error else ""
        print(f"{status} {trigger:4s} - {desc:50s}{error_msg}")
    
    print(f"\n{'='*80}\n")
    
    # Détail des échecs
    failures = [(t, e) for t, s, e in results if not s]
    if failures:
        print(f"Failed messages ({len(failures)}):")
        for trigger, error in failures:
            print(f"  - {trigger}: {error}")
    else:
        print(f"🎉 All messages processed successfully!")
    
    print()


if __name__ == "__main__":
    asyncio.run(test_all_ihe_pam_with_zbe())
