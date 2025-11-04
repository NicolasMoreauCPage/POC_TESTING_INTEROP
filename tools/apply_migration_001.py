#!/usr/bin/env python3
"""
Script d'application de la migration 001: ajout champs Patient et contrainte Identifier.

Usage:
    python tools/apply_migration_001.py
"""
import sys
from pathlib import Path
from sqlmodel import Session, text

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import engine  # Utiliser l'engine existant


def apply_migration():
    """Applique la migration 001 sur la base de données."""
    print("=" * 70)
    print("Migration 001: Add patient birth address and identity reliability")
    print("=" * 70)
    
    # Lire le fichier SQL
    migration_file = Path(__file__).parent.parent / "migrations" / "001_add_patient_birth_address_and_identity.sql"
    
    if not migration_file.exists():
        print(f"❌ Fichier de migration introuvable: {migration_file}")
        sys.exit(1)
    
    with open(migration_file, "r", encoding="utf-8") as f:
        sql_content = f.read()
    
    # Extraire seulement les commandes SQL (ignorer les commentaires de doc)
    sql_commands = []
    for line in sql_content.split("\n"):
        line = line.strip()
        # Ignorer lignes vides et commentaires de documentation
        if not line or line.startswith("--"):
            continue
        sql_commands.append(line)
    
    sql_script = "\n".join(sql_commands)
    
    # Séparer par les sections principales
    parts = sql_script.split("ALTER TABLE")
    
    with Session(engine) as session:
        try:
            print("\n📋 Étape 1: Ajout des colonnes Patient...")
            
            # Liste des ALTER TABLE à exécuter
            alter_commands = [
                "ALTER TABLE patient ADD COLUMN country TEXT",
                "ALTER TABLE patient ADD COLUMN birth_address TEXT",
                "ALTER TABLE patient ADD COLUMN birth_city TEXT",
                "ALTER TABLE patient ADD COLUMN birth_state TEXT",
                "ALTER TABLE patient ADD COLUMN birth_postal_code TEXT",
                "ALTER TABLE patient ADD COLUMN birth_country TEXT",
                "ALTER TABLE patient ADD COLUMN identity_reliability_code TEXT",
                "ALTER TABLE patient ADD COLUMN identity_reliability_date TIMESTAMP",
                "ALTER TABLE patient ADD COLUMN identity_reliability_source TEXT"
            ]
            
            for cmd in alter_commands:
                try:
                    session.exec(text(cmd))
                    col_name = cmd.split("ADD COLUMN")[1].split()[0]
                    print(f"  ✓ Colonne ajoutée: {col_name}")
                except Exception as e:
                    # Si colonne existe déjà, continuer
                    if "duplicate column name" in str(e).lower():
                        col_name = cmd.split("ADD COLUMN")[1].split()[0]
                        print(f"  ⚠ Colonne déjà présente: {col_name}")
                    else:
                        raise
            
            print("\n📋 Étape 2: Ajout de la contrainte UNIQUE sur Identifier...")
            
            # Créer index unique
            index_sql = """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_identifier_unique_per_system 
                ON identifier(value, system, oid) 
                WHERE status = 'active' AND patient_id IS NOT NULL
            """
            
            session.exec(text(index_sql))
            print("  ✓ Index unique créé: idx_identifier_unique_per_system")
            
            # Commit
            session.commit()
            
            print("\n📋 Étape 3: Vérification post-migration...")
            
            # Vérifier colonnes ajoutées
            result = session.exec(text("""
                SELECT 
                    COUNT(*) as total_patients,
                    COUNT(country) as has_country,
                    COUNT(birth_address) as has_birth_address,
                    COUNT(identity_reliability_code) as has_identity_code
                FROM patient
            """)).first()
            
            if result:
                print(f"  ✓ Total patients: {result[0]}")
                print(f"  ✓ Avec country: {result[1]}")
                print(f"  ✓ Avec birth_address: {result[2]}")
                print(f"  ✓ Avec identity_reliability_code: {result[3]}")
            
            # Vérifier index
            index_check = session.exec(text("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name='idx_identifier_unique_per_system'
            """)).first()
            
            if index_check:
                print(f"  ✓ Index UNIQUE vérifié: {index_check[0]}")
            
            print("\n✅ Migration 001 appliquée avec succès!")
            print("=" * 70)
            
        except Exception as e:
            print(f"\n❌ Erreur lors de la migration: {e}")
            session.rollback()
            sys.exit(1)


if __name__ == "__main__":
    apply_migration()
