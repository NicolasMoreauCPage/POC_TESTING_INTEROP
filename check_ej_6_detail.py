"""Vérifier quelles EG sont retournées pour l'EJ #6."""
from app.db import get_session
from app.models_structure_fhir import EntiteJuridique, EntiteGeographique
from sqlmodel import select

s = next(get_session())

# EJ #6
ej = s.get(EntiteJuridique, 6)
print(f"EJ #6: {ej.name} (FINESS: {ej.finess_ej})")
print(f"GHT: {ej.ght_context.name} (id={ej.ght_context_id})\n")

# EG liées à cette EJ
egs = s.exec(select(EntiteGeographique).where(EntiteGeographique.entite_juridique_id == 6)).all()
print(f"Total EG liées à l'EJ #6: {len(egs)}\n")

for eg in egs:
    # Vérifier le GHT via l'EJ
    ej_of_eg = eg.entite_juridique
    ght_name = ej_of_eg.ght_context.name if ej_of_eg and ej_of_eg.ght_context else "SANS GHT"
    ght_id = ej_of_eg.ght_context_id if ej_of_eg else None
    
    marker = "✅" if ght_id == 2 else "❌"
    print(f"{marker} EG #{eg.id}: {eg.name}")
    print(f"   FINESS: {eg.finess}, EJ_ID: {eg.entite_juridique_id}")
    print(f"   GHT: {ght_name} (id={ght_id})\n")
