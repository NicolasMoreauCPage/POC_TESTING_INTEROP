"""Test pour voir ce que l'API retourne vraiment."""
import sys
sys.path.insert(0, str("c:/Travail/Fhir_Tester/MedData_Bridge"))

from sqlmodel import Session, create_engine, select
from sqlalchemy.orm import selectinload
from app.models_structure_fhir import EntiteGeographique, Pole
from app.models_structure import Service, UniteFonctionnelle, UniteHebergement, Chambre, Lit

DATABASE_URL = "sqlite:///./poc.db"
engine = create_engine(DATABASE_URL)

with Session(engine) as session:
    # Charger un service spécifique pour tester
    query = (select(Service)
        .options(
            selectinload(Service.unites_fonctionnelles)
            .selectinload(UniteFonctionnelle.unites_hebergement)
            .selectinload(UniteHebergement.chambres)
            .selectinload(Chambre.lits)
        )
        .limit(5))
    
    services = session.exec(query).all()
    
    print(f"Nombre de services trouvés: {len(services)}\n")
    
    for service in services:
        print(f"Service #{service.id}: {service.name}")
        print(f"  service.unites_fonctionnelles: {service.unites_fonctionnelles}")
        print(f"  Nombre d'UF: {len(service.unites_fonctionnelles) if service.unites_fonctionnelles else 0}")
        
        if service.unites_fonctionnelles:
            for uf in service.unites_fonctionnelles[:2]:  # Montrer 2 premières UF
                print(f"    UF #{uf.id}: {uf.name}")
                print(f"      Nombre d'UH: {len(uf.unites_hebergement) if uf.unites_hebergement else 0}")
                
                if uf.unites_hebergement:
                    for uh in uf.unites_hebergement[:1]:
                        print(f"        UH #{uh.id}: {uh.name}")
                        print(f"          Nombre de chambres: {len(uh.chambres) if uh.chambres else 0}")
        print()
