#!/usr/bin/env python3
"""
Applique la migration 010 : Ajout des champs UF et nature aux mouvements
"""
import sqlite3
from pathlib import Path

def apply_migration_010():
    db_path = Path("meddata.db")
    
    if not db_path.exists():
        print("❌ Base de données non trouvée. Exécutez d'abord l'initialisation.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Lire le fichier SQL de migration
    migration_file = Path("migrations/010_add_mouvement_uf_fields.sql")
    with open(migration_file, "r", encoding="utf-8") as f:
        sql = f.read()
    
    # Exécuter la migration
    try:
        cursor.executescript(sql)
        conn.commit()
        print("✅ Migration 010 appliquée avec succès")
        print("   - Ajout de uf_responsabilite")
        print("   - Ajout de uf_hebergement")
        print("   - Ajout de uf_medicale")
        print("   - Ajout de uf_soins")
        print("   - Ajout de movement_nature")
        print("   - Index créés pour optimiser les recherches")
    except sqlite3.Error as e:
        print(f"❌ Erreur lors de la migration : {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    apply_migration_010()
