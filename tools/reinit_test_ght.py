#!/usr/bin/env python3
"""
Script pour réinitialiser UNIQUEMENT le GHT de test (code=TEST_GHT).
Ne touche pas aux autres GHT qui pourraient exister.
"""

import sys
from pathlib import Path

# Assurer que le module app est accessible
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from app.db import engine
from app.models_structure_fhir import GHTContext, IdentifierNamespace
from app.models_endpoints import SystemEndpoint
from app.vocabulary_init import init_vocabularies
from app.services.structure_seed import ensure_demo_structure


def init_test_ght_namespaces(session: Session) -> GHTContext:
    """Initialise ou met à jour le GHT de test avec ses namespaces."""
    # Chercher le GHT de test
    ght = session.exec(
        select(GHTContext).where(GHTContext.code == "TEST_GHT")
    ).first()
    
    if not ght:
        print("✗ GHT de test non trouvé (code=TEST_GHT)")
        print("  Création d'un nouveau GHT de test...")
        ght = GHTContext(
            name="Test GHT",
            code="TEST_GHT",
            description="GHT de test pour validation et développement",
            oid_racine="1.2.250.1.213.1.1.1",
            fhir_server_url="http://localhost:8000/fhir",
            is_active=True
        )
        session.add(ght)
        session.commit()
        session.refresh(ght)
        print(f"✓ GHT de test créé (id={ght.id})")
    else:
        print(f"✓ GHT de test trouvé: {ght.name} (id={ght.id})")
    
    # Créer/vérifier les espaces de noms
    namespaces_config = [
        {
            "name": "CPAGE",
            "description": "Identifiants CPAGE",
            "oid": "1.2.250.1.211.10.200.2",
            "system": "urn:oid:1.2.250.1.211.10.200.2",
            "type": "PI"
        },
        {
            "name": "IPP",
            "description": "Identifiant Patient Permanent",
            "oid": "1.2.250.1.213.1.1.1.1",
            "system": "urn:oid:1.2.250.1.213.1.1.1.1",
            "type": "IPP"
        },
        {
            "name": "NDA",
            "description": "Numéro de Dossier Administratif",
            "oid": "1.2.250.1.213.1.1.1.2",
            "system": "urn:oid:1.2.250.1.213.1.1.1.2",
            "type": "NDA"
        },
        {
            "name": "VENUE",
            "description": "Identifiant de venue/séjour",
            "oid": "1.2.250.1.213.1.1.1.3",
            "system": "urn:oid:1.2.250.1.213.1.1.1.3",
            "type": "VN"
        },
        {
            "name": "MOUVEMENT",
            "description": "Identifiant de mouvement patient (ZBE-1)",
            "oid": "1.2.250.1.213.1.1.1.4",
            "system": "urn:oid:1.2.250.1.213.1.1.1.4",
            "type": "MVT"
        },
        {
            "name": "FINESS",
            "description": "Numéro FINESS des établissements",
            "oid": "1.2.250.1.71.4.2.2",
            "system": "urn:oid:1.2.250.1.71.4.2.2",
            "type": "FINESS"
        }
    ]
    
    ns_count = 0
    for ns_config in namespaces_config:
        ns = session.exec(
            select(IdentifierNamespace).where(
                IdentifierNamespace.name == ns_config["name"],
                IdentifierNamespace.ght_context_id == ght.id
            )
        ).first()
        
        if not ns:
            print(f"  • Création namespace {ns_config['name']}...")
            ns = IdentifierNamespace(
                name=ns_config["name"],
                description=ns_config["description"],
                oid=ns_config["oid"],
                system=ns_config["system"],
                type=ns_config["type"],
                ght_context_id=ght.id,
                is_active=True
            )
            session.add(ns)
            ns_count += 1
        else:
            print(f"  ✓ Namespace {ns_config['name']} existe déjà")
    
    if ns_count > 0:
        session.commit()
        print(f"✓ {ns_count} nouveaux namespaces créés")
    
    return ght


