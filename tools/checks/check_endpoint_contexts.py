"""Vérifier les endpoints et leurs contextes"""
from sqlmodel import Session, select
from app.db import engine
from app.models_shared import SystemEndpoint

with Session(engine) as s:
    eps = list(s.exec(select(SystemEndpoint)).all())
    
    print(f"=== {len(eps)} Endpoints ===\n")
    for ep in eps:
        print(f"{ep.name}:")
        print(f"  ID: {ep.id}")
        print(f"  Kind: {ep.kind}")
        print(f"  GHT Context ID: {ep.ght_context_id}")
        print(f"  EJ ID: {ep.entite_juridique_id}")
        print()
