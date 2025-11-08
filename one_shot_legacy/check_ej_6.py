"""Check EntiteJuridique #6 and its structures."""
from app.db import get_session
from app.models_structure_fhir import EntiteJuridique, EntiteGeographique
from sqlmodel import select

s = next(get_session())

# Get EJ #6
ej = s.get(EntiteJuridique, 6)
print(f"EJ #6: {ej.name} (FINESS: {ej.finess_ej})")
print(f"GHT: {ej.ght_context.name if ej.ght_context else None} (id={ej.ght_context_id})")

# Get linked EntiteGeographique
print(f"\nEntités Géographiques liées à cette EJ:")
egs = s.exec(select(EntiteGeographique).where(EntiteGeographique.entite_juridique_id == 6)).all()
print(f"Total: {len(egs)}")
for eg in egs:
    print(f"  - {eg.name} (FINESS: {eg.finess}) - EJ_ID={eg.entite_juridique_id}")
