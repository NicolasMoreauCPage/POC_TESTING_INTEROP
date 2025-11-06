"""
Test de validation des segments obligatoires ZBE et MRG dans les messages IHE PAM
"""
import asyncio
from datetime import datetime
from app.db import engine, Session
from app.models import Patient, Dossier, Venue, Mouvement
from app.models_structure import UniteFonctionnelle, Service
from app.models_structure_fhir import EntiteJuridique, GHTContext
from app.models_shared import SystemEndpoint
from sqlmodel import select, delete
from app.services.transport_inbound import on_message_inbound_async


async def setup_test_data(session: Session):
    """Créer une structure de test minimale"""
    print("\n" + "="*80)
    print("SETUP: Création de la structure de test")
    print("="*80)
    
    # Créer un GHT
    ght = GHTContext(
        name="GHT Test",
        code="TGHT",
        description="GHT de test"
    )
    session.add(ght)
    session.flush()
    
    # Créer une EJ
    ej = EntiteJuridique(
        name="Hopital Test",
        finess_ej="210000123",
        short_name="HTEST",
        ght_context_id=ght.id
    )
    session.add(ej)
    session.flush()
    
    # Créer un endpoint
    endpoint = SystemEndpoint(
        name="Test Endpoint",
        kind="MLLP",
        role="RECEIVER",
        entite_juridique_id=ej.id
    )
    session.add(endpoint)
    session.flush()
    
    print(f"✅ GHT créé: {ght.name} (ID={ght.id})")
    print(f"✅ EJ créée: {ej.name} (ID={ej.id}, FINESS={ej.finess_ej})")
    print(f"✅ Endpoint créé: {endpoint.name} (ID={endpoint.id})")
    
    return ght, ej, endpoint


async def cleanup_test_data(session: Session):
    """Nettoyer les données de test"""
    print("\n" + "="*80)
    print("CLEANUP: Suppression des données de test")
    print("="*80)
    
    # Supprimer dans l'ordre inverse des dépendances
    session.exec(delete(Mouvement))
    session.exec(delete(Venue))
    session.exec(delete(Dossier))
    session.exec(delete(Patient))
    session.exec(delete(SystemEndpoint))
    session.exec(delete(EntiteJuridique))
    session.exec(delete(GHTContext))
    session.commit()
    print("✅ Données nettoyées")


async def test_missing_zbe_segment():
    """Test : Message de mouvement sans segment ZBE (doit être rejeté)"""
    print("\n" + "="*80)
    print("TEST 1: Message A01 sans segment ZBE")
    print("="*80)
    
    # Message A01 (admission) SANS segment ZBE
    message = """MSH|^~\\&|CPAGE|CPAGE|ANTARES|ANTARES|20251106120000||ADT^A01^ADT_A01|MSG001|P|2.5^FRA^2.11|||||FRA|8859/1
EVN||20251106120000|20251106120000||pat^INCONNU^INCONNU^^^^^^CPAGE&1.2.250.1.154&ISO|20251106120000
PID|||000059478001^^^CPAGE&1.2.250.1.211.10.200.2&ISO^PI||MARTIN^JEAN^^^M^^D||19800101|M
PV1||O|7700|R|||101005344^PICQUE^JEAN BAPTISTE^^^^^^ASIP-SANTE-PS&1.2.250.1.71.4.2.1&ISO^L^^^ADELI|||||||A||1|||||MSG001^^^CPAGE&1.2.250.1.211.12.1.2&L^VN|||N"""
    
    session = Session(engine)
    try:
        ght, ej, endpoint = await setup_test_data(session)
        
        # Tester l'intégration
        ack_message = await on_message_inbound_async(message, session, endpoint)
        
        # Analyser l'ACK pour vérifier le rejet
        if "MSA|AE|" in ack_message and "ZBE obligatoire" in ack_message:
            print("\n✅ Message rejeté comme prévu")
            print(f"   Message d'erreur : {ack_message.split('ERR|')[1][:150] if 'ERR|' in ack_message else 'Vérifier ACK'}")
        else:
            print(f"\n❌ Message accepté alors qu'il devrait être rejeté!")
            print(f"   ACK: {ack_message[:200]}...")
            
    finally:
        await cleanup_test_data(session)
        session.close()


