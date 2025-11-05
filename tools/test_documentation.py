#!/usr/bin/env python3
"""Test de l'interface de documentation."""
import sys
from pathlib import Path

# Ajouter le dossier racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from app.routers.documentation import get_doc_structure, DOC_ROOT

def test_doc_structure():
    """Vérifie que tous les fichiers de la structure existent."""
    print("=" * 80)
    print("TEST DE LA STRUCTURE DE DOCUMENTATION")
    print("=" * 80)
    
    structure = get_doc_structure()
    total_files = 0
    missing_files = []
    
    for category_id, category_info in structure.items():
        print(f"\n📂 {category_info['icon']} {category_info['title']} ({category_id})")
        
        for filename in category_info['files']:
            total_files += 1
            filepath = DOC_ROOT / category_id / filename
            
            if filepath.exists():
                size = filepath.stat().st_size
                print(f"   ✓ {filename} ({size:,} bytes)")
            else:
                missing_files.append(f"{category_id}/{filename}")
                print(f"   ✗ {filename} (MANQUANT)")
    
    # Vérifier INDEX.md
    print(f"\n📚 Fichier principal")
    index_path = DOC_ROOT / "INDEX.md"
    if index_path.exists():
        size = index_path.stat().st_size
        print(f"   ✓ INDEX.md ({size:,} bytes)")
    else:
        missing_files.append("INDEX.md")
        print(f"   ✗ INDEX.md (MANQUANT)")
    
    # Résumé
    print("\n" + "=" * 80)
    print("RÉSUMÉ")
    print("=" * 80)
    print(f"Fichiers déclarés : {total_files}")
    print(f"Fichiers trouvés : {total_files - len(missing_files)}")
    print(f"Fichiers manquants : {len(missing_files)}")
    
    if missing_files:
        print("\n⚠️  FICHIERS MANQUANTS :")
        for f in missing_files:
            print(f"   - {f}")
        return False
    else:
        print("\n✅ TOUS LES FICHIERS SONT PRÉSENTS")
        return True

if __name__ == "__main__":
    success = test_doc_structure()
    sys.exit(0 if success else 1)
