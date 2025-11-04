#!/usr/bin/env python3
"""
Initialise un endpoint MLLP sur le port 2575 pour les tests IHE PAM
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import engine, Session
from app.models_shared import SystemEndpoint, EndpointKind, EndpointRole
from sqlmodel import select, delete
import requests
import time


def init_mllp_endpoint():
    """Crée un endpoint MLLP sur port 2575"""
    with Session(engine) as session:
        # Supprimer l'ancien endpoint s'il existe
        existing = session.exec(
            select(SystemEndpoint).where(SystemEndpoint.port == 2575)
        ).first()
        
        if existing:
            print(f"✅ Endpoint MLLP existe déjà: id={existing.id}, port={existing.port}")
            return existing.id
        
        # Créer un nouvel endpoint
        endpoint = SystemEndpoint(
            name="IHE_PAM_Test_Endpoint",
            description="Endpoint MLLP pour tests IHE PAM avec segments ZBE",
            kind=EndpointKind.MLLP,
            role=EndpointRole.RECEIVER,
            host="0.0.0.0",
            port=2575,
            enabled=True,
        )
        session.add(endpoint)
        session.commit()
        session.refresh(endpoint)
        
        print(f"✅ Endpoint MLLP créé: id={endpoint.id}, port={endpoint.port}")
        return endpoint.id


def start_mllp_server(endpoint_id: int):
    """Démarre le serveur MLLP via l'API"""
    print(f"\nDémarrage du serveur MLLP (endpoint_id={endpoint_id})...")
    
    try:
        response = requests.post(
            f"http://localhost:8000/interop/mllp/start/{endpoint_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Serveur MLLP démarré: {data}")
            return True
        else:
            print(f"❌ Échec démarrage: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Erreur démarrage: {e}")
        return False


def main():
    print("="*80)
    print("Initialisation endpoint MLLP pour tests IHE PAM")
    print("="*80)
    
    # Étape 1: Créer l'endpoint
    endpoint_id = init_mllp_endpoint()
    
    # Étape 2: Attendre que le serveur FastAPI soit prêt
    print(f"\nVérification serveur FastAPI...")
    for i in range(5):
        try:
            r = requests.get("http://localhost:8000/docs", timeout=2)
            if r.status_code == 200:
                print(f"✅ Serveur FastAPI prêt")
                break
        except:
            print(f"⏳ Attente serveur FastAPI... ({i+1}/5)")
            time.sleep(2)
    else:
        print(f"❌ Serveur FastAPI non accessible")
        print(f"   Veuillez démarrer: uvicorn app.app:app --reload")
        return
    
    # Étape 3: Démarrer le serveur MLLP
    if start_mllp_server(endpoint_id):
        print(f"\n{'='*80}")
        print(f"✅ Endpoint MLLP prêt sur port 2575")
        print(f"{'='*80}")
        print(f"\nVous pouvez maintenant lancer les tests:")
        print(f"  python3 tools/test_ihe_pam_with_zbe.py")
        print()
    else:
        print(f"\n❌ Échec démarrage serveur MLLP")
        print(f"   Vérifiez les logs du serveur FastAPI")


if __name__ == "__main__":
    main()
