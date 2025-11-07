#!/usr/bin/env python3
"""Apply migration 009 - add PAM validation fields to SystemEndpoint and MessageLog"""

import sqlite3
import sys

def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def main():
    db_path = "poc.db"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # SystemEndpoint fields
        changed = False
        if not column_exists(cursor, "systemendpoint", "pam_validate_enabled"):
            cursor.execute("ALTER TABLE systemendpoint ADD COLUMN pam_validate_enabled INTEGER DEFAULT 0")
            changed = True
        if not column_exists(cursor, "systemendpoint", "pam_validate_mode"):
            cursor.execute("ALTER TABLE systemendpoint ADD COLUMN pam_validate_mode TEXT DEFAULT 'warn'")
            changed = True
        if not column_exists(cursor, "systemendpoint", "pam_profile"):
            cursor.execute("ALTER TABLE systemendpoint ADD COLUMN pam_profile TEXT DEFAULT 'IHE_PAM_FR'")
            changed = True

        # MessageLog fields
        if not column_exists(cursor, "messagelog", "pam_validation_status"):
            cursor.execute("ALTER TABLE messagelog ADD COLUMN pam_validation_status TEXT")
            changed = True
        if not column_exists(cursor, "messagelog", "pam_validation_issues"):
            cursor.execute("ALTER TABLE messagelog ADD COLUMN pam_validation_issues TEXT")
            changed = True

        conn.commit()
        conn.close()
        if changed:
            print("\n✓ Migration 009 applied successfully")
        else:
            print("\n✓ Migration 009 already applied")
        return 0
    except sqlite3.Error as e:
        print(f"✗ Error applying migration 009: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
