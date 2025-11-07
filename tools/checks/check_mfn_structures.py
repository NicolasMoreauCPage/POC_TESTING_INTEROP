"""
Script pour vérifier si le message MFN a créé des structures
"""
from app.db import get_session
from app.models_shared import MessageLog
from app.models_transport import SystemEndpoint
from app.models_structure_fhir import GHTContext, EntiteJuridique, EntiteGeographique
from sqlmodel import select

def main():
    session = next(get_session())
    
    # 1. Vérifier le message
    print("=== MESSAGE ===")
    msg = session.exec(
        select(MessageLog)
        .where(MessageLog.correlation_id.like('%20250206141011%'))
        .order_by(MessageLog.id.desc())
    ).first()
    
    if msg:
        print(f"Message ID: {msg.id}")
        print(f"Type: {msg.message_type}")
        print(f"Status: {msg.status}")
        print(f"Endpoint ID: {msg.endpoint_id}")
        print(f"Correlation ID: {msg.correlation_id}")
        print(f"Created at: {msg.created_at}")
        
        # Afficher un extrait du payload
        lines = msg.payload.split('\n')[:5]
        print(f"\nPayload (first 5 lines):")
        for line in lines:
            print(f"  {line}")
    else:
        print("Message not found!")
        return
    
    # 2. Vérifier l'endpoint et son GHT
    print("\n=== ENDPOINT ===")
    ep = session.get(SystemEndpoint, msg.endpoint_id)
    if ep:
        print(f"Endpoint: {ep.name}")
        print(f"Type: {ep.kind}")
        print(f"GHT Context ID: {ep.ght_context_id}")
        
        if ep.ght_context_id:
            ght = session.get(GHTContext, ep.ght_context_id)
            print(f"GHT: {ght.name if ght else 'NOT FOUND'}")
        
        if ep.entite_juridique_id:
            ej = session.get(EntiteJuridique, ep.entite_juridique_id)
            print(f"EJ: {ej.name if ej else 'NOT FOUND'} ({ej.finess_ej if ej else '?'})")
    
    # 3. Chercher les structures créées pour ce GHT
    print("\n=== STRUCTURES DANS GHT TEST Nico (id=2) ===")
    
    # Entités Juridiques
    ejs = session.exec(
        select(EntiteJuridique).where(EntiteJuridique.ght_context_id == 2)
    ).all()
    print(f"\nEntités Juridiques: {len(ejs)}")
    ej_ids = []
    for ej in ejs:
        print(f"  - ID={ej.id} {ej.name} ({ej.finess_ej})")
        ej_ids.append(ej.id)
    
    # Entités Géographiques (via les EJ du GHT)
    if ej_ids:
        egs = session.exec(
            select(EntiteGeographique).where(EntiteGeographique.entite_juridique_id.in_(ej_ids))
        ).all()
        print(f"\nEntités Géographiques (pour les EJ du GHT): {len(egs)}")
        for eg in egs:
            print(f"  - {eg.name} (FINESS: {eg.finess}) - EJ_ID={eg.entite_juridique_id}")
    else:
        print("\nAucune EJ trouvée, donc aucune EG à chercher")
    
    # 4. Chercher toutes les structures (sans filtre GHT) pour voir si elles ont été créées ailleurs
    print("\n=== TOUTES LES ENTITÉS GÉOGRAPHIQUES (tous GHT) ===")
    all_egs = session.exec(select(EntiteGeographique)).all()
    print(f"\nTotal EntitésGéographiques dans la base: {len(all_egs)}")
    for eg in all_egs[:10]:  # Afficher les 10 premières
        ej = session.get(EntiteJuridique, eg.entite_juridique_id) if eg.entite_juridique_id else None
        ght = ej.ght_context if ej else None
        print(f"  - {eg.name} (FINESS: {eg.finess}) - EJ: {ej.name if ej else 'None'}, GHT: {ght.name if ght else 'None'}")
    
    session.close()

if __name__ == "__main__":
    main()
