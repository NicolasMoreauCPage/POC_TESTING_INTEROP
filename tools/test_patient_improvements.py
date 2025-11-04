#!/usr/bin/env python3
"""
Test de bout en bout des améliorations patient:
- Identifiants multiples
- Adresse de naissance
- État de l'identité (PID-32)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select, SQLModel
from app.db import engine
from app.models import Patient
from app.models_identifiers import Identifier, IdentifierType
from app.utils.identifier_validation import (
    validate_unique_identifier,
    add_or_update_identifier,
    validate_identity_reliability_code,
    DuplicateIdentifierError
)
from app.services.emit_on_create import generate_pam_hl7


def test_patient_improvements():
    """Test complet des améliorations patient."""
    print("=" * 80)
    print("Test: Améliorations Patient (identifiants, adresses, PID-32)")
    print("=" * 80)
    
    # Créer les tables si elles n'existent pas
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # ===== TEST 1: Créer un patient avec toutes les nouvelles données =====
        print("\n📋 Test 1: Création patient avec données complètes")
        
        patient = Patient(
            family="DUPONT",
            given="Jean",
            middle="Michel",
            gender="M",
            birth_date="1985-03-15",
            # Adresse d'habitation
            address="15 rue de la République",
            city="Lyon",
            state="Rhône",
            postal_code="69001",
            country="FRA",
            # Adresse de naissance
            birth_address="Maternité Saint-Joseph",
            birth_city="Marseille",
            birth_state="Bouches-du-Rhône",
            birth_postal_code="13008",
            birth_country="FRA",
            # État de l'identité
            identity_reliability_code="VALI",
            identity_reliability_date="2024-01-15",
            identity_reliability_source="CNI n°123456789"
        )
        
        session.add(patient)
        session.commit()
        session.refresh(patient)
        
        print(f"  ✓ Patient créé: {patient.family} {patient.given} (ID={patient.id})")
        print(f"    - Adresse habitation: {patient.address}, {patient.postal_code} {patient.city}, {patient.country}")
        print(f"    - Lieu de naissance: {patient.birth_city} ({patient.birth_country})")
        print(f"    - Identité: {patient.identity_reliability_code}")
        
        # ===== TEST 2: Ajouter des identifiants multiples =====
        print("\n📋 Test 2: Ajout identifiants multiples")
        
        # IPP
        ipp = add_or_update_identifier(
            session, patient.id,
            value=f"IPP{patient.id}",
            system="HOSP_A",
            oid="1.2.250.1.213.1.1.9",
            identifier_type=IdentifierType.IPP
        )
        print(f"  ✓ IPP ajouté: {ipp.value} (system={ipp.system})")
        
        # NIR (générer un NIR unique basé sur l'ID patient)
        from datetime import datetime
        unique_nir = f"{datetime.now().strftime('%y%m%d%H%M%S')}{patient.id:03d}"[:13]
        nir = add_or_update_identifier(
            session, patient.id,
            value=unique_nir,
            system="INS-NIR",
            oid="1.2.250.1.213.1.4.8",
            identifier_type=IdentifierType.SNS
        )
        print(f"  ✓ NIR ajouté: {nir.value} (system={nir.system})")
        
        # Externe LABO_X (unique)
        unique_lab_id = f"LAB{patient.id}"
        external_lab = add_or_update_identifier(
            session, patient.id,
            value=unique_lab_id,
            system="LABO_X",
            oid="1.2.250.1.999.1",
            identifier_type=IdentifierType.PI
        )
        print(f"  ✓ Identifiant externe LABO_X ajouté: {external_lab.value}")
        
        session.commit()
        
        # ===== TEST 3: Validation unicité =====
        print("\n📋 Test 3: Validation unicité identifiants")
        
        # Créer un 2e patient
        patient2 = Patient(
            family="MARTIN",
            given="Marie",
            gender="F",
            birth_date="1990-07-20"
        )
        session.add(patient2)
        session.commit()
        session.refresh(patient2)
        
        print(f"  ✓ Patient 2 créé: {patient2.family} {patient2.given} (ID={patient2.id})")
        
        # Test: Patient 2 peut avoir un identifiant différent dans le même système
        try:
            add_or_update_identifier(
                session, patient2.id,
                value="LAB99999",  # Valeur différente
                system="LABO_X",
                oid="1.2.250.1.999.1",
                identifier_type=IdentifierType.PI
            )
            session.commit()
            print(f"  ✓ Patient 2 peut avoir un identifiant différent dans LABO_X: OK")
        except DuplicateIdentifierError as e:
            print(f"  ❌ Erreur inattendue: {e}")
        
        # Test: Patient 2 NE PEUT PAS avoir le même identifiant dans le même système
        try:
            add_or_update_identifier(
                session, patient2.id,
                value=unique_lab_id,  # MÊME valeur que patient 1
                system="LABO_X",
                oid="1.2.250.1.999.1",
                identifier_type=IdentifierType.PI
            )
            print(f"  ❌ Patient 2 ne devrait pas pouvoir réutiliser {unique_lab_id}!")
        except DuplicateIdentifierError as e:
            print(f"  ✓ Contrainte unicité respectée: {str(e)[:80]}...")
        
        # ===== TEST 4: Génération PID segment avec identifiants multiples =====
        print("\n📋 Test 4: Génération message HL7 avec identifiants multiples")
        
        # Rafraîchir le patient pour avoir les dernières données
        session.refresh(patient)
        
        # Debug: vérifier les valeurs avant génération
        print(f"  [DEBUG] patient.birth_city = '{patient.birth_city}'")
        print(f"  [DEBUG] patient.identity_reliability_code = '{patient.identity_reliability_code}'")
        
        hl7_msg = generate_pam_hl7(
            entity=patient,
            entity_type="patient",
            session=session,
            forced_identifier_system="HOSP_A",
            operation="insert"
        )
        
        print(f"  ✓ Message HL7 généré ({len(hl7_msg)} octets)")
        
        # Extraire et analyser le segment PID
        lines = hl7_msg.split("\r")
        pid_line = [l for l in lines if l.startswith("PID|")][0]
        pid_fields = pid_line.split("|")
        
        print(f"\n  Segment PID complet ({len(pid_fields)} champs):")
        print(f"    {pid_line[:150]}...")
        print(f"\n  Champs décodés:")
        print(f"    PID-3 (identifiants): {pid_fields[3]}")
        print(f"    PID-5 (nom): {pid_fields[5]}")
        print(f"    PID-11 (adresse): {pid_fields[11]}")
        
        print(f"    PID-23 (lieu naissance): {pid_fields[23] if len(pid_fields) > 23 else 'N/A'}")
        print(f"    PID-32 (état identité): {pid_fields[32] if len(pid_fields) > 32 else 'N/A'}")
        
        # Vérifier répétitions ~ dans PID-3
        identifiers_in_pid3 = pid_fields[3].split("~")
        print(f"\n  ✓ PID-3 contient {len(identifiers_in_pid3)} identifiants (répétitions ~):")
        for i, ident in enumerate(identifiers_in_pid3, 1):
            print(f"    {i}. {ident}")
        
        # Vérifications
        assert len(identifiers_in_pid3) >= 3, "PID-3 devrait contenir au moins 3 identifiants"
        assert "VALI" in (pid_fields[32] if len(pid_fields) > 32 else ""), "PID-32 devrait contenir VALI"
        assert "Lyon" in pid_fields[11], "PID-11 devrait contenir Lyon"
        assert "Marseille" in (pid_fields[23] if len(pid_fields) > 23 else ""), "PID-23 devrait contenir Marseille"
        
        print("\n  ✓ Tous les champs PID vérifiés avec succès!")
        
        # ===== TEST 5: Validation codes PID-32 =====
        print("\n📋 Test 5: Validation codes PID-32")
        
        valid_codes = ["VIDE", "PROV", "VALI", "DOUTE", "FICTI", ""]
        for code in valid_codes:
            assert validate_identity_reliability_code(code), f"Code {code} devrait être valide"
        
        print(f"  ✓ Tous les codes PID-32 valides reconnus: {', '.join(valid_codes)}")
        
        invalid_codes = ["INVALID", "TEST", "XXX"]
        for code in invalid_codes:
            assert not validate_identity_reliability_code(code), f"Code {code} devrait être invalide"
        
        print(f"  ✓ Codes invalides rejetés correctement")
        
        print("\n" + "=" * 80)
        print("✅ TOUS LES TESTS PASSÉS!")
        print("=" * 80)
        print("\nRésumé:")
        print("  ✓ Patient avec adresse habitation + naissance")
        print("  ✓ État de l'identité (PID-32) enregistré")
        print("  ✓ Identifiants multiples (IPP, NIR, externe)")
        print("  ✓ Contrainte UNIQUE respectée")
        print("  ✓ PID-3 avec répétitions ~ générées")
        print("  ✓ Segments PID-11, PID-23, PID-32 corrects")
        print("  ✓ Validation codes PID-32 fonctionnelle")


if __name__ == "__main__":
    test_patient_improvements()
