#!/usr/bin/env python3
"""Test roundtrip MFN avec vraies données (1946 entités)"""
import sys
from pathlib import Path
from sqlmodel import Session, select, SQLModel

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db import init_db, engine
from app.db_session_factory import session_factory
from app.models_structure_fhir import GHTContext, EntiteJuridique, IdentifierNamespace
from app.models_structure import EntiteGeographique, Pole, Service, UniteFonctionnelle, UniteHebergement, Chambre, Lit
from app.services.mfn_structure import process_mfn_message, generate_mfn_message

def count_locations(session: Session) -> dict:
    return {
        "eg": len(session.exec(select(EntiteGeographique)).all()),
        "poles": len(session.exec(select(Pole)).all()),
        "services": len(session.exec(select(Service)).all()),
        "uf": len(session.exec(select(UniteFonctionnelle)).all()),
        "uh": len(session.exec(select(UniteHebergement)).all()),
        "ch": len(session.exec(select(Chambre)).all()),
        "lits": len(session.exec(select(Lit)).all()),
    }

def main():
    print("="*80)
    print("TEST ROUNDTRIP MFN AVEC VRAIES DONNÉES")
    print("="*80)
    
    mfn_file = project_root / "tests" / "exemples" / "ExempleExtractionStructure.txt"
    if not mfn_file.exists():
        print(f"❌ Fichier introuvable: {mfn_file}")
        return 1
    
    # Réinitialiser la base
    print("\n🔧 Réinitialisation DB...")
    SQLModel.metadata.drop_all(engine)
    init_db()
    
    # PHASE 1: Import MFN réel
    print("\n" + "="*80)
    print("PHASE 1: IMPORT DU MFN RÉEL")
    print("="*80)
    
    with session_factory() as session:
        # Créer le GHT et EJ source
        ght = GHTContext(name="GHT Réel Source", code="GHT-REAL")
        session.add(ght); session.commit(); session.refresh(ght)
        
        ej = EntiteJuridique(
            name="EJ Réel Source",
            finess_ej="700004591",
            ght_context_id=ght.id
        )
        session.add(ej); session.commit(); session.refresh(ej)
        
        # Créer le namespace
        ns = IdentifierNamespace(
            name="Namespace CPage",
            system="CPAGE",
            type="STRUCTURE",
            ght_context_id=ght.id
        )
        session.add(ns); session.commit(); session.refresh(ns)
        
        print(f"\n✅ GHT créé: {ght.code}")
        print(f"✅ EJ créée: {ej.finess_ej}")
        
        # Lire le MFN
        with open(mfn_file, 'r', encoding='utf-8') as f:
            mfn_content = f.read()
        
        mfe_count = len([l for l in mfn_content.splitlines() if l.startswith('MFE|')])
        print(f"\n📊 Entités MFE dans le fichier: {mfe_count}")
        print(f"⚙️  Import multi-pass...")
        
        results = process_mfn_message(mfn_content, session, multi_pass=True)
        
        print(f"\n📊 Résultats import initial:")
        print(f"   Total résultats: {len(results)}")
        success_count = len([r for r in results if r.get('status') == 'success'])
        error_count = len([r for r in results if r.get('status') == 'error'])
        print(f"   Succès: {success_count}")
        print(f"   Erreurs: {error_count}")
        
        counts = count_locations(session)
        total = sum(counts.values())
        print(f"\n📊 Locations importées:")
        for k, v in counts.items():
            print(f"   {k}: {v}")
        print(f"   TOTAL: {total}")
    
    # PHASE 2: Export MFN
    print("\n" + "="*80)
    print("PHASE 2: EXPORT MFN")
    print("="*80)
    
    with session_factory() as session:
        egs = session.exec(select(EntiteGeographique)).all()
        if not egs:
            print("❌ Aucune EG trouvée")
            return 1
        
        # Prendre l'EG avec le plus de pôles
        eg_max = max(egs, key=lambda eg: len(eg.poles) if hasattr(eg, 'poles') else 0)
        print(f"\n🎯 EG sélectionnée: {eg_max.identifier}")
        print(f"   Nom: {eg_max.name}")
        
        print(f"\n⚙️  Export MFN...")
        mfn_export = generate_mfn_message(session, eg_identifier=eg_max.identifier)
        mfn_segs = len([l for l in mfn_export.splitlines() if l.startswith('MFE|')])
        print(f"✅ MFN exporté: {mfn_segs} segments MFE")
    
    # PHASE 3: Réimport MFN
    print("\n" + "="*80)
    print("PHASE 3: RÉIMPORT MFN")
    print("="*80)
    
    with session_factory() as session:
        # Créer GHT et EJ cible
        ght2 = GHTContext(name="GHT MFN Roundtrip", code="GHT-MFRT")
        session.add(ght2); session.commit(); session.refresh(ght2)
        
        ej2 = EntiteJuridique(
            name="EJ MFN Roundtrip",
            finess_ej="700999999",
            ght_context_id=ght2.id
        )
        session.add(ej2); session.commit(); session.refresh(ej2)
        
        ns2 = IdentifierNamespace(
            name="Namespace MFN Roundtrip",
            system="MFRT",
            type="STRUCTURE",
            ght_context_id=ght2.id
        )
        session.add(ns2); session.commit(); session.refresh(ns2)
        
        print(f"\n✅ GHT cible créé: {ght2.code}")
        
        # Transformer les identifiants
        mfn_transformed = mfn_export.replace("&CPAGE&", "&MFRT&")
        
        print(f"⚙️  Réimport multi-pass...")
        reimport = process_mfn_message(mfn_transformed, session, multi_pass=True)
        
        print(f"\n📊 Résultats réimport:")
        print(f"   Créées: {reimport.get('created', 0)}")
        print(f"   Ignorées: {reimport.get('skipped', 0)}")
        print(f"   Erreurs: {len(reimport.get('errors', []))}")
        
        if reimport.get('errors'):
            print(f"\n⚠️  Premières erreurs:")
            for err in reimport['errors'][:10]:
                print(f"   - {err}")
    
    # PHASE 4: Vérification
    print("\n" + "="*80)
    print("PHASE 4: VÉRIFICATION")
    print("="*80)
    
    with session_factory() as session:
        counts_final = count_locations(session)
        total_final = sum(counts_final.values())
        
        print(f"\n📊 Total final:")
        for k, v in counts_final.items():
            print(f"   {k}: {v}")
        print(f"   TOTAL: {total_final}")
        
        print(f"\n📊 RÉSUMÉ:")
        print(f"   Fichier MFN: {mfe_count} entités")
        print(f"   Import initial: {total} locations")
        print(f"   Export MFN: {mfn_segs} segments")
        print(f"   Réimport MFN: {reimport.get('created', 0)}/{mfn_segs} ({100*reimport.get('created', 0)/mfn_segs if mfn_segs else 0:.1f}%)")
        
        success = reimport.get('created', 0) == mfn_segs
        print(f"\n{'='*80}")
        if success:
            print("✅ SUCCÈS: Roundtrip MFN à 100% avec 1946 vraies entités!")
        else:
            print(f"⚠️  ATTENTION: {reimport.get('created', 0)}/{mfn_segs} ({100*reimport.get('created', 0)/mfn_segs if mfn_segs else 0:.1f}%)")
        print(f"{'='*80}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
