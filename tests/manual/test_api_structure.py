"""Test API structure tree."""
import requests

# Test avec les IDs d'EG de l'EJ #6
eg_ids = "4,6,7,8,9,10,11,12,13"
r = requests.get(f'http://127.0.0.1:8000/api/structure/tree?eg_ids={eg_ids}')
data = r.json()

print(f"Total EG retournées: {len(data)}\n")

for eg in data:
    print(f"EG #{eg['id']}: {eg['name']}")
    print(f"  FINESS: {eg.get('finess', 'N/A')}")
    
    # Compter les sous-structures
    poles = eg.get('children', [])
    total_services = sum(len(p.get('children', [])) for p in poles)
    total_ufs = sum(len(s.get('children', [])) for s in [srv for p in poles for srv in p.get('children', [])])
    
    print(f"  Pôles: {len(poles)}, Services: {total_services}, UFs: {total_ufs}")
    print()
