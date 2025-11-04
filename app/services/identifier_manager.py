"""
Services de gestion des identifiants et mappings FHIR/HL7
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from app.models_identifiers import Identifier, IdentifierType


def parse_hl7_cx_identifier(cx_value: str) -> Tuple[str, str, Optional[str], Optional[str]]:
    """
    Parse un identifiant au format HL7 CX (Component/Subcomponent Separator: ^)
    Format HL7 standard: ID^Check Digit^Check Digit Scheme^Assigning Authority^Identifier Type Code
    Pour simplifier, on extrait: value (pos 0), system (assigning authority à pos 3), type_code (pos 4)
    Retourne: (value, system, authority_oid, type_code)
    """
    parts = cx_value.split("^")
    value = parts[0] if len(parts) > 0 else ""
    # CX-4 = Assigning Authority (system)
    system = parts[3] if len(parts) > 3 else ""
    # CX-5 = Identifier Type Code
    type_code = parts[4] if len(parts) > 4 else None
    # Compatibility : authority_oid (not used currently)
    authority_oid = None
    
    return value, system, authority_oid, type_code


def create_identifier_from_hl7(
    cx_value: str,
    entity_type: str,
    entity_id: int
) -> Identifier:
    """
    Crée un identifiant à partir d'une valeur HL7 CX
    """
    value, namespace, auth_namespace, type_code = parse_hl7_cx_identifier(cx_value)
    
    # Déterminer le type d'identifiant — par défaut on considère PI (Patient Internal)
    id_type = None
    if type_code:
        try:
            id_type = IdentifierType(type_code)
        except ValueError:
            id_type = None

    if id_type is None:
        # Par souci de compatibilité, définir un type par défaut non-null
        id_type = IdentifierType.PI
    
    # Créer l'identifiant
    identifier = Identifier(
        value=value,
        system=namespace,
        type=id_type,
        status="active"
    )
    
    # Associer à l'entité
    if entity_type == "patient":
        identifier.patient_id = entity_id
    elif entity_type == "dossier":
        identifier.dossier_id = entity_id
    elif entity_type == "venue":
        identifier.venue_id = entity_id
    
    return identifier


def create_fhir_identifier(identifier: Identifier) -> Dict:
    """
    Convertit un identifiant en structure FHIR
    """
    fhir_id = {
        "use": "official",
        "system": identifier.system,
        "value": identifier.value
    }
    
    if identifier.type:
        fhir_id["type"] = {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                "code": identifier.type.value
            }]
        }
    
    return fhir_id


def create_identifier_from_fhir(fhir_identifier: Dict) -> Identifier:
    """
    Crée un identifiant à partir d'une structure FHIR
    """
    # Extraire le type si présent
    id_type = None
    if "type" in fhir_identifier and "coding" in fhir_identifier["type"]:
        for coding in fhir_identifier["type"]["coding"]:
            if coding["system"] == "http://terminology.hl7.org/CodeSystem/v2-0203":
                try:
                    id_type = IdentifierType(coding["code"])
                    break
                except ValueError:
                    pass
    
    return Identifier(
        value=fhir_identifier["value"],
        system=fhir_identifier.get("system", ""),
        type=id_type,
        status="active"
    )


def get_main_identifier(identifiers: List[Identifier], id_type: Optional[IdentifierType] = None) -> Optional[Identifier]:
    """
    Récupère l'identifiant principal d'une liste selon le type
    """
    if not identifiers:
        return None
        
    # Si un type est spécifié, chercher d'abord ce type
    if id_type:
        for identifier in identifiers:
            if identifier.type == id_type and identifier.status == "active":
                return identifier
    
    # Sinon prendre le premier actif
    for identifier in identifiers:
        if identifier.status == "active":
            return identifier
            
    return identifiers[0]  # Si aucun actif, prendre le premier


def merge_identifiers(
    existing: List[Identifier],
    new: List[Identifier],
    keep_inactive: bool = True
) -> List[Identifier]:
    """
    Fusionne deux listes d'identifiants en gérant les conflits
    """
    result = []
    seen = set()
    
    # Ajouter les nouveaux identifiants
    for identifier in new:
        key = (identifier.system, identifier.value)
        seen.add(key)
        result.append(identifier)
    
    # Ajouter ou mettre à jour les existants
    for identifier in existing:
        key = (identifier.system, identifier.value)
        if key not in seen:
            if identifier.status == "active" or keep_inactive:
                result.append(identifier)
                seen.add(key)
    
    return result