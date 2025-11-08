import sqlite3
conn = sqlite3.connect('poc.db')
tables = conn.execute('SELECT name FROM sqlite_master WHERE type="table" ORDER BY name').fetchall()
print(f"Total tables: {len(tables)}")
for t in tables:  # Show all
    if 'entite' in t[0].lower() or 'ght' in t[0].lower():
        print(t[0])
conn.close()
