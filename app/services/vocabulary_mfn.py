"""
Service de chargement des segments HL7 pour les messages MFN
"""
from typing import List, Dict
from app.models_vocabulary import VocabularySystem, VocabularyValue, VocabularySystemType

def create_mfn_segment_fields() -> List[VocabularySystem]:
    """Crée les vocabulaires pour les segments MFN"""
    systems = []
    
    # Table Z99 - Types de segments locaux
    z99_system = VocabularySystem(
        name="local-segment-type",
        label="Type de segments locaux (Z99)",
        system_type=VocabularySystemType.LOCAL,
        is_user_defined=False,
        description="Types de segments Z99 pour MFN"
    )
    
    z99_values = [
        VocabularyValue(code="MSH", display="Message Header", definition="En-tête du message", order=1),
        VocabularyValue(code="MFI", display="Master File Identification", definition="Identification du fichier maître", order=2),
        VocabularyValue(code="Z99", display="Structure Info", definition="Information sur la structure", order=3),
        VocabularyValue(code="NTE", display="Notes", definition="Notes additionnelles", order=4)
    ]
    z99_system.values = z99_values
    systems.append(z99_system)
    
    # Champs du segment Z99 (local)
    z99_fields = VocabularySystem(
        name="z99-field-content",
        label="Contenu des champs Z99",
        system_type=VocabularySystemType.LOCAL,
        is_user_defined=False,
        description="Définition du contenu des champs du segment Z99"
    )
    
    field_values = [
        VocabularyValue(code="TYPE", display="Type structure", definition="Type de la structure (service, UF...)", order=1),
        VocabularyValue(code="CODE", display="Code", definition="Code de la structure", order=2),
        VocabularyValue(code="LIBELLE", display="Libellé", definition="Libellé de la structure", order=3),
        VocabularyValue(code="PARENT", display="Parent", definition="Code de la structure parente", order=4),
        VocabularyValue(code="STATUT", display="Statut", definition="Statut de la structure", order=5),
        VocabularyValue(code="SPECIALITE", display="Spécialité", definition="Code de spécialité", order=6),
        VocabularyValue(code="DATE_DEBUT", display="Date début", definition="Date de début de validité", order=7),
        VocabularyValue(code="DATE_FIN", display="Date fin", definition="Date de fin de validité", order=8)
    ]
    z99_fields.values = field_values
    systems.append(z99_fields)
    
    # Types de structures
    structure_type = VocabularySystem(
        name="structure-type",
        label="Type de structure",
        system_type=VocabularySystemType.LOCAL,
        is_user_defined=False,
        description="Types de structures dans les messages MFN"
    )
    
    type_values = [
        VocabularyValue(code="UF", display="Unité Fonctionnelle", definition="Unité fonctionnelle", order=1),
        VocabularyValue(code="US", display="Unité de Soins", definition="Unité de soins", order=2),
        VocabularyValue(code="UA", display="Unité d'Hébergement", definition="Unité d'hébergement", order=3),
        VocabularyValue(code="BAT", display="Bâtiment", definition="Bâtiment", order=4),
        VocabularyValue(code="SITE", display="Site", definition="Site géographique", order=5),
        VocabularyValue(code="POLE", display="Pôle", definition="Pôle médical", order=6),
        VocabularyValue(code="SERV", display="Service", definition="Service médical", order=7)
    ]
    structure_type.values = type_values
    systems.append(structure_type)
    
    return systems