def init_test_endpoints(session: Session, ght: GHTContext) -> None:
    """Crée les endpoints de test s'ils n'existent pas."""
    endpoints_config = [
        {
            "name": "MLLP Receiver Test",
            "kind": "mllp",
            "role": "receiver",
            "host": "127.0.0.1",
            "port": 2575,
            "sending_app": "EXTERNAL_SYS",
            "sending_facility": "EXTERNAL_FACILITY",
            "receiving_app": "MedBridge",
            "receiving_facility": "TEST-GHT",
            "pam_validate_enabled": True,
            "pam_validate_mode": "warn",
            "pam_profile": "IHE_PAM_FR",
            "description": "Endpoint MLLP de test pour réception IHE PAM"
        },
        {
            "name": "MLLP Sender Test",
            "kind": "mllp",
            "role": "sender",
            "host": "127.0.0.1",
            "port": 2576,
            "sending_app": "MedBridge",
            "sending_facility": "TEST-GHT",
            "receiving_app": "TARGET_SYS",
            "receiving_facility": "TARGET_FACILITY",
            "description": "Endpoint MLLP de test pour émission HL7"
        },
        {
            "name": "FHIR Receiver Test",
            "kind": "fhir",
            "role": "receiver",
            "base_url": "http://127.0.0.1:8000/fhir",
            "auth_kind": "none",
            "description": "Endpoint FHIR de test pour réception"
        },
        {
            "name": "FHIR Sender Test",
            "kind": "fhir",
            "role": "sender",
            "base_url": "http://127.0.0.1:8080/fhir",
            "auth_kind": "none",
            "description": "Endpoint FHIR de test pour émission"
        }
    ]
    
    created_count = 0
    for ep_config in endpoints_config:
        existing = session.exec(
            select(SystemEndpoint).where(
                SystemEndpoint.name == ep_config["name"],
                SystemEndpoint.ght_context_id == ght.id
            )
        ).first()
        
        if existing:
            print(f"  ✓ Endpoint '{ep_config['name']}' existe déjà")
            continue
        
        endpoint_data = {
            "name": ep_config["name"],
            "kind": ep_config["kind"],
            "role": ep_config["role"],
            "ght_context_id": ght.id,
            "is_enabled": True,
        }
        
        if ep_config["kind"] == "mllp":
            endpoint_data.update({
                "host": ep_config.get("host"),
                "port": ep_config.get("port"),
                "sending_app": ep_config.get("sending_app"),
                "sending_facility": ep_config.get("sending_facility"),
                "receiving_app": ep_config.get("receiving_app"),
                "receiving_facility": ep_config.get("receiving_facility"),
                "pam_validate_enabled": ep_config.get("pam_validate_enabled", False),
                "pam_validate_mode": ep_config.get("pam_validate_mode"),
                "pam_profile": ep_config.get("pam_profile"),
            })
        elif ep_config["kind"] == "fhir":
            endpoint_data.update({
                "base_url": ep_config.get("base_url"),
                "auth_kind": ep_config.get("auth_kind", "none"),
            })
        
        if "description" in ep_config:
            endpoint_data["description"] = ep_config["description"]
        
        endpoint = SystemEndpoint(**endpoint_data)
        session.add(endpoint)
        created_count += 1
        print(f"  • Endpoint '{ep_config['name']}' créé")
    
    if created_count > 0:
        session.commit()
        print(f"✓ {created_count} nouveaux endpoints créés")


def main():
    print("="*70)
    print("RÉINITIALISATION DU GHT DE TEST UNIQUEMENT")
    print("="*70)
    print("\n⚠️  Ce script ne touche QUE au GHT avec code=TEST_GHT")
    print("   Les autres GHT restent intacts.\n")
    
    with Session(engine) as session:
        # Étape 1: Vérifier/créer le GHT de test et ses namespaces
        print("[1/4] Initialisation du GHT de test et namespaces...")
        ght = init_test_ght_namespaces(session)
        ght_id = ght.id  # Sauvegarder l'ID avant de fermer la session
        
        # Étape 2: Créer les endpoints de test
        print("\n[2/4] Initialisation des endpoints de test...")
        try:
            init_test_endpoints(session, ght)
        except Exception as e:
            print(f"  ⚠️  Erreur lors de la création des endpoints: {e}")
            import traceback
            traceback.print_exc()
        
        # Étape 3: Initialiser les vocabulaires (pour tous les GHT, mais sans doublon)
        print("\n[3/4] Initialisation des vocabulaires...")
        try:
            init_vocabularies(session)
            print("  ✓ Vocabulaires initialisés")
        except Exception as e:
            print(f"  ⚠️  Erreur lors de l'initialisation des vocabulaires: {e}")
            import traceback
            traceback.print_exc()
        
        # Étape 4: Initialiser la structure de démo pour le GHT de test
        print("\n[4/4] Seeding de la structure de démonstration...")
        try:
            ensure_demo_structure(session, ght)
            print("  ✓ Structure de démonstration créée")
        except Exception as e:
            print(f"  ⚠️  Erreur lors du seeding de la structure: {e}")
            import traceback
            traceback.print_exc()
    
    # Affichage final
    with Session(engine) as display_session:
        ght_display = display_session.exec(
            select(GHTContext).where(GHTContext.id == ght_id)
        ).first()
        
        if ght_display:
            print("\n" + "="*70)
            print("✓ RÉINITIALISATION DU GHT DE TEST TERMINÉE")
            print("="*70)
            print(f"\nGHT mis à jour: {ght_display.name}")
            print(f"  • ID: {ght_display.id}")
            print(f"  • Code: {ght_display.code}")
            print(f"  • OID racine: {ght_display.oid_racine or 'Non défini'}")
            print(f"  • URL FHIR: {ght_display.fhir_server_url or 'Non défini'}")
            print()


if __name__ == "__main__":
    main()
