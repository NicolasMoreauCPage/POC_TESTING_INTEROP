"""
Parser HL7 v2.x pour extraction de données.

Ce module permet de parser des messages HL7 existants pour extraire
les données Patient, Dossier, Venue, Mouvement et créer des workflows.
"""

import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple


def parse_hl7_line(line: str) -> Tuple[str, List[str]]:
    """
    Parse une ligne HL7 en segment_type et fields.
    
    Args:
        line: Ligne HL7 (ex: "PID|1||12345||DOE^JOHN||19800101|M")
    
    Returns:
        (segment_type, fields) où fields[0] est le type de segment
    """
    if not line or line.startswith("\n"):
        return "", []
    
    # Supprimer caractères de contrôle
    line = line.replace("\r", "").replace("\n", "")
    
    # Split sur |
    fields = line.split("|")
    
    segment_type = fields[0] if fields else ""
    
    return segment_type, fields


def parse_hl7_datetime(value: str) -> Optional[datetime]:
    """
    Parse un timestamp HL7 (YYYYMMDDHHmmss ou YYYYMMDD).
    
    Args:
        value: Timestamp HL7
    
    Returns:
        datetime ou None
    """
    if not value:
        return None
    
    # Enlever les caractères non numériques
    value = re.sub(r'[^0-9]', '', value)
    
    try:
        if len(value) >= 14:
            return datetime.strptime(value[:14], "%Y%m%d%H%M%S")
        elif len(value) >= 8:
            return datetime.strptime(value[:8], "%Y%m%d")
    except ValueError:
        pass
    
    return None


def parse_hl7_identifier(value: str) -> Dict[str, str]:
    """
    Parse un identifiant HL7 (format: ID^^^AUTHORITY&OID&ISO^TYPE).
    
    Args:
        value: Identifiant HL7
    
    Returns:
        Dict avec id, authority, oid, type
    """
    parts = value.split("^")
    result = {
        "id": parts[0] if len(parts) > 0 else "",
        "authority": "",
        "oid": "",
        "type": ""
    }
    
    # Authority&OID&ISO dans parts[3]
    if len(parts) > 3:
        authority_parts = parts[3].split("&")
        if len(authority_parts) > 0:
            result["authority"] = authority_parts[0]
        if len(authority_parts) > 1:
            result["oid"] = authority_parts[1]
    
    # Type dans parts[4]
    if len(parts) > 4:
        result["type"] = parts[4]
    
    return result


def parse_hl7_name(value: str) -> Dict[str, str]:
    """
    Parse un nom HL7 (format: FAMILY^GIVEN^MIDDLE^SUFFIX^PREFIX).
    
    Args:
        value: Nom HL7
    
    Returns:
        Dict avec family, given, middle, suffix, prefix
    """
    parts = value.split("^")
    return {
        "family": parts[0] if len(parts) > 0 else "",
        "given": parts[1] if len(parts) > 1 else "",
        "middle": parts[2] if len(parts) > 2 else "",
        "suffix": parts[3] if len(parts) > 3 else "",
        "prefix": parts[4] if len(parts) > 4 else ""
    }


def parse_msh_segment(fields: List[str]) -> Dict[str, Any]:
    """Parse segment MSH."""
    return {
        "sending_application": fields[2] if len(fields) > 2 else "",
        "sending_facility": fields[3] if len(fields) > 3 else "",
        "receiving_application": fields[4] if len(fields) > 4 else "",
        "receiving_facility": fields[5] if len(fields) > 5 else "",
        "message_datetime": parse_hl7_datetime(fields[6]) if len(fields) > 6 else None,
        "message_type": fields[8].split("^")[0] if len(fields) > 8 else "",
        "trigger_event": fields[8].split("^")[1] if len(fields) > 8 and "^" in fields[8] else "",
        "message_control_id": fields[9] if len(fields) > 9 else "",
        "version": fields[11] if len(fields) > 11 else "2.5"
    }


def parse_pid_segment(fields: List[str]) -> Dict[str, Any]:
    """Parse segment PID (Patient Identification)."""
    # PID-3: Identifiants (peut être multiples, séparés par ~)
    identifiers = []
    if len(fields) > 3 and fields[3]:
        for id_str in fields[3].split("~"):
            identifiers.append(parse_hl7_identifier(id_str))
    
    # PID-5: Nom
    name = parse_hl7_name(fields[5]) if len(fields) > 5 else {}
    
    # PID-7: Date de naissance
    birth_date = parse_hl7_datetime(fields[7]) if len(fields) > 7 else None
    
    # PID-8: Genre
    gender = fields[8] if len(fields) > 8 else ""
    
    return {
        "identifiers": identifiers,
        "family": name.get("family", ""),
        "given": name.get("given", ""),
        "birth_date": birth_date,
        "gender": gender,
        "ssn": fields[19] if len(fields) > 19 else None
    }


