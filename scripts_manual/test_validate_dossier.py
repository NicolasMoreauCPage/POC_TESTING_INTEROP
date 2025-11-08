"""
Test de la fonctionnalité de validation de dossier.

Ce script teste la validation des messages d'un dossier en utilisant
l'endpoint /messages/validate-dossier.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.db_session_factory import session_factory
from app.models import Dossier
from app.models_endpoints import MessageLog
from sqlmodel import select

def main():
    print("=" * 80)
    print("Test de validation de dossier")
    print("=" * 80)
    
    with session_factory() as session:
        # 1. Lister les dossiers disponibles
        print("\n1. Dossiers disponibles:")
        dossiers = session.exec(select(Dossier).limit(10)).all()
        if not dossiers:
            print("   ⚠️  Aucun dossier trouvé en base de données")
            print("   → Créez d'abord des dossiers avec des messages associés")
        else:
            for d in dossiers:
                print(f"   - Dossier ID={d.id}, seq={d.dossier_seq}, patient_id={d.patient_id}")
        
        # 2. Compter les messages MLLP
        print("\n2. Messages MLLP disponibles:")
        msg_count = session.exec(
            select(MessageLog).where(MessageLog.kind == "MLLP")
        ).all()
        print(f"   Total: {len(msg_count)} messages MLLP")
        
        if len(msg_count) > 0:
            # Afficher quelques exemples
            print("\n   Exemples de messages:")
            for msg in msg_count[:5]:
                print(f"   - Message ID={msg.id}, type={msg.message_type}, created_at={msg.created_at}")
                if msg.payload:
                    # Extraire PV1-19 (numéro de dossier)
                    lines = msg.payload.replace("\r\n", "\r").replace("\n", "\r").split("\r")
                    for line in lines:
                        if line.startswith("PV1|"):
                            parts = line.split("|")
                            if len(parts) > 19 and parts[19]:
                                visit_num = parts[19].split("^")[0]
                                print(f"      → Numéro de visite (PV1-19): {visit_num}")
                            break
        
        # 3. Instructions pour tester
        print("\n3. Pour tester la fonctionnalité:")
        print("   → Allez sur http://127.0.0.1:8000/messages")
        print("   → Cliquez sur 'Valider un dossier'")
        if dossiers:
            print(f"   → Entrez un ID de dossier (ex: {dossiers[0].id})")
            if dossiers[0].dossier_seq:
                print(f"   → Ou un numéro de visite externe (ex: {dossiers[0].dossier_seq})")
        print("   → Cliquez sur 'Valider le dossier'")
        
        print("\n4. Test de la fonction d'extraction:")
        # Tester la fonction _extract_ipp_and_dossier avec un vrai message
        if len(msg_count) > 0:
            test_msg = msg_count[0]
            from app.routers.messages import _extract_ipp_and_dossier
            ipp, dossier = _extract_ipp_and_dossier(test_msg.payload)
            print(f"   Message réel (ID={test_msg.id}): IPP={ipp}, Dossier={dossier}")
            
            # Afficher le segment PV1 pour débogage
            if test_msg.payload:
                lines = test_msg.payload.replace("\r\n", "\r").replace("\n", "\r").split("\r")
                for line in lines:
                    if line.startswith("PV1|"):
                        print(f"   Segment PV1: {line[:100]}...")
                        break
        else:
            # Test avec message synthétique
            sample_hl7 = "MSH|^~\\&|SendingApp|SendFac|ReceivingApp|RecvFac|20240101120000||ADT^A01^ADT_A01|MSG001|P|2.5\r"
            sample_hl7 += "EVN|A01|20240101120000\r"
            sample_hl7 += "PID|1||123456^^^HOSP^PI||DOE^JOHN||19800101|M\r"
            sample_hl7 += "PV1|1|I|WARD^101^A|||DOC123^SMITH^JANE|||||||||||V2024-12345^^^HOSP^VN"
            
            from app.routers.messages import _extract_ipp_and_dossier
            ipp, dossier = _extract_ipp_and_dossier(sample_hl7)
            print(f"   Message test: IPP={ipp}, Dossier={dossier}")
            if ipp == "123456" and dossier == "V2024-12345":
                print("   ✓ Extraction OK")
            else:
                print(f"   ✗ Extraction incorrecte (attendu: IPP=123456, Dossier=V2024-12345)")
        
        print("\n" + "=" * 80)
        print("Test terminé")
        print("=" * 80)

if __name__ == "__main__":
    main()
