"""
Service de chargement des vocabulaires IHE PAM France CP
"""
from typing import List
from app.models_vocabulary import VocabularySystem, VocabularyValue, VocabularySystemType, VocabularyMapping

def create_patient_type_vocabularies() -> List[VocabularySystem]:
    """Crée les vocabulaires pour le type de patient"""
    systems = []
    
    # Table personnalisée PAM France 
    ihe_system = VocabularySystem(
        name="patient-type-fr",
        label="Type de patient",
        system_type=VocabularySystemType.LOCAL,
        is_user_defined=False,
        description="Types de patient selon IHE PAM France"
    )
    
    ihe_values = [
        VocabularyValue(code="H", display="Hospitalisé", definition="Patient hospitalisé", order=1),
        VocabularyValue(code="C", display="Consultation", definition="Patient en consultation", order=2),
        VocabularyValue(code="U", display="Urgence", definition="Patient en urgence", order=3),
        VocabularyValue(code="S", display="Séance", definition="Patient en séance", order=4),
        VocabularyValue(code="P", display="Permission", definition="Patient en permission", order=5)
    ]
    ihe_system.values = ihe_values
    systems.append(ihe_system)
    
    return systems

def create_patient_location_vocabularies() -> List[VocabularySystem]:
    """Crée les vocabulaires pour la localisation du patient"""
    systems = []
    
    # Types d'unités fonctionnelles
    service_type = VocabularySystem(
        name="service-type-fr",
        label="Type d'UF",
        system_type=VocabularySystemType.LOCAL,
        is_user_defined=False,
        description="Types d'unités fonctionnelles selon IHE PAM France"
    )
    
    service_values = [
        VocabularyValue(code="UM", display="UF Médicale", definition="Unité fonctionnelle médicale", order=1),
        VocabularyValue(code="UC", display="UF Soins", definition="Unité fonctionnelle de soins", order=2),
        VocabularyValue(code="UH", display="UF Hébergement", definition="Unité fonctionnelle d'hébergement", order=3),
        VocabularyValue(code="UA", display="UF Administrative", definition="Unité fonctionnelle administrative", order=4),
        VocabularyValue(code="UT", display="UF Technique", definition="Unité fonctionnelle technique (plateau technique)", order=5)
    ]
    service_type.values = service_values
    systems.append(service_type)
    
    # Points de service (HL7)
    pnt_loc_type = VocabularySystem(
        name="point-of-care-type",
        label="Type de point de service (HL7)",
        oid="2.16.840.1.113883.12.302",
        system_type=VocabularySystemType.HL7V2,
        is_user_defined=False,
        description="Table HL7 0302 - Point of Care Type"
    )
    
    pnt_loc_values = [
        VocabularyValue(code="C", display="Clinique", definition="Service clinique", order=1),
        VocabularyValue(code="D", display="Département", definition="Service médical", order=2),
        VocabularyValue(code="N", display="Unité de soins", definition="Unité de soins", order=3),
        VocabularyValue(code="R", display="Chambre", definition="Chambre", order=4),
        VocabularyValue(code="B", display="Lit", definition="Lit", order=5)
    ]
    pnt_loc_type.values = pnt_loc_values
    systems.append(pnt_loc_type)
    
    return systems

def create_movement_vocabularies() -> List[VocabularySystem]:
    """Crée les vocabulaires pour les mouvements"""
    systems = []
    
    # Types de mouvements IHE PAM France
    mvt_type = VocabularySystem(
        name="movement-type-fr",
        label="Type de mouvement",
        system_type=VocabularySystemType.LOCAL,
        is_user_defined=False,
        description="Types de mouvements selon IHE PAM France"
    )
    
    mvt_values = [
        VocabularyValue(code="E", display="Entrée", definition="Entrée dans l'établissement", order=1),
        VocabularyValue(code="S", display="Sortie", definition="Sortie de l'établissement", order=2),
        VocabularyValue(code="T", display="Transfert", definition="Transfert interne", order=3),
        VocabularyValue(code="P", display="Permission", definition="Permission", order=4),
        VocabularyValue(code="M", display="Mutation", definition="Mutation interne", order=5),
        VocabularyValue(code="R", display="Retour", definition="Retour de permission", order=6)
    ]
    mvt_type.values = mvt_values
    systems.append(mvt_type)
    
    return systems
