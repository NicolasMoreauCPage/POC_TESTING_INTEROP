"""
Test MFN import avec structure complète hierarchique:
EJ → EG → Service → UF → Chambre → Lit
"""
import asyncio
from sqlmodel import Session, select
from app.db import engine
from app.services.mfn_importer import import_mfn
from app.models_structure_fhir import GHTContext, EntiteJuridique, EntiteGeographique
from app.models_structure import Pole, Service, UniteFonctionnelle, Chambre, Lit

# MFN complet avec tous les niveaux de structure (format CPAGE compatible)
MFN_FULL = """MSH|^~\\&|STR|STR|RECEPTEUR|RECEPTEUR|20250206141011||MFN^M05^MFN_M05|20250206141011|P|2.5|||||FRA|8859/15
MFI|LOC|CPAGE_LOC_FRA|REP||20250206141011|AL
MFE|MAD|||^^^^^M^^^^69&CPAGE&700004591&FINEJ|PL
LOC|^^^^^M^^^^69&CPAGE&700004591&FINEJ||M|Etablissement juridique
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||ID_GLBL^Identifiant unique global^L|^69
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||CD^Code^L|^69
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||LBL^Libelle^L|^GRGAP
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||FNS^Code FINESS^L|^700004591
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||ADRS_1^Adresse 1^L|^1 Avenue de la Paix
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||CD_PSTL^Code postal^L|^69000
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||VL^Ville^L|^Lyon
MFE|MAD|||^^^^^ETBL_GRPQ^^^^888888888&CPAGE&700004591&FINEJ|PL
LOC|^^^^^ETBL_GRPQ^^^^888888888&CPAGE&700004591&FINEJ||ETBL_GRPQ|Hôpital Lyon Sud
LCH|^^^^^ETBL_GRPQ^^^^888888888&CPAGE&700004591&FINEJ|||ID_GLBL^Identifiant unique global^L|^888888888
LCH|^^^^^ETBL_GRPQ^^^^888888888&CPAGE&700004591&FINEJ|||CD^Code^L|^888888888
LCH|^^^^^ETBL_GRPQ^^^^888888888&CPAGE&700004591&FINEJ|||LBL^Libelle^L|^Hôpital Lyon Sud
LCH|^^^^^ETBL_GRPQ^^^^888888888&CPAGE&700004591&FINEJ|||FNS^Code FINESS^L|^888888888
LRL|^^^^^ETBL_GRPQ^^^^888888888&CPAGE&700004591&FINEJ|||ETBLSMNT^Relation établissement^L||^^^^^M^^^^69&CPAGE&700004591&FINEJ
MFE|MAD|||^^^^^D^^^^URG_SERVICE&CPAGE&888888888&FINEG|PL
LOC|^^^^^D^^^^URG_SERVICE&CPAGE&888888888&FINEG||D|Service d'urgences
LCH|^^^^^D^^^^URG_SERVICE&CPAGE&888888888&FINEG|||ID_GLBL^Identifiant unique global^L|^URG_SERVICE
LCH|^^^^^D^^^^URG_SERVICE&CPAGE&888888888&FINEG|||CD^Code^L|^URG_SERVICE
LCH|^^^^^D^^^^URG_SERVICE&CPAGE&888888888&FINEG|||LBL^Libelle^L|^Service d'urgences
LRL|^^^^^D^^^^URG_SERVICE&CPAGE&888888888&FINEG|||LCLSTN^Localisation^L||^^^^^ETBL_GRPQ^^^^888888888&CPAGE&700004591&FINEJ
MFE|MAD|||^^^^^N^^^^UF_URG_01&CPAGE&URG_SERVICE&SERV|PL
LOC|^^^^^N^^^^UF_URG_01&CPAGE&URG_SERVICE&SERV||N|UF Accueil Urgences
LCH|^^^^^N^^^^UF_URG_01&CPAGE&URG_SERVICE&SERV|||ID_GLBL^Identifiant unique global^L|^UF_URG_01
LCH|^^^^^N^^^^UF_URG_01&CPAGE&URG_SERVICE&SERV|||CD^Code^L|^UF_URG_01
LCH|^^^^^N^^^^UF_URG_01&CPAGE&URG_SERVICE&SERV|||LBL^Libelle^L|^UF Accueil Urgences
LRL|^^^^^N^^^^UF_URG_01&CPAGE&URG_SERVICE&SERV|||LCLSTN^Localisation^L||^^^^^D^^^^URG_SERVICE&CPAGE&888888888&FINEG
MFE|MAD|||^^^^^R^^^^URG_CHAMBRE_01&CPAGE&UF_URG_01&UF|PL
LOC|^^^^^R^^^^URG_CHAMBRE_01&CPAGE&UF_URG_01&UF||R|Chambre Urgences 01
LCH|^^^^^R^^^^URG_CHAMBRE_01&CPAGE&UF_URG_01&UF|||ID_GLBL^Identifiant unique global^L|^URG_CHAMBRE_01
LCH|^^^^^R^^^^URG_CHAMBRE_01&CPAGE&UF_URG_01&UF|||CD^Code^L|^URG_CHAMBRE_01
LCH|^^^^^R^^^^URG_CHAMBRE_01&CPAGE&UF_URG_01&UF|||LBL^Libelle^L|^Chambre Urgences 01
LRL|^^^^^R^^^^URG_CHAMBRE_01&CPAGE&UF_URG_01&UF|||LCLSTN^Localisation^L||^^^^^N^^^^UF_URG_01&CPAGE&URG_SERVICE&SERV
MFE|MAD|||^^^^^B^^^^URG_LIT_01A&CPAGE&URG_CHAMBRE_01&ROOM|PL
LOC|^^^^^B^^^^URG_LIT_01A&CPAGE&URG_CHAMBRE_01&ROOM||B|Lit A - Chambre 01
LCH|^^^^^B^^^^URG_LIT_01A&CPAGE&URG_CHAMBRE_01&ROOM|||ID_GLBL^Identifiant unique global^L|^URG_LIT_01A
LCH|^^^^^B^^^^URG_LIT_01A&CPAGE&URG_CHAMBRE_01&ROOM|||CD^Code^L|^URG_LIT_01A
LCH|^^^^^B^^^^URG_LIT_01A&CPAGE&URG_CHAMBRE_01&ROOM|||LBL^Libelle^L|^Lit A - Chambre 01
LRL|^^^^^B^^^^URG_LIT_01A&CPAGE&URG_CHAMBRE_01&ROOM|||LCLSTN^Localisation^L||^^^^^R^^^^URG_CHAMBRE_01&CPAGE&UF_URG_01&UF
"""

