"""Test simple pour voir les liens Service -> UF."""
import sqlite3

conn = sqlite3.connect("poc.db")
cursor = conn.cursor()

# Compter les UF par service
cursor.execute("""
    SELECT s.id, s.name, COUNT(uf.id) as nb_uf
    FROM service s
    LEFT JOIN unitefonctionnelle uf ON uf.service_id = s.id
    GROUP BY s.id
    ORDER BY nb_uf DESC
    LIMIT 10
""")

print("Services avec leurs UF:")
print("=" * 60)
for row in cursor.fetchall():
    print(f"Service #{row[0]}: {row[1]} -> {row[2]} UF")

print("\n\nDétail des UF d'un service:")
print("=" * 60)

cursor.execute("""
    SELECT s.id, s.name
    FROM service s
    LEFT JOIN unitefonctionnelle uf ON uf.service_id = s.id
    GROUP BY s.id
    HAVING COUNT(uf.id) > 0
    LIMIT 1
""")
service = cursor.fetchone()

if service:
    print(f"\nService #{service[0]}: {service[1]}")
    
    cursor.execute("""
        SELECT id, name, service_id
        FROM unitefonctionnelle
        WHERE service_id = ?
    """, (service[0],))
    
    ufs = cursor.fetchall()
    print(f"  Nombre d'UF: {len(ufs)}")
    for uf in ufs[:5]:
        print(f"    UF #{uf[0]}: {uf[1]} (service_id={uf[2]})")

conn.close()
