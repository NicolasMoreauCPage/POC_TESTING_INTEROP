"""
Utilitaires de validation et gestion des identifiants patients.
"""
from typing import Optional
from sqlmodel import Session, select
from app.models_identifiers import Identifier, IdentifierType


class DuplicateIdentifierError(ValueError):
    """Exception levée quand un identifiant existe déjà dans le même système."""
    pass


def validate_unique_identifier(
    session: Session,
    value: str,
    system: str,
    oid: str,
    patient_id: Optional[int] = None,
    raise_on_duplicate: bool = True
) -> bool:
    """
    Vérifie qu'un identifiant est unique dans son système (system + oid).
    
    Règle: Dans un même établissement juridique (system + oid), un identifiant
    externe ne peut être utilisé que par un seul patient.
    
    Args:
        session: Session DB
        value: Valeur de l'identifiant (ex: "12345")
        system: Système d'identification (ex: "LABO_X", "HOSP_A")
        oid: OID du système (ex: "1.2.250.1.213.1.1.9")
        patient_id: ID du patient actuel (pour ignorer lors d'update)
        raise_on_duplicate: Si True, lève DuplicateIdentifierError, sinon retourne False
    
    Returns:
        True si unique, False si doublon (seulement si raise_on_duplicate=False)
    
    Raises:
        DuplicateIdentifierError: Si l'identifiant existe déjà (et raise_on_duplicate=True)
    
    Examples:
        >>> # Patient 1 a IPP "123" dans système "HOSP_A"
        >>> validate_unique_identifier(session, "123", "HOSP_A", "1.2.3")  # OK
        
        >>> # Patient 2 essaie d'avoir le même IPP dans le même système
        >>> validate_unique_identifier(session, "123", "HOSP_A", "1.2.3")  # ❌ DuplicateIdentifierError
        
        >>> # Patient 2 peut avoir IPP "123" dans un AUTRE système
        >>> validate_unique_identifier(session, "123", "HOSP_B", "1.2.4")  # ✅ OK
    """
    # Chercher identifiant existant avec même value + system + oid
    query = (
        select(Identifier)
        .where(Identifier.value == value)
        .where(Identifier.system == system)
        .where(Identifier.oid == oid)
        .where(Identifier.status == "active")
    )
    
    # Si on est en train de modifier un patient, exclure ses propres identifiants
    if patient_id:
        query = query.where(Identifier.patient_id != patient_id)
    
    existing = session.exec(query).first()
    
    if existing:
        if raise_on_duplicate:
            raise DuplicateIdentifierError(
                f"Identifiant '{value}' déjà utilisé dans le système '{system}' (OID: {oid}) "
                f"par le patient #{existing.patient_id}"
            )
        return False
    
    return True


def add_or_update_identifier(
    session: Session,
    patient_id: int,
    value: str,
    system: str,
    oid: str,
    identifier_type: IdentifierType,
    validate_unique: bool = True
) -> Identifier:
    """
    Ajoute ou met à jour un identifiant pour un patient.
    
    Si l'identifiant existe déjà pour ce patient, il est mis à jour.
    Sinon, un nouvel identifiant est créé.
    
    Args:
        session: Session DB
        patient_id: ID du patient
        value: Valeur de l'identifiant
        system: Système d'identification
        oid: OID du système
        identifier_type: Type d'identifiant (IPP, NDA, etc.)
        validate_unique: Si True, vérifie l'unicité avant création
    
    Returns:
        L'identifiant créé ou mis à jour
    
    Raises:
        DuplicateIdentifierError: Si validate_unique=True et doublon détecté
    """
    # Vérifier unicité si demandé
    if validate_unique:
        validate_unique_identifier(session, value, system, oid, patient_id)
    
    # Chercher identifiant existant pour ce patient
    existing = session.exec(
        select(Identifier)
        .where(Identifier.patient_id == patient_id)
        .where(Identifier.value == value)
        .where(Identifier.system == system)
        .where(Identifier.oid == oid)
    ).first()
    
    if existing:
        # Mettre à jour
        existing.type = identifier_type
        existing.status = "active"
        from datetime import datetime
        existing.last_updated = datetime.utcnow()
        session.add(existing)
        return existing
    else:
        # Créer nouveau
        identifier = Identifier(
            value=value,
            type=identifier_type,
            system=system,
            oid=oid,
            status="active",
            patient_id=patient_id
        )
        session.add(identifier)
        return identifier


def validate_identity_reliability_code(code: str) -> bool:
    """
    Valide un code PID-32 Identity Reliability Code (HL7 Table 0445).
    
    Codes valides (IHE PAM France):
    - VIDE: Non renseigné / Déclaratif
    - PROV: Provisoire (en attente validation)
    - VALI: Validé (pièce d'identité contrôlée)
    - DOUTE: Identité douteuse (incohérences)
    - FICTI: Identité fictive (X, Anonyme, Inconnu)
    
    Args:
        code: Code à valider
    
    Returns:
        True si valide, False sinon
    """
    valid_codes = ["", "VIDE", "PROV", "VALI", "DOUTE", "FICTI"]
    return code in valid_codes


def get_identity_reliability_label(code: str) -> str:
    """
    Retourne le label français pour un code PID-32.
    
    Args:
        code: Code PID-32
    
    Returns:
        Label en français
    """
    labels = {
        "": "Non renseigné",
        "VIDE": "Non renseigné / Déclaratif",
        "PROV": "Provisoire (en attente validation)",
        "VALI": "Validé (pièce d'identité contrôlée)",
        "DOUTE": "Identité douteuse",
        "FICTI": "Identité fictive (X, Anonyme, Inconnu)"
    }
    return labels.get(code, f"Code inconnu: {code}")
