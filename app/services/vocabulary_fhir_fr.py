"""
Service de chargement des vocabulaires FHIR Français
Basé sur https://interop-sante.github.io/hl7.fhir.fr.structure/
"""
from typing import List
from app.models_vocabulary import VocabularySystem, VocabularyValue, VocabularySystemType

def create_fr_practitioner_specialty() -> List[VocabularySystem]:
    """Crée les vocabulaires pour les spécialités FHIR FR"""
    systems = []
    
    # FHIR FR Practitioner Specialty
    specialty = VocabularySystem(
        name="practitioner-specialty-fr",
        label="Spécialité ou Rôle PS (FHIR FR)",
        uri="https://mos.esante.gouv.fr/NOS/TRE_R38-SpecialiteOrdinale/FHIR/TRE-R38-SpecialiteOrdinale",
        system_type=VocabularySystemType.FHIR,
        is_user_defined=False,
        description="Codes des spécialités ordinales - NOS"
    )
    
    specialty_values = [
        VocabularyValue(code="SM01", display="Médecine générale", definition="Médecin généraliste", order=1),
        VocabularyValue(code="SM02", display="Anesthésie-réanimation", definition="Anesthésiste-réanimateur", order=2),
        VocabularyValue(code="SM03", display="Cardiologie", definition="Cardiologue", order=3),
        VocabularyValue(code="SM04", display="Chirurgie générale", definition="Chirurgien", order=4),
        VocabularyValue(code="SM24", display="Médecine d'urgence", definition="Médecin urgentiste", order=5),
        VocabularyValue(code="SM26", display="Pédiatrie", definition="Pédiatre", order=6),
        VocabularyValue(code="SM54", display="Psychiatrie", definition="Psychiatre", order=7)
    ]
    specialty.values = specialty_values
    systems.append(specialty)
    
    return systems

def create_fr_organization_type() -> List[VocabularySystem]:
    """Crée les vocabulaires pour les types d'organisations FHIR FR"""
    systems = []
    
    # FHIR FR Organization Type
    org_type = VocabularySystem(
        name="organization-type-fr",
        label="Type de structure (FHIR FR)",
        uri="https://mos.esante.gouv.fr/NOS/TRE_R02-SecteurActivite/FHIR/TRE-R02-SecteurActivite",
        system_type=VocabularySystemType.FHIR,
        is_user_defined=False,
        description="Types de structures de santé - NOS"
    )
    
    org_values = [
        VocabularyValue(code="SA01", display="Centre Hospitalier", definition="Établissement public de santé", order=1),
        VocabularyValue(code="SA02", display="Clinique", definition="Établissement privé de santé", order=2),
        VocabularyValue(code="SA03", display="EHPAD", definition="Établissement d'hébergement pour personnes âgées dépendantes", order=3),
        VocabularyValue(code="SA04", display="Cabinet libéral", definition="Cabinet de praticien libéral", order=4),
        VocabularyValue(code="SA05", display="Maison de santé", definition="Maison de santé pluriprofessionnelle", order=5),
        VocabularyValue(code="SA07", display="Centre de santé", definition="Centre de santé", order=6),
        VocabularyValue(code="SA08", display="HAD", definition="Hospitalisation à domicile", order=7)
    ]
    org_type.values = org_values
    systems.append(org_type)
    
    return systems

def create_fr_location_type() -> List[VocabularySystem]:
    """Crée les vocabulaires pour les types de lieux FHIR FR"""
    systems = []
    
    # FHIR FR Location Type
    loc_type = VocabularySystem(
        name="location-type-fr",
        label="Type d'emplacement (FHIR FR)",
        uri="https://mos.esante.gouv.fr/NOS/TRE_R67-TypeLieu/FHIR/TRE-R67-TypeLieu",
        system_type=VocabularySystemType.FHIR,
        is_user_defined=False,
        description="Types de lieux de santé - NOS"
    )
    
    loc_values = [
        VocabularyValue(code="SITE", display="Site", definition="Site géographique", order=1),
        VocabularyValue(code="BAT", display="Bâtiment", definition="Bâtiment", order=2),
        VocabularyValue(code="ETAGE", display="Étage", definition="Étage", order=3),
        VocabularyValue(code="SERV", display="Service", definition="Service médical", order=4),
        VocabularyValue(code="UF", display="Unité Fonctionnelle", definition="Unité fonctionnelle", order=5),
        VocabularyValue(code="CHAMBRE", display="Chambre", definition="Chambre d'hospitalisation", order=6),
        VocabularyValue(code="LIT", display="Lit", definition="Lit d'hospitalisation", order=7)
    ]
    loc_type.values = loc_values
    systems.append(loc_type)
    
    # FHIR FR Location Physical Type
    phys_type = VocabularySystem(
        name="location-physical-type-fr",
        label="Type physique de lieu (FHIR FR)",
        uri="https://mos.esante.gouv.fr/NOS/TRE_R68-TypeEmplacement/FHIR/TRE-R68-TypeEmplacement",
        system_type=VocabularySystemType.FHIR,
        is_user_defined=False,
        description="Types physiques de lieux - NOS"
    )
    
    phys_values = [
        VocabularyValue(code="bu", display="Bâtiment", definition="Structure physique ou bâtiment", order=1),
        VocabularyValue(code="wi", display="Aile", definition="Aile d'un bâtiment", order=2),
        VocabularyValue(code="wa", display="Service", definition="Zone/Service dans un bâtiment", order=3),
        VocabularyValue(code="ro", display="Chambre", definition="Chambre", order=4),
        VocabularyValue(code="bd", display="Lit", definition="Lit", order=5),
        VocabularyValue(code="area", display="Zone", definition="Zone ou région", order=6),
        VocabularyValue(code="lvl", display="Niveau", definition="Niveau ou étage", order=7)
    ]
    phys_type.values = phys_values
    systems.append(phys_type)
    
    return systems

