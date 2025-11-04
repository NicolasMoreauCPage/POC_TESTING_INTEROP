"""
Service de mapping entre vocabulaires IHE PAM et FHIR FR
"""
from typing import List
from sqlmodel import Session, select
from app.models_vocabulary import VocabularySystem, VocabularyValue, VocabularyMapping

def create_location_type_mappings(session: Session) -> List[VocabularyMapping]:
    """Crée les mappings entre types de lieux IHE PAM et FHIR FR"""
    mappings = []
    
    # Récupérer les systèmes
    ihe_system = session.exec(
        select(VocabularySystem).where(VocabularySystem.name == "service-type-fr")
    ).first()
    
    fhir_system = session.exec(
        select(VocabularySystem).where(VocabularySystem.name == "location-type-fr")
    ).first()
    
    if not ihe_system or not fhir_system:
        return []
        
    # Créer le dictionnaire de mapping
    map_pairs = [
        # (code IHE, code FHIR)
        ("UM", "SERV"),   # UF Médicale -> Service
        ("UC", "UF"),     # UF Soins -> UF
        ("UH", "UF"),     # UF Hébergement -> UF
        ("UA", "SERV"),   # UF Administrative -> Service
        ("UT", "SERV"),   # UF Technique -> Service
    ]
    
    # Créer les mappings
    for ihe_code, fhir_code in map_pairs:
        ihe_value = session.exec(
            select(VocabularyValue).where(
                VocabularyValue.code == ihe_code,
                VocabularyValue.system_id == ihe_system.id,
            )
        ).first()
        
        if ihe_value:
            mapping = VocabularyMapping(
                source_value=ihe_value,
                target_system=fhir_system,
                target_code=fhir_code,
                map_type="equivalent"
            )
            mappings.append(mapping)
    
    return mappings

def create_patient_class_mappings(session: Session) -> List[VocabularyMapping]:
    """Crée les mappings entre classes de patients IHE PAM et FHIR FR"""
    mappings = []
    
    # Récupérer les systèmes
    hl7_system = session.exec(
        select(VocabularySystem).where(VocabularySystem.name == "patient-class")
    ).first()
    
    encounter_system = session.exec(
        select(VocabularySystem).where(VocabularySystem.name == "encounter-class")
    ).first()
    
    if not hl7_system or not encounter_system:
        return []
        
    # Créer le dictionnaire de mapping
    map_pairs = [
        # (code HL7, code FHIR)
        ("I", "IMP"),     # Inpatient -> Hospitalisé
        ("O", "AMB"),     # Outpatient -> Ambulatoire
        ("E", "EMER"),    # Emergency -> Urgence
        ("P", "PRENC"),   # Preadmit -> Pre-encounter
        ("R", "AMB"),     # Recurring -> Ambulatoire
        ("B", "IMP"),     # Obstetrics -> Hospitalisé
    ]
    
    # Créer les mappings
    for hl7_code, fhir_code in map_pairs:
        hl7_value = session.exec(
            select(VocabularyValue).where(
                VocabularyValue.code == hl7_code,
                VocabularyValue.system_id == hl7_system.id,
            )
        ).first()
        
        if hl7_value:
            mapping = VocabularyMapping(
                source_value=hl7_value,
                target_system=encounter_system,
                target_code=fhir_code,
                map_type="equivalent"
            )
            mappings.append(mapping)
    
    return mappings

def create_admit_source_mappings(session: Session) -> List[VocabularyMapping]:
    """Crée les mappings entre types d'admission IHE PAM et FHIR FR"""
    mappings = []
    
    # Récupérer les systèmes
    hl7_system = session.exec(
        select(VocabularySystem).where(VocabularySystem.name == "admission-type")
    ).first()
    
    fhir_system = session.exec(
        select(VocabularySystem).where(VocabularySystem.name == "encounter-admission-fr")
    ).first()
    
    if not hl7_system or not fhir_system:
        return []
        
    # Créer le dictionnaire de mapping
    map_pairs = [
        # (code HL7, code FHIR)
        ("E", "RD"),      # Emergency -> Domicile (en urgence)
        ("A", "RD"),      # Accident -> Domicile
        ("L", "RD"),      # Labor -> Domicile
        ("R", "RT"),      # Routine -> Transfert
        ("U", "RD"),      # Urgent -> Domicile (en urgence)
    ]
    
    # Créer les mappings
    for hl7_code, fhir_code in map_pairs:
        hl7_value = session.exec(
            select(VocabularyValue).where(
                VocabularyValue.code == hl7_code,
                VocabularyValue.system_id == hl7_system.id,
            )
        ).first()
        
        if hl7_value:
            mapping = VocabularyMapping(
                source_value=hl7_value,
                target_system=fhir_system,
                target_code=fhir_code,
                map_type="equivalent"
            )
            mappings.append(mapping)
    
    return mappings

