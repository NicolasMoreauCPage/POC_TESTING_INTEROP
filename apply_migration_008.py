#!/usr/bin/env python3
"""Apply migration 008 - add entite_juridique_id to identifiernamespace"""

import sqlite3
import sys

def main():
    db_path = "poc.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(identifiernamespace)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "entite_juridique_id" in columns:
            print("✓ Column entite_juridique_id already exists")
            return 0
        
        print("Applying migration 008...")
        
        # Add column
        cursor.execute("""
            ALTER TABLE identifiernamespace 
            ADD COLUMN entite_juridique_id INTEGER REFERENCES entitejuridique(id)
        """)
        print("✓ Added column entite_juridique_id")
        
        # Add index
        cursor.execute("""
            CREATE INDEX idx_namespace_ej 
            ON identifiernamespace(entite_juridique_id)
        """)
        print("✓ Created index idx_namespace_ej")
        
        conn.commit()
        conn.close()
        
        print("\n✓ Migration 008 applied successfully")
        return 0
        
    except sqlite3.Error as e:
        print(f"✗ Error applying migration: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
