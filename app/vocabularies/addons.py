"""
Initialisation des vocabulaires additionnels (workflow et structure)
"""
from sqlmodel import Session
from app.models_vocabulary import VocabularySystem, VocabularyValue, VocabularyMapping, VocabularySystemType

def init_workflow_vocabularies(session: Session):
    """Initialise les vocabulaires liés au workflow"""
    
    # --- Location Status (FHIR) ---
    status_fhir = VocabularySystem(
        name="location-status",
        label="Statut d'emplacement (FHIR)",
        system_type=VocabularySystemType.FHIR,
        uri="http://hl7.org/fhir/location-status",
        is_user_defined=False
    )
    session.add(status_fhir)
    session.add_all([
        VocabularyValue(system=status_fhir, code="active", display="Actif"),
        VocabularyValue(system=status_fhir, code="suspended", display="Suspendu"),
        VocabularyValue(system=status_fhir, code="inactive", display="Inactif")
    ])
    
    # --- Location Physical Type (FHIR) ---
    physical_type = VocabularySystem(
        name="location-physical-type",
        label="Type d'emplacement (FHIR)",
        system_type=VocabularySystemType.FHIR,
        uri="http://terminology.hl7.org/CodeSystem/location-physical-type",
        is_user_defined=False
    )
    session.add(physical_type)
    session.add_all([
        VocabularyValue(system=physical_type, code="bu", display="Bâtiment"),
        VocabularyValue(system=physical_type, code="wi", display="Aile"),
        VocabularyValue(system=physical_type, code="wa", display="Service"),
        VocabularyValue(system=physical_type, code="ro", display="Chambre"),
        VocabularyValue(system=physical_type, code="bd", display="Lit"),
        VocabularyValue(system=physical_type, code="area", display="Zone"),
        VocabularyValue(system=physical_type, code="lvl", display="Niveau")
    ])
    
    # --- Movement Type (Local) ---
    movement_type = VocabularySystem(
        name="movement-type",
        label="Type de mouvement",
        system_type=VocabularySystemType.LOCAL,
        is_user_defined=True
    )
    session.add(movement_type)
    session.add_all([
        VocabularyValue(system=movement_type, code="ADM", display="Admission"),
        VocabularyValue(system=movement_type, code="TRF", display="Transfert"),
        VocabularyValue(system=movement_type, code="TMP", display="Permission"),
        VocabularyValue(system=movement_type, code="DIS", display="Sortie")
    ])
    
    # --- Movement Status (Local) ---
    movement_status = VocabularySystem(
        name="movement-status",
        label="Statut du mouvement",
        system_type=VocabularySystemType.LOCAL,
        is_user_defined=True
    )
    session.add(movement_status)
    session.add_all([
        VocabularyValue(system=movement_status, code="PLAN", display="Planifié"),
        VocabularyValue(system=movement_status, code="PROG", display="En cours"),
        VocabularyValue(system=movement_status, code="COMP", display="Terminé"),
        VocabularyValue(system=movement_status, code="CANC", display="Annulé")
    ])
    
    # --- Movement Reason (Local) ---
    movement_reason = VocabularySystem(
        name="movement-reason",
        label="Raison du mouvement",
        system_type=VocabularySystemType.LOCAL,
        is_user_defined=True
    )
    session.add(movement_reason)
    session.add_all([
        VocabularyValue(system=movement_reason, code="MED", display="Médical"),
        VocabularyValue(system=movement_reason, code="ADM", display="Administratif"),
        VocabularyValue(system=movement_reason, code="PSY", display="Psychiatrique"),
        VocabularyValue(system=movement_reason, code="SOC", display="Social")
    ])
    
    session.commit()

def init_structure_vocabularies(session: Session):
    """Initialise les vocabulaires liés à la structure"""
    
    # --- Service Type (FHIR) ---
    service_type = VocabularySystem(
        name="service-type",
        label="Type de service",
        system_type=VocabularySystemType.FHIR,
        uri="http://terminology.hl7.org/CodeSystem/service-type",
        is_user_defined=False
    )
    session.add(service_type)
    session.add_all([
        VocabularyValue(system=service_type, code="EMR", display="Urgences"),
        VocabularyValue(system=service_type, code="SUR", display="Chirurgie"),
        VocabularyValue(system=service_type, code="INT", display="Médecine interne"),
        VocabularyValue(system=service_type, code="PSY", display="Psychiatrie"),
        VocabularyValue(system=service_type, code="OBS", display="Obstétrique"),
        VocabularyValue(system=service_type, code="PED", display="Pédiatrie")
    ])
    
    # --- Location Mode (FHIR) ---
    location_mode = VocabularySystem(
        name="location-mode",
        label="Mode d'occupation",
        system_type=VocabularySystemType.FHIR,
        uri="http://hl7.org/fhir/location-mode",
        is_user_defined=False
    )
    session.add(location_mode)
    session.add_all([
        VocabularyValue(system=location_mode, code="instance", display="Instance spécifique"),
        VocabularyValue(system=location_mode, code="kind", display="Type générique")
    ])
    
    # --- Room Type (Local) ---
    room_type = VocabularySystem(
        name="room-type",
        label="Type de chambre",
        system_type=VocabularySystemType.LOCAL,
        is_user_defined=True
    )
    session.add(room_type)
    session.add_all([
        VocabularyValue(system=room_type, code="SINGLE", display="Chambre simple"),
        VocabularyValue(system=room_type, code="DOUBLE", display="Chambre double"),
        VocabularyValue(system=room_type, code="WARD", display="Dortoir"),
        VocabularyValue(system=room_type, code="ISO", display="Chambre d'isolement"),
        VocabularyValue(system=room_type, code="VIP", display="Chambre VIP")
    ])
    
    session.commit()

def init_additional_vocabularies(session: Session):
    """Initialise tous les vocabulaires additionnels"""
    init_workflow_vocabularies(session)
    init_structure_vocabularies(session)
