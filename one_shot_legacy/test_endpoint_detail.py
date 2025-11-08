"""
Test de la route detail_endpoint pour identifier l'erreur
"""
from sqlmodel import Session, create_engine, select
from app.models_transport import SystemEndpoint
from app.models_structure_fhir import GHTContext, EntiteJuridique
from app.routers.endpoints import registry

engine = create_engine("sqlite:///poc.db")

with Session(engine) as session:
    print("\n=== Test endpoint detail ===")
    
    endpoint_id = 1
    e = session.get(SystemEndpoint, endpoint_id)
    
    if not e:
        print(f"✗ Endpoint {endpoint_id} not found")
    else:
        print(f"✓ Endpoint found: {e.name}")
        print(f"  ID: {e.id}")
        print(f"  kind: {e.kind}")
        print(f"  role: {e.role}")
        print(f"  is_enabled: {e.is_enabled}")
        print(f"  ght_context_id: {e.ght_context_id}")
        print(f"  entite_juridique_id: {e.entite_juridique_id}")
    
    print("\n=== Test GHT list ===")
    try:
        ghts = session.exec(select(GHTContext).where(GHTContext.is_active == True)).all()
        print(f"✓ GHT count: {len(ghts)}")
        for ght in ghts:
            print(f"  - {ght.name} (ID={ght.id})")
    except Exception as ex:
        print(f"✗ Error loading GHTs: {ex}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Test EJ list ===")
    try:
        ejs = session.exec(select(EntiteJuridique).where(EntiteJuridique.is_active == True)).all()
        print(f"✓ EJ count: {len(ejs)}")
        for ej in ejs:
            print(f"  - {ej.name} (ID={ej.id}, GHT={ej.ght_context_id})")
    except Exception as ex:
        print(f"✗ Error loading EJs: {ex}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Test registry ===")
    try:
        running_ids = set(registry.running_ids())
        print(f"✓ Running endpoints: {running_ids}")
        is_running = endpoint_id in running_ids
        print(f"  Endpoint {endpoint_id} is {'RUNNING' if is_running else 'STOPPED'}")
    except Exception as ex:
        print(f"✗ Error checking registry: {ex}")
        import traceback
        traceback.print_exc()
