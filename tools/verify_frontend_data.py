"""Verify EJ #6 EG filtering and what frontend would see - using raw SQL."""
import sqlite3

conn = sqlite3.connect("poc.db")
cursor = conn.cursor()

# Get EJ #6
cursor.execute("SELECT id, name, finess_ej, ght_context_id FROM entitejuridique WHERE id = 6")
ej = cursor.fetchone()
print(f"EJ #{ej[0]}: {ej[1]} (FINESS: {ej[2]})")
print(f"GHT ID: {ej[3]}")

# Get its GHT
cursor.execute("SELECT id, name FROM ghtcontext WHERE id = ?", (ej[3],))
ght = cursor.fetchone()
print(f"GHT: {ght[1]}")
print()

# Get EG filtered like backend does
cursor.execute("""
    SELECT id, name, finess, entite_juridique_id 
    FROM entitegeographique 
    WHERE entite_juridique_id = 6
    ORDER BY id
""")
egs = cursor.fetchall()

print(f"📊 Backend would pass filtered_egs = {[eg[0] for eg in egs]}")
print(f"   ({len(egs)} EG)")
print()

# What API would return for these IDs
print("What API /api/structure/tree?eg_ids=... would return:")
for eg in egs:
    print(f"  EG #{eg[0]}: {eg[1]}")
    print(f"    FINESS: {eg[2]}")
    print(f"    EJ ID: {eg[3]}")
    
    # Verify EJ's GHT
    cursor.execute("SELECT ght_context_id FROM entitejuridique WHERE id = ?", (eg[3],))
    eg_ej_ght_id = cursor.fetchone()[0]
    
    cursor.execute("SELECT id, name FROM ghtcontext WHERE id = ?", (eg_ej_ght_id,))
    eg_ght = cursor.fetchone()
    
    if eg_ght[0] == ght[0]:
        print(f"    ✅ GHT: {eg_ght[1]} (CORRECT)")
    else:
        print(f"    ❌ GHT: {eg_ght[1]} (WRONG! Expected {ght[1]})")
    print()

conn.close()
