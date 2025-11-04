"""
Service de chargement des vocabulaires standard (HL7v2 / FHIR)
"""
from typing import List
from app.models_vocabulary import VocabularySystem, VocabularyValue, VocabularySystemType


def create_ihe_pam_vocabularies() -> List[VocabularySystem]:
    """Crée les systèmes de vocabulaire issus des tables HL7v2 utilisées par IHE PAM."""
    systems: List[VocabularySystem] = []
    
    # Table 0004 - Patient Class
    patient_class = VocabularySystem(
        name="patient-class",
        label="Type de patient (HL7v2)",
        oid="2.16.840.1.113883.12.4",
        system_type=VocabularySystemType.HL7V2,
        is_user_defined=False,
        description="Table HL7 0004 - Patient Class"
    )
    patient_class.values = [
        VocabularyValue(code="E", display="Emergency", definition="Patient urgence", order=1),
        VocabularyValue(code="I", display="Inpatient", definition="Patient hospitalisé", order=2),
        VocabularyValue(code="O", display="Outpatient", definition="Patient externe", order=3),
        VocabularyValue(code="P", display="Preadmit", definition="Pré-admission", order=4),
        VocabularyValue(code="R", display="Recurring patient", definition="Patient récurrent", order=5),
        VocabularyValue(code="B", display="Obstetrics", definition="Obstétrique", order=6),
        VocabularyValue(code="C", display="Commercial Account", definition="Compte commercial", order=7),
        VocabularyValue(code="N", display="Not Applicable", definition="Non applicable", order=8),
        VocabularyValue(code="U", display="Unknown", definition="Inconnu", order=9),
    ]
    systems.append(patient_class)

    # Table 0007 - Admission Type
    admission_type = VocabularySystem(
        name="admission-type",
        label="Type d'admission (HL7v2)",
        oid="2.16.840.1.113883.12.7",
        system_type=VocabularySystemType.HL7V2,
        is_user_defined=False,
        description="Table HL7 0007 - Admission Type"
    )
    admission_type.values = [
        VocabularyValue(code="A", display="Accident", definition="Admission suite à un accident", order=1),
        VocabularyValue(code="C", display="Elective", definition="Admission programmée", order=2),
        VocabularyValue(code="E", display="Emergency", definition="Admission en urgence", order=3),
        VocabularyValue(code="L", display="Labor and Delivery", definition="Admission pour accouchement", order=4),
        VocabularyValue(code="N", display="Newborn", definition="Nouveau-né", order=5),
        VocabularyValue(code="R", display="Routine", definition="Admission de routine", order=6),
        VocabularyValue(code="U", display="Urgent", definition="Admission urgente", order=7),
    ]
    systems.append(admission_type)

    # Table 0027 - Priority
    encounter_priority = VocabularySystem(
        name="encounter-priority",
        label="Priorité de venue (HL7v2)",
        oid="2.16.840.1.113883.12.27",
        system_type=VocabularySystemType.HL7V2,
        is_user_defined=False,
        description="Table HL7 0027 - Priority"
    )
    encounter_priority.values = [
        VocabularyValue(code="EM", display="Emergency", definition="Prise en charge immédiate", order=1),
        VocabularyValue(code="EL", display="Elective", definition="Priorité programmée / élective", order=2),
        VocabularyValue(code="UR", display="Urgent", definition="Urgent", order=3),
        VocabularyValue(code="RO", display="Routine", definition="Suivi programmé", order=4),
    ]
    systems.append(encounter_priority)

    # Table 0112 - Discharge Disposition
    discharge_disposition = VocabularySystem(
        name="discharge-disposition",
        label="Disposition de sortie (HL7v2)",
        oid="2.16.840.1.113883.12.112",
        system_type=VocabularySystemType.HL7V2,
        is_user_defined=False,
        description="Table HL7 0112 - Discharge Disposition"
    )
    discharge_disposition.values = [
        VocabularyValue(code="01", display="Home", definition="Retour au domicile", order=1),
        VocabularyValue(code="02", display="Short-term hospital", definition="Transfert vers court séjour", order=2),
        VocabularyValue(code="04", display="Intermediate care", definition="Transfert vers structure médico-sociale", order=3),
        VocabularyValue(code="06", display="Left against advice", definition="Sortie contre avis médical", order=4),
        VocabularyValue(code="07", display="Left without notice", definition="Départ sans prévenir", order=5),
        VocabularyValue(code="20", display="Expired", definition="Patient décédé", order=6),
        VocabularyValue(code="30", display="Still patient", definition="Patient toujours hospitalisé", order=7),
    ]
    systems.append(discharge_disposition)

    # Table 0092 - Re-Admission Indicator
    readmission = VocabularySystem(
        name="readmission-indicator",
        label="Indicateur de réadmission (HL7v2)",
        oid="2.16.840.1.113883.12.92",
        system_type=VocabularySystemType.HL7V2,
        is_user_defined=False,
        description="Table HL7 0092 - Re-Admission Indicator"
    )
    readmission.values = [
        VocabularyValue(code="R", display="Réadmission", definition="Il s'agit d'une réadmission", order=1),
        VocabularyValue(code="N", display="Pas une réadmission", definition="Il ne s'agit pas d'une réadmission", order=2),
    ]
    systems.append(readmission)
    
    return systems


def create_fhir_encounter_vocabularies() -> List[VocabularySystem]:
    """Crée les vocabulaires FHIR internationaux nécessaires aux venues."""
    systems: List[VocabularySystem] = []
    
    # Encounter.class (http://terminology.hl7.org/CodeSystem/v3-ActCode)
    encounter_class = VocabularySystem(
        name="encounter-class",
        label="Type de venue (FHIR)",
        uri="http://terminology.hl7.org/CodeSystem/v3-ActCode",
        system_type=VocabularySystemType.FHIR,
        is_user_defined=False,
        description="Classification des venues selon FHIR (ActEncounterCode)"
    )
    encounter_class.values = [
        VocabularyValue(code="IMP", display="Hospitalisation", definition="Séjour en hospitalisation complète", order=1),
        VocabularyValue(code="AMB", display="Ambulatoire", definition="Consultation ou venue ambulatoire", order=2),
        VocabularyValue(code="EMER", display="Urgence", definition="Passage aux urgences", order=3),
        VocabularyValue(code="ACUTE", display="Séjour court", definition="Hospitalisation de courte durée", order=4),
        VocabularyValue(code="NONAC", display="Séjour long", definition="Hospitalisation de longue durée", order=5),
        VocabularyValue(code="HH", display="Domicile", definition="Prise en charge à domicile", order=6),
        VocabularyValue(code="FLD", display="Terrain", definition="Intervention sur le terrain", order=7),
        VocabularyValue(code="SS", display="Séjour partiel", definition="Hospitalisation de jour / nuit", order=8),
        VocabularyValue(code="VR", display="Virtuelle", definition="Téléconsultation ou visite virtuelle", order=9),
    ]
    systems.append(encounter_class)
    
    return systems

