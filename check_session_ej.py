"""
Script pour vérifier l'état de la session et identifier l'erreur avec ej_context_id
"""
from sqlmodel import Session, create_engine, select
from sqlalchemy.orm import selectinload
from app.models_structure_fhir import GHTContext, EntiteJuridique
from app.models_transport import SystemEndpoint

# Connexion à la base de données
engine = create_engine("sqlite:///poc.db")

with Session(engine) as session:
    print("\n=== GHT Contexts ===")
    ghts = session.exec(select(GHTContext)).all()
    for ght in ghts:
        print(f"  ID={ght.id}, name='{ght.name}', code='{ght.code}'")
    
    print("\n=== Entités Juridiques ===")
    ejs = session.exec(select(EntiteJuridique)).all()
    for ej in ejs:
        print(f"  ID={ej.id}, name='{ej.name}', FINESS={ej.finess_ej}, ght_context_id={ej.ght_context_id}")
    
    print("\n=== Test de chargement avec ej_context_id=1 ===")
    ej_context_id = 1
    
    # Simuler la requête de list_endpoints
    from sqlmodel import select as sqlmodel_select
    stmt = (
        sqlmodel_select(SystemEndpoint)
        .options(
            selectinload(SystemEndpoint.ght_context).selectinload(GHTContext.entites_juridiques),
            selectinload(SystemEndpoint.entite_juridique).selectinload(EntiteJuridique.ght_context)
        )
        .where(SystemEndpoint.entite_juridique_id == ej_context_id)
    )
    
    eps = session.exec(stmt).all()
    print(f"\n✓ Endpoints trouvés: {len(eps)}")
    
    for e in eps:
        print(f"\nEndpoint: {e.name}")
        print(f"  ID: {e.id}")
        print(f"  entite_juridique_id: {e.entite_juridique_id}")
        print(f"  ght_context_id: {e.ght_context_id}")
    
    # Test du titre
    print("\n=== Test de chargement de l'EJ pour le titre ===")
    try:
        ej = session.get(EntiteJuridique, ej_context_id)
        if ej:
            print(f"✓ EJ chargé: {ej.name}")
            print(f"  Type: {type(ej)}")
            print(f"  Attributs disponibles: {dir(ej)}")
        else:
            print("✗ EJ non trouvé")
    except Exception as e:
        print(f"✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
