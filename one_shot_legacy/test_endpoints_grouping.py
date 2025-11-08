"""Test pour reproduire l'erreur de la page endpoints"""
import sys
sys.path.insert(0, '.')

from sqlmodel import Session, select
from app.db import engine
from app.models_shared import SystemEndpoint
from app.models_structure_fhir import GHTContext, EntiteJuridique

with Session(engine) as session:
    print("=== Test de la logique de groupement ===\n")
    
    # Simuler le code de list_endpoints
    from sqlmodel.sql.expression import select as sqlmodel_select
    from sqlalchemy.orm import selectinload
    
    stmt = (
        sqlmodel_select(SystemEndpoint)
        .options(
            selectinload(SystemEndpoint.ght_context).selectinload(GHTContext.entites_juridiques),
            selectinload(SystemEndpoint.entite_juridique).selectinload(EntiteJuridique.ght_context)
        )
    )
    
    try:
        eps = session.exec(stmt).unique().all()
        print(f"✓ Endpoints chargés: {len(eps)}")
        
        for e in eps:
            print(f"\nEndpoint: {e.name}")
            print(f"  ID: {e.id}")
            print(f"  ght_context: {e.ght_context}")
            print(f"  entite_juridique: {e.entite_juridique}")
            
            if e.entite_juridique:
                print(f"  EJ.ght_context: {e.entite_juridique.ght_context if hasattr(e.entite_juridique, 'ght_context') else 'NOT LOADED'}")
                print(f"  EJ.ght_context_id: {e.entite_juridique.ght_context_id}")
            
            # Tester la logique de récupération du GHT
            ght = e.ght_context
            if not ght and e.entite_juridique:
                if hasattr(e.entite_juridique, 'ght_context') and e.entite_juridique.ght_context:
                    ght = e.entite_juridique.ght_context
                    print(f"  → GHT trouvé via EJ: {ght.name}")
                elif e.entite_juridique.ght_context_id:
                    ght = session.get(GHTContext, e.entite_juridique.ght_context_id)
                    print(f"  → GHT chargé manuellement: {ght.name if ght else 'NONE'}")
            
            if ght:
                print(f"  ✓ GHT final: {ght.name} (ID={ght.id})")
            else:
                print(f"  ✗ Pas de GHT trouvé")
                
    except Exception as e:
        print(f"\n✗ ERREUR: {e}")
        import traceback
        traceback.print_exc()
