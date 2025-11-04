#!/usr/bin/env python3
"""
Applique la migration 002 : ajout champs téléphones multiples et nom de naissance.

Usage:
    python tools/apply_migration_002.py

Cette migration ajoute :
- birth_family: nom de naissance (PID-5 répétition type L)
- mobile: téléphone mobile (PID-13 répétition type CP/CELL)
- work_phone: téléphone professionnel (PID-13 répétition type WP/WORK)
"""
import sys
from pathlib import Path

# Ajouter le répertoire racine au path pour importer les modules app
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select, text
from app.db import engine
from app.models import Patient


def apply_migration_002():
    """Applique la migration 002 pour ajouter les nouveaux champs Patient."""
    
    print("🔄 Début de la migration 002...")
    
    with Session(engine) as session:
        # Vérifier si les colonnes existent déjà (SQLite)
        result = session.exec(text("PRAGMA table_info(patient)"))
        columns = [row[1] for row in result.fetchall()]  # row[1] contient le nom de colonne
        
        existing_columns = [col for col in ['birth_family', 'mobile', 'work_phone'] if col in columns]
        
        if len(existing_columns) == 3:
            print("✅ Les colonnes existent déjà. Migration 002 déjà appliquée.")
            return
        
        print(f"📊 Colonnes existantes parmi les nouvelles: {existing_columns}")
        
        # Lire et exécuter le fichier SQL de migration
        migration_file = Path(__file__).parent.parent / "migrations" / "002_add_patient_phones_and_birth_family.sql"
        
        if not migration_file.exists():
            print(f"❌ Fichier de migration introuvable: {migration_file}")
            return
        
        print(f"📄 Lecture de {migration_file}...")
        sql_content = migration_file.read_text()
        
        # SQLite ne supporte pas COMMENT, on les retire
        sql_lines = [
            line for line in sql_content.split('\n')
            if not line.strip().startswith('COMMENT ON')
            and not line.strip().startswith('--')
            and line.strip()
        ]
        
        # Exécuter chaque ALTER TABLE séparément
        for line in sql_lines:
            if line.strip():
                try:
                    print(f"  Exécution: {line[:60]}...")
                    session.exec(text(line))
                except Exception as e:
                    # Si colonne existe déjà, continuer
                    if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                        print(f"  ⚠️  Colonne déjà présente, ignorée")
                    else:
                        raise
        
        session.commit()
        
        # Vérifier que les colonnes ont été créées (SQLite)
        result = session.exec(text("PRAGMA table_info(patient)"))
        columns = [row[1] for row in result.fetchall()]
        new_columns = [col for col in ['birth_family', 'mobile', 'work_phone'] if col in columns]
        
        print(f"\n✅ Migration 002 appliquée avec succès!")
        print(f"📊 Nouvelles colonnes ajoutées: {new_columns}")
        
        # Compter les patients
        patients = session.exec(select(Patient)).all()
        print(f"👥 Nombre de patients dans la base: {len(patients)}")


if __name__ == "__main__":
    try:
        apply_migration_002()
    except Exception as e:
        print(f"\n❌ Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
