#!/usr/bin/env python3
"""Apply migration 006 - add entite_juridique_id to systemendpoint"""

import sqlite3
import sys

def main():
    db_path = "poc.db"  # Changed to poc.db
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # List tables first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables in database: {[t[0] for t in tables]}")
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(systemendpoint)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "entite_juridique_id" in columns:
            print("✓ Column entite_juridique_id already exists")
            return 0
        
        print("Applying migration 006...")
        
        # Add column
        cursor.execute("""
            ALTER TABLE systemendpoint 
            ADD COLUMN entite_juridique_id INTEGER REFERENCES entitejuridique(id)
        """)
        print("✓ Added column entite_juridique_id")
        
        # Add index
        cursor.execute("""
            CREATE INDEX idx_systemendpoint_entite_juridique_id 
            ON systemendpoint(entite_juridique_id)
        """)
        print("✓ Created index idx_systemendpoint_entite_juridique_id")
        
        conn.commit()
        conn.close()
        
        print("\n✓ Migration 006 applied successfully")
        return 0
        
    except sqlite3.Error as e:
        print(f"✗ Error applying migration: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
