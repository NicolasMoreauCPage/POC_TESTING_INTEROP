"""Analyse tous les fichiers Markdown et génère un rapport de réorganisation."""
import os
from pathlib import Path
from collections import defaultdict

# Catégories de documentation
CATEGORIES = {
    "validation": ["validation", "datatypes", "ordre", "segment", "règles", "conformité"],
    "ihe_pam": ["ihe", "pam", "zbe", "mfn", "structure"],
    "patient": ["patient", "rgpd", "formulaire", "identif"],
    "architecture": ["architecture", "workflow", "transition", "état"],
    "integration": ["integration", "hl7", "fhir", "mllp", "endpoint", "file"],
    "emission": ["emission", "automatique", "sender"],
    "admin": ["namespace", "finess", "dossier"],
}

def analyze_md_files():
    """Analyse tous les fichiers .md du projet."""
    root = Path("/home/nico/Travail/Fhir_MedBridgeData/MedData_Bridge")
    doc_dir = root / "Doc"
    
    # Fichiers à la racine
    root_files = [
        f for f in root.iterdir() 
        if f.suffix == ".md" and f.name not in [".pytest_cache", ".venv"]
    ]
    
    # Fichiers dans Doc/
    doc_files = list(doc_dir.glob("*.md"))
    
    # Catégoriser automatiquement
    categorized = defaultdict(list)
    uncategorized = []
    
    all_files = root_files + doc_files
    
    for filepath in all_files:
        filename = filepath.name.lower()
        content_sample = ""
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content_sample = f.read(500).lower()
        except Exception:
            pass
        
        # Tentative de catégorisation
        matched = False
        for category, keywords in CATEGORIES.items():
            if any(kw in filename or kw in content_sample for kw in keywords):
                categorized[category].append(filepath)
                matched = True
                break
        
        if not matched:
            uncategorized.append(filepath)
    
    # Rapport
    print("=" * 80)
    print("ANALYSE DES FICHIERS MARKDOWN")
    print("=" * 80)
    
    print(f"\n📁 Total fichiers analysés: {len(all_files)}")
    print(f"   - À la racine: {len(root_files)}")
    print(f"   - Dans Doc/: {len(doc_files)}")
    
    print("\n" + "=" * 80)
    print("CATÉGORISATION")
    print("=" * 80)
    
    for category in sorted(categorized.keys()):
        files = categorized[category]
        print(f"\n📂 {category.upper().replace('_', ' ')} ({len(files)} fichiers)")
        for f in files:
            rel_path = f.relative_to(root)
            print(f"   - {rel_path}")
    
    if uncategorized:
        print(f"\n❓ NON CATÉGORISÉS ({len(uncategorized)} fichiers)")
        for f in uncategorized:
            rel_path = f.relative_to(root)
            print(f"   - {rel_path}")
    
    # Détection de doublons/similarités
    print("\n" + "=" * 80)
    print("DÉTECTION DE DOUBLONS/SIMILARITÉS")
    print("=" * 80)
    
    # Groupes suspects
    groups = {
        "Formulaire Patient": [
            "FORMULAIRE_PATIENT_RESUME.md",
            "POINT_GENERAL_FORMULAIRE_PATIENT.md",
            "formulaire_patient_rgpd.md",
            "PATIENT_IMPROVEMENTS_RECAP.md"
        ],
        "Validation": [
            "INDEX_VALIDATION_PAM.md",
            "RESUME_VALIDATION_DATATYPES.md",
            "REGLES_VALIDATION_HL7v25.md",
            "REGLES_DATATYPES_COMPLEXES_HL7v25.md",
            "VALIDATION_ORDRE_SEGMENTS.md"
        ],
        "Émission": [
            "emission_automatique.md",
            "emission_automatique_debug.md",
            "etat_reel_emission.md",
            "correction_a31_emission.md"
        ],
        "Intégration": [
            "INTEGRATION_HL7v25_RECAP.md",
            "INTEGRATION_DATATYPES_COMPLEXES_RECAP.md"
        ]
    }
    
    for group_name, filenames in groups.items():
        print(f"\n🔗 Groupe: {group_name}")
        for fname in filenames:
            full_path = root / fname if (root / fname).exists() else doc_dir / fname
            if full_path.exists():
                print(f"   ✓ {fname}")
            else:
                print(f"   ✗ {fname} (non trouvé)")
    
    # Proposition de réorganisation
    print("\n" + "=" * 80)
    print("PROPOSITION DE RÉORGANISATION")
    print("=" * 80)
    
    structure = {
        "Doc/01-Getting-Started/": ["README.md", "CONTRIBUTING.md"],
        "Doc/02-Validation/": [
            "INDEX_VALIDATION_PAM.md",
            "RESUME_VALIDATION_DATATYPES.md",
            "REGLES_VALIDATION_HL7v25.md",
            "REGLES_DATATYPES_COMPLEXES_HL7v25.md",
            "VALIDATION_ORDRE_SEGMENTS.md"
        ],
        "Doc/03-IHE-PAM/": [
            "conformite_zbe.md",
            "namespaces_mouvement_finess.md"
        ],
        "Doc/04-Patient-Management/": [
            "PATIENT_IMPROVEMENTS_RECAP.md",
            "formulaire_patient_rgpd.md",
            "spec_patient_identifiers_addresses.md"
        ],
        "Doc/05-Architecture/": [
            "architecture_workflows_proposal.md",
            "dossier_types.md",
            "STANDARDS.md"
        ],
        "Doc/06-Integration/": [
            "INTEGRATION_HL7v25_RECAP.md",
            "INTEGRATION_DATATYPES_COMPLEXES_RECAP.md",
            "FILE_IMPORT_README.md",
            "file_based_import.md",
            "endpoints_hierarchical_organization.md"
        ],
        "Doc/07-Emission/": [
            "emission_automatique.md",
            "emission_automatique_debug.md",
            "etat_reel_emission.md",
            "correction_a31_emission.md"
        ],
        "Doc/08-Scenarios/": [
            "scenario_date_update.md"
        ],
        "Doc/_Archived/": [
            "FORMULAIRE_PATIENT_RESUME.md",  # fusionné dans PATIENT_IMPROVEMENTS
            "POINT_GENERAL_FORMULAIRE_PATIENT.md"  # fusionné dans PATIENT_IMPROVEMENTS
        ]
    }
    
    for new_dir, files in structure.items():
        print(f"\n📁 {new_dir}")
        for fname in files:
            print(f"   - {fname}")
    
    return categorized, uncategorized, structure

if __name__ == "__main__":
    analyze_md_files()