def create_discharge_disposition_mappings(session: Session) -> List[VocabularyMapping]:
    """Crée les mappings entre modes de sortie IHE PAM et FHIR FR"""
    mappings = []
    
    # Récupérer les systèmes
    hl7_system = session.exec(
        select(VocabularySystem).where(VocabularySystem.name == "discharge-disposition")
    ).first()
    
    fhir_system = session.exec(
        select(VocabularySystem).where(VocabularySystem.name == "encounter-discharge-fr")
    ).first()
    
    if not hl7_system or not fhir_system:
        return []
        
    # Créer le dictionnaire de mapping
    map_pairs = [
        # (code HL7, code FHIR)
        ("01", "F"),      # Discharged to home -> Retour domicile
        ("02", "T"),      # Transferred -> Transfert
        ("04", "DC"),     # Discharged to care facility -> Décès
        ("06", "AS"),     # Left against medical advice -> Autre sortie
        ("07", "F"),      # Left without notice -> Retour domicile
        ("20", "T"),      # Expired -> Transfert
        ("30", "T"),      # Still patient -> Transfert
    ]
    
    # Créer les mappings
    for hl7_code, fhir_code in map_pairs:
        hl7_value = session.exec(
            select(VocabularyValue).where(
                VocabularyValue.code == hl7_code,
                VocabularyValue.system_id == hl7_system.id,
            )
        ).first()
        
        if hl7_value:
            mapping = VocabularyMapping(
                source_value=hl7_value,
                target_system=fhir_system,
                target_code=fhir_code,
                map_type="equivalent"
            )
            mappings.append(mapping)
    
    return mappings

def create_encounter_priority_mappings(session: Session) -> List[VocabularyMapping]:
    """Crée les mappings entre priorités de venue IHE PAM et FHIR FR"""
    mappings = []
    
    # Récupérer les systèmes
    hl7_system = session.exec(
        select(VocabularySystem).where(VocabularySystem.name == "encounter-priority")
    ).first()
    
    fhir_system = session.exec(
        select(VocabularySystem).where(VocabularySystem.name == "encounter-priority-fr")
    ).first()
    
    if not hl7_system or not fhir_system:
        return []
        
    # Créer le dictionnaire de mapping
    map_pairs = [
        # (code HL7, code FHIR)
        ("EM", "U"),      # Emergency -> Urgence
        ("EL", "UR"),     # Elective -> Non urgent
        ("UR", "S"),      # Urgent -> Semi-urgent
        ("RO", "P"),      # Routine -> Programmé
    ]
    
    # Créer les mappings
    for hl7_code, fhir_code in map_pairs:
        hl7_value = session.exec(
            select(VocabularyValue).where(
                VocabularyValue.code == hl7_code,
                VocabularyValue.system_id == hl7_system.id,
            )
        ).first()
        
        if hl7_value:
            mapping = VocabularyMapping(
                source_value=hl7_value,
                target_system=fhir_system,
                target_code=fhir_code,
                map_type="equivalent"
            )
            mappings.append(mapping)
    
    return mappings

def init_vocabulary_mappings(session: Session) -> None:
    """Initialise tous les mappings entre vocabulaires"""
    
    all_mappings = []
    
    # Mappings type de lieu
    all_mappings.extend(create_location_type_mappings(session))
    
    # Mappings classe de patient
    all_mappings.extend(create_patient_class_mappings(session))
    
    # Mappings type d'admission
    all_mappings.extend(create_admit_source_mappings(session))
    
    # Mappings mode de sortie
    all_mappings.extend(create_discharge_disposition_mappings(session))
    
    # Mappings priorité de venue
    all_mappings.extend(create_encounter_priority_mappings(session))
    
    # Sauvegarder tous les mappings
    for mapping in all_mappings:
        session.add(mapping)
    
    session.commit()
