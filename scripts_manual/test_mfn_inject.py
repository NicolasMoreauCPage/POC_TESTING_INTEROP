"""Test direct d'injection de message MFN"""
import asyncio
from app.db import engine
from sqlmodel import Session, select
from app.models_structure_fhir import GHTContext

async def test():
    # Message MFN avec structure complète : EJ → Service → UF → Chambre → Lit
    payload = """MSH|^~\\&|STR|STR|RECEPTEUR|RECEPTEUR|20250206141011||MFN^M05^MFN_M05|20250206141011|P|2.5|||||FRA|8859/15
MFI|LOC|CPAGE_LOC_FRA|REP||20250206141011|AL
MFE|MAD|||^^^^^M^^^^69&CPAGE&700004591&FINEJ|PL
LOC|^^^^^M^^^^69&CPAGE&700004591&FINEJ||M|Etablissement juridique
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||ID_GLBL^Identifiant unique global^L|^69
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||CD^Code^L|^69
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||LBL^Libelle^L|^GRGAP
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||LBL_CRT^Libelle court^L|^Etab Hosp INTERCOMMUNAL
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||FNS^Code FINESS^L|^700004591
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||ADRS_1^Adresse 1^L|^4 Avenue de la VBF
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||ADRS_2^Adresse 2^L|^B.P. 4
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||ADRS_3^Adresse 3^L|^
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||CD_PSTL^Code postal^L|^70014
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||VL^Ville^L|^VESOUL CEDEX
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||INS^Code INSEE commune^L|^550
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||DT_OVRTR^Date d'ouverture^L|^19000101000000
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||DT_ACTVTN^Date d'activation^L|^19000101000000
MFE|MAD|||^^^^^ETBL_GRPQ^^^^GI&CPAGE&700004591&FINEJ|PL
LOC|^^^^^ETBL_GRPQ^^^^GI&CPAGE&700004591&FINEJ||ETBL_GRPQ|Etablissement géographique
LCH|^^^^^ETBL_GRPQ^^^^GI&CPAGE&700004591&FINEJ|||ID_GLBL^Identifiant unique global^L|^69GI
LCH|^^^^^ETBL_GRPQ^^^^GI&CPAGE&700004591&FINEJ|||CD^Code^L|^GI
LCH|^^^^^ETBL_GRPQ^^^^GI&CPAGE&700004591&FINEJ|||LBL^Libelle^L|^ne pas utiliser GIP
LCH|^^^^^ETBL_GRPQ^^^^GI&CPAGE&700004591&FINEJ|||LBL_CRT^Libelle court^L|^ne pas utiliser GIP
LCH|^^^^^ETBL_GRPQ^^^^GI&CPAGE&700004591&FINEJ|||FNS^Code FINESS^L|^888888888
LCH|^^^^^ETBL_GRPQ^^^^GI&CPAGE&700004591&FINEJ|||CTGR_S^Catégorie SAE^L|^103
LCH|^^^^^ETBL_GRPQ^^^^GI&CPAGE&700004591&FINEJ|||ADRS_1^Adresse 1^L|^
LCH|^^^^^ETBL_GRPQ^^^^GI&CPAGE&700004591&FINEJ|||ADRS_2^Adresse 2^L|^
LCH|^^^^^ETBL_GRPQ^^^^GI&CPAGE&700004591&FINEJ|||ADRS_3^Adresse 3^L|^
LCH|^^^^^ETBL_GRPQ^^^^GI&CPAGE&700004591&FINEJ|||CD_PSTL^Code postal^L|^
LCH|^^^^^ETBL_GRPQ^^^^GI&CPAGE&700004591&FINEJ|||VL^Ville^L|^
LCH|^^^^^ETBL_GRPQ^^^^GI&CPAGE&700004591&FINEJ|||DT_OVRTR^Date d'ouverture^L|^20991231235900
LCH|^^^^^ETBL_GRPQ^^^^GI&CPAGE&700004591&FINEJ|||DT_ACTVTN^Date d'activation^L|^20991231235900
LCH|^^^^^ETBL_GRPQ^^^^GI&CPAGE&700004591&FINEJ|||DT_FRMTR^Date de fermeture^L|^20991231235900
LCH|^^^^^ETBL_GRPQ^^^^GI&CPAGE&700004591&FINEJ|||DT_FN_ ACTVTN^Date de fin d'activation^L|^20991231235900
LRL|^^^^^ETBL_GRPQ^^^^GI&CPAGE&700004591&FINEJ|||ETBLSMNT^Relation établissement^L||^^^^^M^^^^69&CPAGE&700004591&FINEJ"""
    
    with Session(engine) as session:
        # Trouver ou créer un contexte GHT pour le test
        ght = session.exec(select(GHTContext).where(GHTContext.is_active == True)).first()
        if not ght:
            print("Création d'un contexte GHT de test...")
            ght = GHTContext(
                name="GHT Test",
                code="TEST",
                oid_root="1.2.250.1.213.1.1.1",
                is_active=True
            )
            session.add(ght)
            session.commit()
            session.refresh(ght)
        
        print(f"Utilisation du GHT: {ght.name} (id={ght.id})")
        print(f"\nTest d'injection du message MFN:\n{payload[:200]}...\n")
        
        try:
            from app.services.mfn_importer import import_mfn
            result = import_mfn(payload, session, ght)
            print(f"\n✓ Import MFN réussi!")
            print(f"Résultat: {result}")
            session.commit()
            print("✓ Session committed")
            
            # Vérifier ce qui a été créé
            from app.models_structure_fhir import EntiteJuridique, EntiteGeographique
            
            ej = session.exec(select(EntiteJuridique).where(EntiteJuridique.finess_ej == "700004591")).first()
            if ej:
                print(f"\n✓ Entité juridique créée:")
                print(f"  - ID: {ej.id}")
                print(f"  - Nom: {ej.name}")
                print(f"  - FINESS EJ: {ej.finess_ej}")
                print(f"  - Adresse: {ej.address_line}, {ej.postal_code} {ej.city}")
                print(f"  - GHT: {ej.ght_context_id}")
            else:
                print("\n⚠ Aucune entité juridique trouvée avec FINESS 700004591")
            
            eg = session.exec(select(EntiteGeographique).where(EntiteGeographique.finess == "888888888")).first()
            if eg:
                print(f"\n✓ Entité géographique créée:")
                print(f"  - ID: {eg.id}")
                print(f"  - Nom: {eg.name}")
                print(f"  - FINESS: {eg.finess}")
                print(f"  - Identifier: {eg.identifier}")
                print(f"  - Entité juridique ID: {eg.entite_juridique_id}")
                if eg.entite_juridique_id:
                    print(f"  ✓ Liée à l'EJ (ID={eg.entite_juridique_id})")
            else:
                print("\n⚠ Aucune entité géographique trouvée avec FINESS 888888888")
                
        except Exception as e:
            print(f"\n✗ ERREUR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
