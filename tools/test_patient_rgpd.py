#!/usr/bin/env python3
"""
Test du formulaire Patient - Conformité RGPD
Vérifie que les champs interdits ne sont pas collectés.
"""
import sys
from sqlmodel import Session, select, SQLModel
from app.db import engine
from app.models import Patient

def test_patient_rgpd_compliance():
    """Vérifie la conformité RGPD du formulaire patient."""
    print("🧪 Test de conformité RGPD du formulaire Patient")
    print("=" * 60)
    
    # Créer les tables si elles n'existent pas
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # 1. Vérifier les patients existants
        patients = session.exec(select(Patient)).all()
        print(f"\n📊 {len(patients)} patients en base de données")
        
        # 2. Vérifier si des champs interdits sont remplis
        issues = []
        
        for patient in patients:
            if patient.race:
                issues.append(f"Patient #{patient.id} a race='{patient.race}' (INTERDIT RGPD)")
            if patient.religion:
                issues.append(f"Patient #{patient.id} a religion='{patient.religion}' (INTERDIT RGPD)")
            if patient.administrative_gender and patient.gender:
                issues.append(f"Patient #{patient.id} a gender ET administrative_gender (DOUBLON)")
        
        # 3. Afficher les résultats
        if issues:
            print(f"\n⚠️  {len(issues)} problème(s) de conformité détecté(s):")
            for issue in issues:
                print(f"   • {issue}")
            print("\n💡 Action recommandée : Nettoyer ces données")
            return False
        else:
            print("\n✅ Aucun problème de conformité RGPD détecté")
            return True
        
        # 4. Statistiques sur les champs utilisés
        print(f"\n📈 Statistiques d'utilisation des champs:")
        print(f"   • NIR renseigné : {sum(1 for p in patients if p.nir)}/{len(patients)}")
        print(f"   • Statut marital : {sum(1 for p in patients if p.marital_status)}/{len(patients)}")
        print(f"   • Nationalité : {sum(1 for p in patients if p.nationality)}/{len(patients)}")
        print(f"   • Téléphone : {sum(1 for p in patients if p.phone)}/{len(patients)}")
        print(f"   • Email : {sum(1 for p in patients if p.email)}/{len(patients)}")

def clean_legacy_data():
    """Nettoie les données legacy non conformes (race/religion)."""
    print("\n🧹 Nettoyage des données non conformes RGPD")
    print("=" * 60)
    
    with Session(engine) as session:
        patients = session.exec(select(Patient)).all()
        cleaned = 0
        
        for patient in patients:
            modified = False
            if patient.race:
                print(f"   Nettoyage patient #{patient.id}: race='{patient.race}' → None")
                patient.race = None
                modified = True
            if patient.religion:
                print(f"   Nettoyage patient #{patient.id}: religion='{patient.religion}' → None")
                patient.religion = None
                modified = True
            if patient.administrative_gender and patient.gender:
                print(f"   Nettoyage patient #{patient.id}: administrative_gender='{patient.administrative_gender}' → None (doublon)")
                patient.administrative_gender = None
                modified = True
            
            if modified:
                session.add(patient)
                cleaned += 1
        
        if cleaned > 0:
            session.commit()
            print(f"\n✅ {cleaned} patient(s) nettoyé(s)")
        else:
            print("\n✅ Aucune donnée à nettoyer")

if __name__ == "__main__":
    # Test conformité
    compliant = test_patient_rgpd_compliance()
    
    # Proposer nettoyage si problèmes détectés
    if not compliant:
        print("\n" + "=" * 60)
        response = input("Voulez-vous nettoyer les données non conformes ? (oui/non): ")
        if response.lower() in ['oui', 'o', 'y', 'yes']:
            clean_legacy_data()
            print("\n" + "=" * 60)
            print("🔄 Nouvelle vérification après nettoyage:")
            test_patient_rgpd_compliance()
        else:
            print("\n⚠️  Nettoyage annulé - données non conformes conservées")
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ Test terminé")
    sys.exit(0 if compliant else 1)
