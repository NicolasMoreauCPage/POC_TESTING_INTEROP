"""
Mapping des pages vers leur documentation correspondante.

Ce module fournit une fonction pour obtenir l'URL de documentation
contextuelle en fonction de l'URL de la page actuelle.
"""

from typing import Optional

# Mapping des patterns d'URL vers les fichiers de documentation
DOC_MAPPING = {
    # Validation
    "/validation": "/docs/02-Validation/README.md",
    "/validation/validate": "/docs/02-Validation/REGLES_VALIDATION_HL7v25.md",
    
    # Supervision des messages
    "/messages": "/docs/06-Integration/INTEGRATION_HL7v25_RECAP.md",
    "/messages/validate-dossier": "/docs/02-Validation/VALIDATION_DOSSIER.md",
    "/messages/send": "/docs/06-Integration/FILE_IMPORT_README.md",
    "/messages/rejections": "/docs/06-Integration/INTEGRATION_HL7v25_RECAP.md",
    
    # Endpoints
    "/endpoints": "/docs/06-Integration/ENDPOINTS_DEMO.md",
    
    # Scénarios
    "/scenarios": "/docs/08-Scenarios/scenario_date_update.md",
    
    # Patients
    "/patients": "/docs/04-Patient-Management/PATIENT_IMPROVEMENTS_RECAP.md",
    
    # Dossiers
    "/dossiers": "/docs/05-Architecture/dossier_types.md",
    
    # Structure
    "/structure": "/docs/EMISSION_STRUCTURE.md",
    "/structure/eg": "/docs/EMISSION_STRUCTURE.md",
    "/structure/poles": "/docs/EMISSION_STRUCTURE.md",
    "/structure/services": "/docs/EMISSION_STRUCTURE.md",
    "/structure/ufs": "/docs/EMISSION_STRUCTURE.md",
    "/structure/uh": "/docs/EMISSION_STRUCTURE.md",
    "/structure/chambres": "/docs/EMISSION_STRUCTURE.md",
    "/structure/lits": "/docs/EMISSION_STRUCTURE.md",
    
    # Émission
    "/emit": "/docs/07-Emission/emission_automatique.md",
    
    # IHE PAM
    "/ihe": "/docs/03-IHE-PAM/README.md",
    
    # Standards
    "/standards": "/docs/05-Architecture/STANDARDS.md",
    
    # Vocabulaires
    "/vocabularies": "/docs/02-Validation/INDEX_VALIDATION_PAM.md",
    
    # Documentation générale
    "/": "/docs/INDEX.md",
    "/documentation": "/docs/INDEX.md",
    "/guide": "/docs/01-Getting-Started/README.md",
}


def get_doc_url(page_path: str) -> Optional[str]:
    """
    Retourne l'URL de documentation pour une page donnée.
    
    Args:
        page_path: Chemin de la page actuelle (ex: "/validation", "/messages")
        
    Returns:
        URL du fichier de documentation correspondant, ou None si aucune doc n'existe
    """
    # Recherche exacte
    if page_path in DOC_MAPPING:
        return DOC_MAPPING[page_path]
    
    # Recherche par préfixe (pour les pages avec paramètres)
    for pattern, doc_url in DOC_MAPPING.items():
        if page_path.startswith(pattern + "/") or page_path.startswith(pattern + "?"):
            return doc_url
    
    return None


def get_doc_title(page_path: str) -> str:
    """
    Retourne le titre de la documentation pour une page donnée.
    
    Args:
        page_path: Chemin de la page actuelle
        
    Returns:
        Titre de la documentation
    """
    doc_titles = {
        "/validation": "Validation HL7 v2.5",
        "/messages": "Supervision des messages",
        "/messages/validate-dossier": "Validation de dossier",
        "/endpoints": "Configuration des endpoints",
        "/scenarios": "Scénarios IHE PAM",
        "/patients": "Gestion des patients",
        "/dossiers": "Types de dossiers",
        "/structure": "Structure organisationnelle",
        "/standards": "Standards et conformité",
        "/vocabularies": "Vocabulaires et tables de codes",
        "/": "Documentation générale",
        "/documentation": "Documentation générale",
        "/guide": "Guide de démarrage",
    }
    
    # Recherche exacte
    if page_path in doc_titles:
        return doc_titles[page_path]
    
    # Recherche par préfixe
    for pattern, title in doc_titles.items():
        if page_path.startswith(pattern + "/") or page_path.startswith(pattern + "?"):
            return title
    
    return "Documentation"