async def test_valid_zbe_segment():
    """Test : Message de mouvement avec segment ZBE (doit être accepté)"""
    print("\n" + "="*80)
    print("TEST 2: Message A01 avec segment ZBE valide")
    print("="*80)
    
    # Message A01 (admission) AVEC segment ZBE
    message = """MSH|^~\\&|CPAGE|CPAGE|ANTARES|ANTARES|20251106120000||ADT^A01^ADT_A01|MSG002|P|2.5^FRA^2.11|||||FRA|8859/1
EVN||20251106120000|20251106120000||pat^INCONNU^INCONNU^^^^^^CPAGE&1.2.250.1.154&ISO|20251106120000
PID|||000059478002^^^CPAGE&1.2.250.1.211.10.200.2&ISO^PI||DUPONT^MARIE^^^Mme^^D||19900505|F
PV1||O|7700|R|||101005344^PICQUE^JEAN BAPTISTE^^^^^^ASIP-SANTE-PS&1.2.250.1.71.4.2.1&ISO^L^^^ADELI|||||||A||1|||||MSG002^^^CPAGE&1.2.250.1.211.12.1.2&L^VN|||N
ZBE|12565200^CPAGE^1.2.250.1.211.12.1.2^ISO|20251106120000||INSERT|N|A01|||M"""
    
    session = Session(engine)
    try:
        ght, ej, endpoint = await setup_test_data(session)
        
        # Tester l'intégration
        ack_message = await on_message_inbound_async(message, session, endpoint)
        
        # Analyser l'ACK pour vérifier l'acceptation
        if "MSA|AA|" in ack_message:
            print("\n✅ Message accepté comme prévu")
            print(f"   ACK: {ack_message[:100]}...")
        else:
            print(f"\n❌ Message rejeté alors qu'il devrait être accepté!")
            print(f"   ACK: {ack_message[:200]}...")
            
    finally:
        await cleanup_test_data(session)
        session.close()


async def test_missing_mrg_segment():
    """Test : Message A40 sans segment MRG (doit être rejeté)"""
    print("\n" + "="*80)
    print("TEST 3: Message A40 (fusion) sans segment MRG")
    print("="*80)
    
    # Message A40 (fusion patients) SANS segment MRG
    message = """MSH|^~\\&|CPAGE|CPAGE|ANTARES|ANTARES|20251106120000||ADT^A40^ADT_A40|MSG003|P|2.5^FRA^2.11|||||FRA|8859/1
EVN||20251106120000|20251106120000||pat^INCONNU^INCONNU^^^^^^CPAGE&1.2.250.1.154&ISO|20251106120000
PID|||000059478003^^^CPAGE&1.2.250.1.211.10.200.2&ISO^PI||BERNARD^PAUL^^^M^^D||19750315|M"""
    
    session = Session(engine)
    try:
        ght, ej, endpoint = await setup_test_data(session)
        
        # Tester l'intégration
        ack_message = await on_message_inbound_async(message, session, endpoint)
        
        # Analyser l'ACK pour vérifier le rejet
        if "MSA|AE|" in ack_message and "MRG obligatoire" in ack_message:
            print("\n✅ Message rejeté comme prévu")
            print(f"   Message d'erreur : {ack_message.split('ERR|')[1][:150] if 'ERR|' in ack_message else 'Vérifier ACK'}")
        else:
            print(f"\n❌ Message non rejeté correctement!")
            print(f"   ACK: {ack_message[:200]}...")
            
    finally:
        await cleanup_test_data(session)
        session.close()


async def test_valid_mrg_segment():
    """Test : Message A40 avec segment MRG (doit être accepté structurellement)"""
    print("\n" + "="*80)
    print("TEST 4: Message A40 (fusion) avec segment MRG valide")
    print("="*80)
    
    # Message A40 (fusion patients) AVEC segment MRG
    message = """MSH|^~\\&|CPAGE|CPAGE|ANTARES|ANTARES|20251106120000||ADT^A40^ADT_A40|MSG004|P|2.5^FRA^2.11|||||FRA|8859/1
EVN||20251106120000|20251106120000||pat^INCONNU^INCONNU^^^^^^CPAGE&1.2.250.1.154&ISO|20251106120000
PID|||000059478004^^^CPAGE&1.2.250.1.211.10.200.2&ISO^PI||THOMAS^LUC^^^M^^D||19820820|M
MRG|000059478099^^^CPAGE&1.2.250.1.211.10.200.2&ISO^PI|||||||THOMAS^LUC"""
    
    session = Session(engine)
    try:
        ght, ej, endpoint = await setup_test_data(session)
        
        # Tester l'intégration
        ack_message = await on_message_inbound_async(message, session, endpoint)
        
        # Note: Le message peut être rejeté pour d'autres raisons (ex: pas encore supporté)
        # mais au moins il ne doit PAS être rejeté pour segment MRG manquant
        if "MRG obligatoire" in ack_message:
            print(f"\n❌ Message rejeté pour segment MRG manquant alors qu'il est présent!")
            print(f"   ACK: {ack_message[:200]}...")
        else:
            print("\n✅ Segment MRG détecté (message peut être rejeté pour d'autres raisons)")
            if "MSA|AA|" in ack_message:
                print("   → Message accepté")
            else:
                print(f"   → Message rejeté pour une autre raison (normal si A40 pas encore supporté)")
                print(f"   ACK: {ack_message[:150]}...")
            
    finally:
        await cleanup_test_data(session)
        session.close()


