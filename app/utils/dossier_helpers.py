from app.models import DossierType, Dossier

# Mapping entre DossierType et encounter_class HL7/FHIR
ENCOUNTER_CLASS_MAPPING = {
    DossierType.HOSPITALISE: "IMP",  # Inpatient encounter
    DossierType.EXTERNE: "AMB",      # Ambulatory encounter
    DossierType.URGENCE: "EMER"      # Emergency encounter
}

def sync_dossier_class(dossier: Dossier) -> None:
    """
    Synchronise le type de dossier avec la classe de rencontre (encounter_class).
    Cette fonction doit être appelée à chaque fois que le type de dossier change.
    """
    dossier.encounter_class = ENCOUNTER_CLASS_MAPPING[dossier.dossier_type]