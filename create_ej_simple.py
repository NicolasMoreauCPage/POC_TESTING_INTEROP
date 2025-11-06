"""Script simple pour creer une EJ et verifier l'emission."""
from datetime import datetime
from sqlmodel import Session
from app.db import engine
from app.models_structure_fhir import GHTContext, EntiteJuridique
from sqlmodel import select

with Session(engine) as session:
    ght = session.exec(select(GHTContext).limit(1)).first()
    if not ght:
        print("Pas de GHT")
        exit(1)
    
    print(f"GHT: {ght.name}")
    
    ej = EntiteJuridique(
        ght_context_id=ght.id,
        name="Test Direct Emission",
        short_name="TDE",
        finess_ej="990666555",
        siren="888777666",
        siret="88877766600013",
        start_date=datetime(2024, 1, 1),
    )
    session.add(ej)
    session.commit()
    print(f"EJ creee: {ej.name} (id={ej.id})")
