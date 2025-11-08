"""
Test de validation de l'UF Responsable dans les messages PAM
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
    """Créer une structure de test avec une UF"""
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
    
    # Créer un Pole
    from app.models_structure import Pole, EntiteGeographique
    
    entite_geo = EntiteGeographique(
        identifier="EG_TEST",
        name="Entité Géographique Test",
        physical_type="bu",  # Building
        finess="210000124",  # FINESS géographique
        entite_juridique_id=ej.id
    )
    session.add(entite_geo)
    session.flush()
    
    pole = Pole(
        identifier="POLE_TEST",
        name="Pôle Test",
        physical_type="wa",  # Ward
        entite_geo_id=entite_geo.id
    )
    session.add(pole)
    session.flush()
    
    # Créer un Service
    service = Service(
        identifier="7700",
        name="Cardiologie",
        physical_type="wa",  # Ward
        service_type="550",  # Type de service
        pole_id=pole.id
    )
    session.add(service)
    session.flush()
    
    # Créer une UF valide
    uf_valid = UniteFonctionnelle(
        identifier="890975527",  # Code UF du message de test
        name="UF Cardiologie",
        physical_type="ro",  # Room
        service_id=service.id
    )
    session.add(uf_valid)
    session.flush()
    
    print(f"✅ GHT créé: {ght.name} (ID={ght.id})")
    print(f"✅ EJ créée: {ej.name} (ID={ej.id}, FINESS={ej.finess_ej})")
    print(f"✅ Entité Géographique créée: {entite_geo.name} (ID={entite_geo.id})")
    print(f"✅ Pôle créé: {pole.name} (ID={pole.id})")
    print(f"✅ Service créé: {service.name} (ID={service.id}, Code={service.identifier})")
    print(f"✅ UF créée: {uf_valid.name} (ID={uf_valid.id}, Code={uf_valid.identifier})")
    
    # Créer un endpoint factice pour le test
    endpoint = SystemEndpoint(
        name="Test Endpoint",
        kind="MLLP",
        role="RECEIVER",
        entite_juridique_id=ej.id
    )
    session.add(endpoint)
    session.flush()
    print(f"✅ Endpoint créé: {endpoint.name} (ID={endpoint.id})")
    
    return ght, ej, entite_geo, pole, service, uf_valid, endpoint


async def cleanup_test_data(session: Session):
    """Nettoyer les données de test"""
    print("\n" + "="*80)
    print("CLEANUP: Suppression des données de test")
    print("="*80)
    
    from app.models_structure import Pole, EntiteGeographique
    
    # Supprimer dans l'ordre inverse des dépendances
    session.exec(delete(Mouvement))
    session.exec(delete(Venue))
    session.exec(delete(Dossier))
    session.exec(delete(Patient))
    session.exec(delete(SystemEndpoint))
    session.exec(delete(UniteFonctionnelle))
    session.exec(delete(Service))
    session.exec(delete(Pole))
    session.exec(delete(EntiteGeographique))
    session.exec(delete(EntiteJuridique))
    session.exec(delete(GHTContext))
    session.commit()
    print("✅ Données nettoyées")


async def test_valid_uf():
    """Test avec UF valide"""
    print("\n" + "="*80)
    print("TEST 1: Message avec UF valide")
    print("="*80)
    
    message = """MSH|^~\\&|CPAGE|CPAGE|ANTARES|ANTARES|20251103155012||ADT^A01^ADT_A01|1117925483|P|2.5^FRA^2.11|||||FRA|8859/1
