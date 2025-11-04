"""Script d'initialisation complète de la base de données de démonstration"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from sqlmodel import Session, select, SQLModel
from app.db import engine
from app.models_structure_fhir import GHTContext, IdentifierNamespace

def init_complete_demo():
    """Initialise une base complète avec un seul GHT contenant tout"""
    
    # Créer les tables
    print("Création des tables...")
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Chercher ou créer le GHT unique
        ght = session.exec(
            select(GHTContext).where(GHTContext.code == "GHT-DEMO-INTEROP")
        ).first()
        
        if not ght:
            print("Création du GHT Démo Interop...")
            ght = GHTContext(
                name="GHT Démo Interop",
                code="GHT-DEMO-INTEROP",
                description="GHT de démonstration complet pour tests d'interopérabilité",
                oid_racine="1.2.250.1.213.1.1.1",
                fhir_server_url="http://localhost:8000/fhir",
                is_active=True
            )
            session.add(ght)
            session.commit()
            session.refresh(ght)
            print(f"✓ GHT créé (id={ght.id})")
        else:
            print(f"✓ GHT existant trouvé (id={ght.id})")
        
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
                "name": "FINESS",
                "description": "Numéro FINESS des établissements",
                "oid": "1.2.250.1.71.4.2.2",
                "system": "urn:oid:1.2.250.1.71.4.2.2",
                "type": "FINESS"
            }
        ]
        
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
            else:
                print(f"  ✓ Namespace {ns_config['name']} existe déjà")
        
        session.commit()
        
        print("\n" + "="*60)
        print(f"Configuration terminée !")
        print(f"GHT: {ght.name} (id={ght.id}, code={ght.code})")
        print(f"Namespaces: {len(namespaces_config)} configurés")
        print("="*60)
        
        return ght.id

if __name__ == "__main__":
    init_complete_demo()