def parse_pv1_segment(fields: List[str]) -> Dict[str, Any]:
    """Parse segment PV1 (Patient Visit)."""
    # PV1-2: Patient class (I/O/E)
    patient_class = fields[2] if len(fields) > 2 else "I"
    
    # PV1-3: Location (peut être complexe: PointOfCare^Room^Bed^Facility)
    location = ""
    if len(fields) > 3 and fields[3]:
        location_parts = fields[3].split("^")
        location = location_parts[0] if location_parts else ""
    
    # PV1-10: UF (peut être dans plusieurs champs selon implémentation)
    uf = ""
    if len(fields) > 10 and fields[10]:
        uf_parts = fields[10].split("^")
        uf = uf_parts[-1] if uf_parts else ""
    
    # PV1-19: Numéro de visite (NDA)
    visit_number = ""
    if len(fields) > 19 and fields[19]:
        visit_id = parse_hl7_identifier(fields[19])
        visit_number = visit_id.get("id", "")
    
    # PV1-44: Date/heure admission
    admit_datetime = parse_hl7_datetime(fields[44]) if len(fields) > 44 else None
    
    return {
        "patient_class": patient_class,
        "location": location,
        "uf_responsabilite": uf,
        "visit_number": visit_number,
        "admit_datetime": admit_datetime
    }


def parse_zbe_segment(fields: List[str]) -> Dict[str, Any]:
    """Parse segment ZBE (Mouvement patient - France)."""
    # ZBE-1: Identifiant mouvement (ID^AUTHORITY^OID^ISO)
    movement_id_parsed = parse_hl7_identifier(fields[1]) if len(fields) > 1 else {}
    
    # ZBE-2: Date/heure mouvement
    movement_datetime = parse_hl7_datetime(fields[2]) if len(fields) > 2 else None
    
    # ZBE-4: Type d'action
    action_type = fields[4] if len(fields) > 4 else "INSERT"
    
    # ZBE-7: UF responsable (format complexe: ^^^^^^UF^^^CODE_UF)
    uf = ""
    if len(fields) > 7 and fields[7]:
        uf_parts = fields[7].split("^")
        uf = uf_parts[-1] if uf_parts else ""
    
    return {
        "movement_id": movement_id_parsed.get("id", ""),
        "movement_datetime": movement_datetime,
        "action_type": action_type,
        "uf_responsabilite": uf
    }


def parse_hl7_message(message: str) -> Dict[str, Any]:
    """
    Parse un message HL7 complet.
    
    Args:
        message: Message HL7 brut (avec \\r ou \\n)
    
    Returns:
        Dict avec tous les segments parsés
    """
    # Normaliser les séparateurs de ligne
    message = message.replace("\r", "\n")
    lines = [line for line in message.split("\n") if line.strip()]
    
    result = {
        "MSH": None,
        "PID": None,
        "PV1": None,
        "ZBE": None,
        "raw": message
    }
    
    for line in lines:
        segment_type, fields = parse_hl7_line(line)
        
        if segment_type == "MSH":
            result["MSH"] = parse_msh_segment(fields)
        elif segment_type == "PID":
            result["PID"] = parse_pid_segment(fields)
        elif segment_type == "PV1":
            result["PV1"] = parse_pv1_segment(fields)
        elif segment_type == "ZBE":
            result["ZBE"] = parse_zbe_segment(fields)
    
    return result


def extract_scenario_metadata(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait les métadonnées de scénario depuis un message parsé.
    
    Args:
        parsed: Message HL7 parsé
    
    Returns:
        Dict avec name, scenario_type, category
    """
    msh = parsed.get("MSH", {})
    trigger_event = msh.get("trigger_event", "")
    
    # Déterminer le type de scénario
    scenario_type_map = {
        "A01": "ADMISSION",
        "A02": "TRANSFER",
        "A03": "DISCHARGE",
        "A04": "ADMISSION",  # Register patient
        "A08": "UPDATE",
        "A11": "CANCEL_ADMISSION",
        "A12": "CANCEL_TRANSFER",
        "A13": "CANCEL_DISCHARGE"
    }
    
    scenario_type = scenario_type_map.get(trigger_event, "OTHER")
    
    # Catégorie basée sur le type de patient
    pv1 = parsed.get("PV1", {})
    patient_class = pv1.get("patient_class", "I")
    
    category_map = {
        "E": "URGENCE",
        "I": "HOSPITALISATION",
        "O": "EXTERNE"
    }
    
    category = category_map.get(patient_class, "AUTRE")
    
    # Nom généré
    name = f"{scenario_type} - {category}"
    
    return {
        "name": name,
        "scenario_type": scenario_type,
        "category": category,
        "trigger_event": trigger_event
    }