EVN||20251103155012|20251027090000||pat^INCONNU^INCONNU^^^^^^CPAGE&1.2.250.1.154&ISO|20251027090000
PID|||000059478073^^^CPAGE&1.2.250.1.211.10.200.2&ISO^PI||TISSIER^MATHILDE^^^Mme^^D~TISSIER^MATHILDE^MATHILDE^^Mme^^L||19901010|F
PV1||O|7700|R|||101005344^PICQUE^JEAN BAPTISTE^^^^^^ASIP-SANTE-PS&1.2.250.1.71.4.2.1&ISO^L^^^ADELI|||||||A||1|||||4159625^^^CPAGE&1.2.250.1.211.12.1.2&L^VN|||N
ZBE|12565133^CPAGE^1.2.250.1.211.12.1.2^ISO|20251027090000||INSERT|N|A01|^^^^^^UF^^^890975527||M"""
    
    session = Session(engine)
    try:
        ght, ej, entite_geo, pole, service, uf_valid, endpoint = await setup_test_data(session)
        
        # Tester l'intégration
        ack_message = await on_message_inbound_async(message, session, endpoint)
        
        # Analyser l'ACK pour vérifier le succès
        if "MSA|AA|" in ack_message:  # ACK Accept
            print("\n✅ Message intégré avec succès")
            print(f"   ACK: {ack_message[:100]}...")
            
            # Vérifier que le mouvement a bien l'UF
            mouvement = session.exec(
                select(Mouvement).order_by(Mouvement.id.desc())
            ).first()
            
            if mouvement:
                venue = mouvement.venue
                dossier = venue.dossier
                print(f"\n📊 Données créées:")
                print(f"   - Dossier UF: {dossier.uf_responsabilite}")
                print(f"   - Venue UF: {venue.uf_responsabilite}")
                print(f"   - Mouvement location: {mouvement.location}")
                print(f"   - Mouvement when: {mouvement.when}")
        else:
            print(f"\n❌ Échec intégration")
            print(f"   ACK: {ack_message[:200]}...")
            
    finally:
        await cleanup_test_data(session)
        session.close()


async def test_invalid_uf():
    """Test avec UF invalide (non existante)"""
    print("\n" + "="*80)
    print("TEST 2: Message avec UF invalide")
    print("="*80)
    
    # Message avec une UF qui n'existe pas (code différent)
    message = """MSH|^~\\&|CPAGE|CPAGE|ANTARES|ANTARES|20251103155012||ADT^A01^ADT_A01|1117925484|P|2.5^FRA^2.11|||||FRA|8859/1
EVN||20251103155012|20251027090000||pat^INCONNU^INCONNU^^^^^^CPAGE&1.2.250.1.154&ISO|20251027090000
PID|||000059478074^^^CPAGE&1.2.250.1.211.10.200.2&ISO^PI||MARTIN^PAUL^^^M^^D||19850515|M
PV1||O|7700|R|||101005344^PICQUE^JEAN BAPTISTE^^^^^^ASIP-SANTE-PS&1.2.250.1.71.4.2.1&ISO^L^^^ADELI|||||||A||1|||||4159626^^^CPAGE&1.2.250.1.211.12.1.2&L^VN|||N
ZBE|12565134^CPAGE^1.2.250.1.211.12.1.2^ISO|20251027090000||INSERT|N|A01|^^^^^^UF^^^UF_INVALIDE||M"""
    
    session = Session(engine)
    try:
        ght, ej, entite_geo, pole, service, uf_valid, endpoint = await setup_test_data(session)
        
        # Tester l'intégration
        ack_message = await on_message_inbound_async(message, session, endpoint)
        
        # Analyser l'ACK pour vérifier le rejet
        if "MSA|AE|" in ack_message:  # ACK Error
            print("\n✅ Message rejeté comme prévu")
            # Extraire le message d'erreur
            lines = ack_message.split("\r")
            for line in lines:
                if line.startswith("ERR|"):
                    print(f"   Erreur: {line}")
            
            if "UF Responsable" in ack_message and "introuvable" in ack_message:
                print("\n✅ Message d'erreur explicite correct")
            else:
                print(f"\n⚠️  Message d'erreur inattendu")
                print(f"   ACK complet: {ack_message}")
        else:
            print(f"\n❌ Message accepté alors qu'il devrait être rejeté!")
            print(f"   ACK: {ack_message[:100]}...")
            
    finally:
        await cleanup_test_data(session)
        session.close()


async def main():
    """Point d'entrée principal"""
    print("\n" + "="*80)
    print("TEST VALIDATION UF RESPONSABLE")
    print("="*80)
    
    await test_valid_uf()
    await test_invalid_uf()
    
    print("\n" + "="*80)
    print("TESTS TERMINÉS")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
