#!/usr/bin/env python3
"""Apply migrations 006, 007, 008, 009, and 010"""

import sqlite3
import sys

def main():
    db_path = "poc.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check migration 006
        cursor.execute("PRAGMA table_info(systemendpoint)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "entite_juridique_id" not in columns:
            print("Applying migration 006...")
            cursor.execute("""
                ALTER TABLE systemendpoint 
                ADD COLUMN entite_juridique_id INTEGER REFERENCES entitejuridique(id)
            """)
            cursor.execute("""
                CREATE INDEX idx_systemendpoint_entite_juridique_id 
                ON systemendpoint(entite_juridique_id)
            """)
            print("✓ Migration 006 applied")
        else:
            print("✓ Migration 006 already applied")
        
        # Check migration 007
        if "inbox_path" not in columns:
            print("Applying migration 007...")
            cursor.execute("ALTER TABLE systemendpoint ADD COLUMN inbox_path TEXT")
            cursor.execute("ALTER TABLE systemendpoint ADD COLUMN outbox_path TEXT")
            cursor.execute("ALTER TABLE systemendpoint ADD COLUMN archive_path TEXT")
            cursor.execute("ALTER TABLE systemendpoint ADD COLUMN error_path TEXT")
            cursor.execute("ALTER TABLE systemendpoint ADD COLUMN file_extensions TEXT")
            print("✓ Migration 007 applied")
        else:
            print("✓ Migration 007 already applied")
        
        # Check migration 010 (mouvement UF fields)
        cursor.execute("PRAGMA table_info(mouvement)")
        mvt_columns = [row[1] for row in cursor.fetchall()]
        
        if "uf_responsabilite" not in mvt_columns:
            print("Applying migration 010...")
            cursor.execute("ALTER TABLE mouvement ADD COLUMN uf_responsabilite TEXT")
            cursor.execute("ALTER TABLE mouvement ADD COLUMN uf_hebergement TEXT")
            cursor.execute("ALTER TABLE mouvement ADD COLUMN uf_medicale TEXT")
            cursor.execute("ALTER TABLE mouvement ADD COLUMN uf_soins TEXT")
            cursor.execute("ALTER TABLE mouvement ADD COLUMN movement_nature TEXT")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mouvement_uf_responsabilite ON mouvement(uf_responsabilite)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mouvement_nature ON mouvement(movement_nature)")
            print("✓ Migration 010 applied")
        else:
            print("✓ Migration 010 already applied")
        
        conn.commit()
        conn.close()
        
        print("\n✓ All migrations applied successfully")
        return 0
        
    except sqlite3.Error as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