async def test_a08_without_zbe():
    """Test : Message A08 (mise à jour) sans segment ZBE (doit être rejeté)"""
    print("\n" + "="*80)
    print("TEST 5: Message A08 (mise à jour) sans segment ZBE")
    print("="*80)
    
    # Message A08 (mise à jour patient) SANS segment ZBE
    message = """MSH|^~\\&|CPAGE|CPAGE|ANTARES|ANTARES|20251106120000||ADT^A08^ADT_A01|MSG005|P|2.5^FRA^2.11|||||FRA|8859/1
EVN||20251106120000|20251106120000||pat^INCONNU^INCONNU^^^^^^CPAGE&1.2.250.1.154&ISO|20251106120000
PID|||000059478005^^^CPAGE&1.2.250.1.211.10.200.2&ISO^PI||ROBERT^SOPHIE^^^Mme^^D||19880710|F
PV1||O|7700|R|||101005344^PICQUE^JEAN BAPTISTE^^^^^^ASIP-SANTE-PS&1.2.250.1.71.4.2.1&ISO^L^^^ADELI|||||||A||1|||||MSG005^^^CPAGE&1.2.250.1.211.12.1.2&L^VN|||N"""
    
    session = Session(engine)
    try:
        ght, ej, endpoint = await setup_test_data(session)
        
        # Tester l'intégration
        ack_message = await on_message_inbound_async(message, session, endpoint)
        
        # Analyser l'ACK pour vérifier le rejet
        if "MSA|AE|" in ack_message and "ZBE obligatoire" in ack_message:
            print("\n✅ Message rejeté comme prévu")
            print(f"   Message d'erreur : {ack_message.split('ERR|')[1][:150] if 'ERR|' in ack_message else 'Vérifier ACK'}")
        else:
            print(f"\n❌ Message non rejeté correctement!")
            print(f"   ACK: {ack_message[:200]}...")
            
    finally:
        await cleanup_test_data(session)
        session.close()


async def test_a28_without_zbe():
    """Test : Message A28 (identité) sans segment ZBE (doit être accepté car A28 est un message d'identité)"""
    print("\n" + "="*80)
    print("TEST 6: Message A28 (add patient) sans segment ZBE (OK car message d'identité)")
    print("="*80)
    
    # Message A28 (ajout patient) SANS segment ZBE - OK car A28 n'est pas un message de mouvement
    message = """MSH|^~\\&|CPAGE|CPAGE|ANTARES|ANTARES|20251106120000||ADT^A28^ADT_A05|MSG006|P|2.5^FRA^2.11|||||FRA|8859/1
EVN||20251106120000|20251106120000||pat^INCONNU^INCONNU^^^^^^CPAGE&1.2.250.1.154&ISO|20251106120000
PID|||000059478006^^^CPAGE&1.2.250.1.211.10.200.2&ISO^PI||PETIT^CLAIRE^^^Mme^^D||19920225|F"""
    
    session = Session(engine)
    try:
        ght, ej, endpoint = await setup_test_data(session)
        
        # Tester l'intégration
        ack_message = await on_message_inbound_async(message, session, endpoint)
        
        # A28 ne nécessite pas ZBE (c'est un message d'identité, pas de mouvement)
        if "ZBE obligatoire" in ack_message:
            print(f"\n❌ Message rejeté pour segment ZBE manquant alors que A28 ne le requiert pas!")
            print(f"   ACK: {ack_message[:200]}...")
        else:
            print("\n✅ Message non rejeté pour ZBE manquant (correct pour A28)")
            if "MSA|AA|" in ack_message:
                print("   → Message accepté")
            else:
                print(f"   → Message peut être rejeté pour d'autres raisons")
                print(f"   ACK: {ack_message[:150]}...")
            
    finally:
        await cleanup_test_data(session)
        session.close()


async def main():
    """Point d'entrée principal"""
    print("\n" + "="*80)
    print("TEST VALIDATION DES SEGMENTS OBLIGATOIRES ZBE ET MRG")
    print("="*80)
    
    await test_missing_zbe_segment()
    await test_valid_zbe_segment()
    await test_missing_mrg_segment()
    await test_valid_mrg_segment()
    await test_a08_without_zbe()
    await test_a28_without_zbe()
    
    print("\n" + "="*80)
    print("TESTS TERMINÉS")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