def create_fr_patient_contact_role() -> List[VocabularySystem]:
    """Crée les vocabulaires pour les rôles des contacts patients FHIR FR"""
    systems = []
    
    # FHIR FR Patient Contact Role
    contact_role = VocabularySystem(
        name="patient-contact-role-fr",
        label="Rôle du contact (FHIR FR)",
        uri="https://mos.esante.gouv.fr/NOS/TRE_R260-TypeLienPatient/FHIR/TRE-R260-TypeLienPatient",
        system_type=VocabularySystemType.FHIR,
        is_user_defined=False,
        description="Types de liens avec le patient - NOS"
    )
    
    role_values = [
        VocabularyValue(code="FAMMEMB", display="Membre de la famille", definition="Membre de la famille", order=1),
        VocabularyValue(code="CHILD", display="Enfant", definition="Enfant du patient", order=2),
        VocabularyValue(code="PARENT", display="Parent", definition="Parent du patient", order=3),
        VocabularyValue(code="SPOUSE", display="Conjoint", definition="Conjoint du patient", order=4),
        VocabularyValue(code="GUARD", display="Tuteur", definition="Tuteur légal", order=5),
        VocabularyValue(code="EMERGENCY", display="Contact d'urgence", definition="Personne à prévenir en cas d'urgence", order=6),
        VocabularyValue(code="CAREGIVER", display="Aidant", definition="Aidant du patient", order=7),
        VocabularyValue(code="PRN", display="Personne de confiance", definition="Personne de confiance", order=8)
    ]
    contact_role.values = role_values
    systems.append(contact_role)
    
    return systems

def create_fr_encounter_hospitalization() -> List[VocabularySystem]:
    """Crée les vocabulaires pour les modes d'hospitalisation FHIR FR"""
    systems = []
    
    # FHIR FR Admission Type (Mode d'entrée)
    admission = VocabularySystem(
        name="encounter-admission-fr",
        label="Mode d'entrée (FHIR FR)",
        uri="https://mos.esante.gouv.fr/NOS/TRE_R306-TypeAdmission/FHIR/TRE-R306-TypeAdmission",
        system_type=VocabularySystemType.FHIR,
        is_user_defined=False,
        description="Types d'admission - NOS"
    )
    
    admission_values = [
        VocabularyValue(code="RM", display="Mutation", definition="Mouvement en provenance d'une autre unité médicale", order=1),
        VocabularyValue(code="RT", display="Transfert", definition="Transfert depuis un autre établissement", order=2),
        VocabularyValue(code="RD", display="Domicile", definition="En provenance du domicile", order=3),
        VocabularyValue(code="RO", display="Autre", definition="Autre mode d'entrée", order=4)
    ]
    admission.values = admission_values
    systems.append(admission)
    
    # FHIR FR Discharge Type (Mode de sortie)
    discharge = VocabularySystem(
        name="encounter-discharge-fr",
        label="Mode de sortie (FHIR FR)",
        uri="https://mos.esante.gouv.fr/NOS/TRE_R307-TypeSortie/FHIR/TRE-R307-TypeSortie",
        system_type=VocabularySystemType.FHIR,
        is_user_defined=False,
        description="Types de sortie - NOS"
    )
    
    discharge_values = [
        VocabularyValue(code="SM", display="Mutation", definition="Vers une autre unité médicale", order=1),
        VocabularyValue(code="ST", display="Transfert", definition="Vers un autre établissement", order=2),
        VocabularyValue(code="SD", display="Domicile", definition="Retour au domicile", order=3),
        VocabularyValue(code="DC", display="Décès", definition="Patient décédé", order=4),
        VocabularyValue(code="SO", display="Autre", definition="Autre mode de sortie", order=5)
    ]
    discharge.values = discharge_values
    systems.append(discharge)
    
    return systems

def create_fr_encounter_priority() -> List[VocabularySystem]:
    """Crée le vocabulaire pour la priorité des venues (profil français)."""
    systems: List[VocabularySystem] = []
    
    priority = VocabularySystem(
        name="encounter-priority-fr",
        label="Priorité de venue (FHIR FR)",
        uri="https://mos.esante.gouv.fr/NOS/TRE_R38-PrioriteVenue/FHIR/TRE-R38-PrioriteVenue",
        system_type=VocabularySystemType.FHIR,
        is_user_defined=False,
        description="Priorités de venue recommandées pour les dossiers patients"
    )
    
    priority.values = [
        VocabularyValue(code="U", display="Urgence vitale", definition="Prise en charge immédiate", order=1),
        VocabularyValue(code="UR", display="Urgent", definition="Prise en charge à très court terme", order=2),
        VocabularyValue(code="S", display="Semi-urgent", definition="Prise en charge rapide", order=3),
        VocabularyValue(code="P", display="Programmé", definition="Venue planifiée", order=4),
    ]
    systems.append(priority)
    
    return systems
