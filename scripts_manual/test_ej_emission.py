"""
Test de l'émission automatique pour EntiteJuridique
"""
import asyncio
from datetime import datetime
from app.db import engine, Session, init_db
from app.models_structure_fhir import EntiteJuridique, GHTContext
from app.models_structure import EntiteGeographique
from sqlmodel import select, delete


async def test_ej_emission():
    """Test de création d'une EJ pour vérifier l'émission"""
    print("\n" + "="*80)
    print("TEST ÉMISSION AUTOMATIQUE ENTITÉ JURIDIQUE")
    print("="*80)
    
    # S'assurer que les tables existent
    init_db()
    
    session = Session(engine)
    
    try:
        # Créer un GHT si nécessaire
        ght = session.exec(select(GHTContext).where(GHTContext.code == "GHT-TEST-EMIT")).first()
        if not ght:
            ght = GHTContext(
                name="GHT Test Émission",
                code="GHT-TEST-EMIT",
                description="GHT de test pour émission"
            )
            session.add(ght)
            session.commit()
            session.refresh(ght)
            print(f"✓ GHT créé: {ght.name} (ID={ght.id})")
        else:
            print(f"✓ GHT existant: {ght.name} (ID={ght.id})")
        
        # Test 1: Créer une nouvelle EJ
        print("\n[TEST 1] Création d'une nouvelle Entité Juridique...")
        ej_test = EntiteJuridique(
            name="Hopital Test Émission",
            finess_ej="999888777",
            short_name="HTE",
            ght_context_id=ght.id
        )
        session.add(ej_test)
        
        print("  → Commit de la transaction...")
        session.commit()
        session.refresh(ej_test)
        
        print(f"✓ EJ créée avec succès:")
        print(f"  - ID: {ej_test.id}")
        print(f"  - Nom: {ej_test.name}")
        print(f"  - FINESS: {ej_test.finess_ej}")
        
        # Attendre un peu pour que les émissions asynchrones se terminent
        print("\n  → Attente des émissions asynchrones (2 secondes)...")
        await asyncio.sleep(2)
        
        # Test 2: Créer une EG (qui devrait émettre FHIR + MFN)
        print("\n[TEST 2] Création d'une Entité Géographique (pour comparaison)...")
        eg_test = EntiteGeographique(
            identifier="EG-TEST-EMIT",
            name="Entité Géo Test",
            finess="999888778",
            physical_type="bu",
            entite_juridique_id=ej_test.id
        )
        session.add(eg_test)
        
        print("  → Commit de la transaction...")
        session.commit()
        session.refresh(eg_test)
        
        print(f"✓ EG créée avec succès:")
        print(f"  - ID: {eg_test.id}")
        print(f"  - Nom: {eg_test.name}")
        
        print("\n  → Attente des émissions asynchrones (2 secondes)...")
        await asyncio.sleep(2)
        
        # Vérifier les logs d'émission
        from app.models_endpoints import MessageLog
        
        print("\n" + "="*80)
        print("LOGS D'ÉMISSION")
        print("="*80)
        
        logs = session.exec(
            select(MessageLog)
            .where(MessageLog.direction == "out")
            .order_by(MessageLog.id.desc())
            .limit(5)
        ).all()
        
        if logs:
            print(f"\n{len(logs)} derniers messages émis:")
            for log in logs:
                print(f"\n  Message ID={log.id}:")
                print(f"    - Type: {log.kind}")
                print(f"    - Statut: {log.status}")
                print(f"    - Type message: {log.message_type}")
                print(f"    - Endpoint: {log.endpoint_id}")
                print(f"    - Payload: {log.payload[:100] if log.payload else 'N/A'}...")
        else:
            print("\n⚠️  Aucun message émis trouvé")
            print("     → Vérifiez qu'il y a des endpoints 'sender' configurés")
        
        # Nettoyage
        print("\n" + "="*80)
        print("NETTOYAGE")
        print("="*80)
        
        session.delete(eg_test)
        session.delete(ej_test)
        session.commit()
        print("✓ Données de test supprimées")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()
    
    print("\n" + "="*80)
    print("TEST TERMINÉ")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_ej_emission())
