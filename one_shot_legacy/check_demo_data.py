#!/usr/bin/env python3
"""Vérifier l'état de la base de données de démo"""

from sqlmodel import Session, select
from app.db import engine
from app.models_structure_fhir import GHTContext, EntiteJuridique, EntiteGeographique, IdentifierNamespace
from app.models_structure import Pole, Service

s = Session(engine)

# GHT
ghts = s.exec(select(GHTContext)).all()
print(f"GHT: {len(ghts)}")
for g in ghts:
    print(f"  - {g.name} (ID={g.id}, code={g.code})")

# EJ
ejs = s.exec(select(EntiteJuridique)).all()
print(f"\nEntités Juridiques: {len(ejs)}")
for ej in ejs:
    print(f"  - {ej.name} (FINESS={ej.finess_ej})")

# EG
egs = s.exec(select(EntiteGeographique)).all()
print(f"\nEntités Géographiques: {len(egs)}")
for eg in egs:
    print(f"  - {eg.name} (FINESS={eg.finess})")

# Pôles
poles = s.exec(select(Pole)).all()
print(f"\nPôles: {len(poles)}")

# Services
services = s.exec(select(Service)).all()
print(f"Services: {len(services)}")

# Namespaces
nss = s.exec(select(IdentifierNamespace)).all()
print(f"\nNamespaces d'identifiants: {len(nss)}")
for ns in nss:
    print(f"  - {ns.name} (type={ns.type}, system={ns.system})")