async def test_full_hierarchy():
    """Test import MFN avec structure complète"""
    
    with Session(engine) as session:
        # Récupérer ou créer GHT context
        ght_ctx = session.exec(
            select(GHTContext).where(GHTContext.name == "GHT Démo Interop")
        ).first()
        
        if not ght_ctx:
            ght_ctx = GHTContext(
                name="GHT Démo Interop",
                description="GHT de démo pour tests"
            )
            session.add(ght_ctx)
            session.commit()
            session.refresh(ght_ctx)
        
        print(f"GHT Context: {ght_ctx.name} (id={ght_ctx.id})")
        
        # Import MFN
        print("\n=== Import MFN ===")
        result = import_mfn(MFN_FULL, session, ght_ctx)
        print(f"Import result: {result}")
        session.commit()
        
        # Vérifier les résultats
        print("\n=== Vérification structure ===")
        
        # EJ
        ej = session.exec(
            select(EntiteJuridique).where(EntiteJuridique.finess_ej == "700004591")
        ).first()
        print(f"\nEntiteJuridique:")
        if ej:
            print(f"  ID: {ej.id}")
            print(f"  FINESS: {ej.finess_ej}")
            print(f"  Name: {ej.name}")
        else:
            print("  ❌ NON TROUVÉE")
        
        # EG
        eg = session.exec(
            select(EntiteGeographique).where(EntiteGeographique.finess == "888888888")
        ).first()
        print(f"\nEntiteGeographique:")
        if eg:
            print(f"  ID: {eg.id}")
            print(f"  FINESS: {eg.finess}")
            print(f"  Name: {eg.name}")
            print(f"  EJ liée: {eg.entite_juridique_id}")
        else:
            print("  ❌ NON TROUVÉE")
        
        # Pole (créé automatiquement pour Service)
        pole = session.exec(select(Pole)).first()
        print(f"\nPole:")
        if pole:
            print(f"  ID: {pole.id}")
            print(f"  Name: {pole.name}")
            print(f"  EG liée: {pole.entite_geo_id}")
        else:
            print("  ❌ NON TROUVÉ")
        
        # Service
        service = session.exec(
            select(Service).where(Service.identifier == "URG_SERVICE")
        ).first()
        print(f"\nService:")
        if service:
            print(f"  ID: {service.id}")
            print(f"  Identifier: {service.identifier}")
            print(f"  Nom: {service.name}")
            print(f"  Pole lié: {service.pole_id}")
        else:
            print("  ❌ NON TROUVÉ")
        
        # UF
        uf = session.exec(
            select(UniteFonctionnelle).where(UniteFonctionnelle.identifier == "UF_URG_01")
        ).first()
        print(f"\nUF:")
        if uf:
            print(f"  ID: {uf.id}")
            print(f"  Identifier: {uf.identifier}")
            print(f"  Nom: {uf.name}")
            print(f"  Service lié: {uf.service_id}")
        else:
            print("  ❌ NON TROUVÉE")
        
        # Chambre
        chambre = session.exec(
            select(Chambre).where(Chambre.identifier == "URG_CHAMBRE_01")
        ).first()
        print(f"\nChambre:")
        if chambre:
            print(f"  ID: {chambre.id}")
            print(f"  Identifier: {chambre.identifier}")
            print(f"  Nom: {chambre.name}")
            print(f"  UH liée: {chambre.unite_hebergement_id}")
        else:
            print("  ❌ NON TROUVÉE")
        
        # Lit
        lit = session.exec(
            select(Lit).where(Lit.identifier == "URG_LIT_01A")
        ).first()
        print(f"\nLit:")
        if lit:
            print(f"  ID: {lit.id}")
            print(f"  Identifier: {lit.identifier}")
            print(f"  Nom: {lit.name}")
            print(f"  Chambre liée: {lit.chambre_id}")
        else:
            print("  ❌ NON TROUVÉ")
        
        print("\n=== Résumé ===")
        counts = {
            'ej': session.exec(select(EntiteJuridique)).all().__len__(),
            'eg': session.exec(select(EntiteGeographique)).all().__len__(),
            'pole': session.exec(select(Pole)).all().__len__(),
            'service': session.exec(select(Service)).all().__len__(),
            'uf': session.exec(select(UniteFonctionnelle)).all().__len__(),
            'chambre': session.exec(select(Chambre)).all().__len__(),
            'lit': session.exec(select(Lit)).all().__len__(),
        }
        print(f"Total: {counts}")

if __name__ == "__main__":
    asyncio.run(test_full_hierarchy())
