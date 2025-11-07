"""
Helpers pour les formulaires avec vocabulaires
"""
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from app.models_vocabulary import VocabularySystem, VocabularyValue

def get_vocabulary_field(
    session: Session,
    system_name: str,
    required: bool = False,
    current_value: Optional[str] = None,
    include_empty: bool = True,
    field_name: Optional[str] = None,
    field_label: Optional[str] = None
) -> Dict[str, Any]:
    """
    Génère la configuration d'un champ de formulaire pour un vocabulaire.
    
    Args:
        session: Session SQLModel
        system_name: Nom du système de vocabulaire (ex: "administrative-gender")
        required: Si True, le champ est obligatoire
        current_value: Valeur actuelle (code) si elle existe
        include_empty: Si True, ajoute une option vide
        field_name: Surcharge du nom du champ (par défaut <system_name>_code)
        field_label: Surcharge du label (par défaut label du système)
    
    Returns:
        Dict contenant la configuration du champ pour le template form.html
    """
    # Récupérer le système et ses valeurs
    system = session.exec(
        select(VocabularySystem).where(VocabularySystem.name == system_name)
    ).first()
    
    if not system:
        raise ValueError(f"Système de vocabulaire '{system_name}' non trouvé")
    
    # Construire les options
    options = []
    if include_empty:
        options.append({"value": "", "label": "Sélectionnez..."})
    
    # Ajouter les valeurs actives triées par ordre
    options.extend([
        {"value": val.code, "label": val.display}
        for val in sorted(system.values, key=lambda x: x.order)
        if val.is_active
    ])
    
    # Préparer la configuration du champ
    return {
        "name": field_name or f"{system_name}_code",
        "label": field_label or system.label,
        "type": "select",
        "required": required,
        "options": options,
        "value": current_value,
        "help": system.description if system.description else None
    }

def get_vocabulary_display(
    session: Session,
    system_name: str,
    code: str
) -> Optional[str]:
    """
    Récupère le libellé d'affichage pour un code dans un système.
    
    Args:
        session: Session SQLModel
        system_name: Nom du système de vocabulaire
        code: Code de la valeur
    
    Returns:
        Le libellé d'affichage ou None si non trouvé
    """
    value = session.exec(
        select(VocabularyValue)
        .join(VocabularySystem)
        .where(VocabularySystem.name == system_name)
        .where(VocabularyValue.code == code)
    ).first()
    
    return value.display if value else None

def get_vocabulary_mapping(
    session: Session,
    source_system: str,
    source_code: str,
    target_system: str
) -> Optional[str]:
    """
    Traduit un code d'un système vers un autre via les mappings.
    
    Args:
        session: Session SQLModel
        source_system: Nom du système source
        source_code: Code dans le système source
        target_system: Nom du système cible
    
    Returns:
        Le code correspondant dans le système cible ou None si pas de mapping
    """
    # Récupérer le système source
    source = session.exec(
        select(VocabularySystem).where(VocabularySystem.name == source_system)
    ).first()
    
    if not source:
        return None
        
    # Récupérer le mapping via la valeur source
    source_value = session.exec(
        select(VocabularyValue)
        .where(VocabularyValue.system_id == source.id)
        .where(VocabularyValue.code == source_code)
    ).first()
    
    if not source_value:
        return None
    
    # Récupérer le mapping vers le système cible
    mapping = session.exec(
        select(VocabularyValue)
        .join(VocabularySystem)
        .where(VocabularySystem.name == target_system)
        .where(VocabularyValue.code == source_value.code)
    ).first()
    
    return mapping.code if mapping else None
