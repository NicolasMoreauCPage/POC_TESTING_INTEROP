#!/usr/bin/env python3
"""
Applique la migration 003 : ajout de la colonne 'type' sur la table mouvement
et pré-remplissage à partir de trigger_event.

Usage:
    python tools/apply_migration_003.py
"""
import sys
from pathlib import Path

# Ajouter le répertoire racine au path pour importer les modules app
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, text
from app.db import engine

def apply_migration_003():
    print("🔄 Début de la migration 003...")
    with Session(engine) as session:
        # Vérifier si la colonne existe déjà
        result = session.exec(text("PRAGMA table_info(mouvement)"))
        columns = [row[1] for row in result.fetchall()]
        if 'type' in columns:
            print("✅ La colonne 'type' existe déjà. Migration 003 déjà appliquée.")
            return
        # Lire le fichier SQL
        migration_file = Path(__file__).parent.parent / "migrations" / "003_add_mouvement_type.sql"
        if not migration_file.exists():
            print(f"❌ Fichier de migration introuvable: {migration_file}")
            sys.exit(1)
        sql_content = migration_file.read_text(encoding="utf-8")
        # Exécuter chaque instruction séparément
        for stmt in [s.strip() for s in sql_content.split(';') if s.strip()]:
            print(f"  Exécution: {stmt[:60]}...")
            session.exec(text(stmt))
        session.commit()
        # Vérification
        result = session.exec(text("PRAGMA table_info(mouvement)"))
        columns = [row[1] for row in result.fetchall()]
        if 'type' in columns:
            print("✅ Colonne 'type' ajoutée avec succès.")
        else:
            print("❌ Échec de l'ajout de la colonne 'type'.")
            sys.exit(1)
        # Statistiques rapides
        total = session.exec(text("SELECT COUNT(*) FROM mouvement")).first()[0]
        filled = session.exec(text("SELECT COUNT(*) FROM mouvement WHERE type IS NOT NULL AND type <> ''")).first()[0]
        print(f"📊 Mouvements: {total} (avec type: {filled})")
        print("✅ Migration 003 appliquée avec succès!")

if __name__ == "__main__":
    apply_migration_003()
