#!/usr/bin/env python3
"""
Vérifie que les mouvements de démo contiennent bien les nouveaux champs UF.
"""
from sqlmodel import Session, select
from app.db import engine
from app.models import Mouvement

def main():
    print("🔍 Vérification des mouvements de démo\n")
    
    with Session(engine) as session:
        # Récupérer tous les mouvements
        mouvements = session.exec(select(Mouvement)).all()
        
        if not mouvements:
            print("❌ Aucun mouvement trouvé dans la base")
            print("   Exécutez d'abord: python3 tools/init_all.py")
            return
        
        print(f"📊 {len(mouvements)} mouvements trouvés\n")
        
        # Compter les mouvements avec/sans nouveaux champs
        with_uf = 0
        without_uf = 0
        
        for mvt in mouvements:
            if mvt.uf_responsabilite or mvt.movement_nature:
                with_uf += 1
            else:
                without_uf += 1
        
        print(f"✅ Mouvements avec UF: {with_uf}/{len(mouvements)}")
        print(f"⚠️  Mouvements sans UF: {without_uf}/{len(mouvements)}")
        
        if with_uf > 0:
            print("\n📋 Exemple de mouvement avec UF:")
            mvt = next((m for m in mouvements if m.uf_responsabilite), None)
            if mvt:
                print(f"   Type: {mvt.type}")
                print(f"   UF Resp: {mvt.uf_responsabilite}")
                print(f"   UF Méd: {mvt.uf_medicale}")
                print(f"   UF Héb: {mvt.uf_hebergement}")
                print(f"   UF Soins: {mvt.uf_soins}")
                print(f"   Nature: {mvt.movement_nature}")
        
        if without_uf > 0:
            print("\n⚠️  Certains mouvements n'ont pas les nouveaux champs.")
            print("   Cela peut être normal pour les mouvements créés avant la migration 010.")
            print("   Pour mettre à jour, re-initialisez la base avec: python3 tools/init_all.py")

if __name__ == "__main__":
    main()
