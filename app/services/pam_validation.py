"""IHE PAM HL7v2 validator (règles IHE PAM + HL7 v2.5).

Valide les messages ADT contre:
1. Structures HAPI définies dans Doc/HAPI/hapi/custom/message/
2. Règles HL7 v2.5 standard (Doc/HL7v2.5/CH02A.pdf, Ch03.pdf)

Hiérarchie de validation (ordre de prédominance):
1. Règles IHE PAM (profil d'intégration)
2. Structures HAPI/CPage (extensions locales)
3. Règles HL7 v2.5 base (standard)

Contrôles IHE PAM & HAPI:
- Segments obligatoires: MSH, EVN, PID (toujours requis)
- PV1 requis pour les événements de venue/séjour (A01, A03, A04, A05, A06, A08, A11, A12, A13, A21, A22, A23, A52, A53)
- PV1 optionnel/toléré pour les événements d'identité (A28, A31, A40, A47)
- Segments optionnels: PD1, PV2, NK1, SFT, DB1, OBX, AL1, DG1, DRG, GT1, ACC, UB1, UB2, PDA
- Segments Z spécifiques (ZBE, ZFP, ZFV, ZFM, ZFA, ZFD, ZFU, ZPA, ZPV, ZFT, ZFI, ZFS)

Contrôles HL7 v2.5 base:
- MSH-1 (Field Separator) = "|"
- MSH-2 (Encoding Characters) = "^~\\&" (défaut)
- MSH-9 (Message Type) format correct: type^trigger[^structure]
- MSH-10 (Message Control ID) non vide
- MSH-11 (Processing ID) valeur valide (P, D, T)
- MSH-12 (Version ID) présent
- EVN-1 cohérence avec MSH-9
- PID-3 non vide (identifiant patient obligatoire)
- PID-5 présent (nom patient)
- Cohérence des dates/heures (format HL7: YYYYMMDD[HHMM[SS]])

Note: Les règles détaillées HL7 v2.5 (CH02A, CH03) peuvent être consultées
dans Doc/HL7v2.5/ pour référence. Ce validateur implémente les contrôles
essentiels; pour une conformité complète HL7 v2.5, utiliser un parseur
certifié (ex. HAPI avec validation stricte).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Set

from app.services.mllp import parse_msh_fields


# Mapping des segments attendus par trigger (basé sur les structures HAPI)
# Format: trigger -> {"required": [segments], "optional": [segments]}
# "required" = segment obligatoire (true, false dans HAPI)
# "optional" = segment optionnel (false, false ou false, true dans HAPI)
SEGMENT_RULES = {
    "A01": {
        "required": ["MSH", "EVN", "PID", "PV1"],
        "optional": ["SFT", "PD1", "NK1", "PV2", "ZBE", "ZFA", "ZFP", "ZFV", "ZFM", "ZFD",
                     "DB1", "OBX", "ACC", "AL1", "DG1", "DRG", "GT1", "UB1", "UB2", "PDA",
                     "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
    },
    "A03": {
        "required": ["MSH", "EVN", "PID", "PV1"],
        "optional": ["SFT", "PD1", "NK1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM",
                     "DB1", "AL1", "DG1", "DRG", "OBX", "GT1", "ACC", "PDA",
                     "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
    },
    "A04": {
        "required": ["MSH", "EVN", "PID", "PV1"],
        "optional": ["SFT", "PD1", "NK1", "PV2", "ZBE", "ZFA", "ZFP", "ZFV", "ZFM", "ZFD",
                     "DB1", "OBX", "ACC", "AL1", "DG1", "DRG", "GT1", "UB1", "UB2", "PDA",
                     "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
    },
    "A05": {
        "required": ["MSH", "EVN", "PID", "PV1"],
        "optional": ["SFT", "PD1", "NK1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM", "ZFA", "PDA", "ZFD",
                     "DB1", "OBX", "AL1", "DG1", "DRG", "GT1", "ACC", "UB1", "UB2",
                     "ZFU", "ZFS"],
    },
    "A06": {
        "required": ["MSH", "EVN", "PID", "PV1"],
        "optional": ["SFT", "PD1", "NK1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM",
                     "DB1", "OBX", "AL1", "DG1", "DRG", "GT1", "ACC", "UB1", "UB2", "PDA",
                     "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
    },
    "A08": {
        "required": ["MSH", "EVN", "PID", "PV1"],
        "optional": ["SFT", "PD1", "NK1", "PV2",
                     "DB1", "OBX", "AL1", "DG1", "DRG", "GT1", "ACC", "UB1", "UB2", "PDA",
                     "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
        "forbidden": ["ZBE"],  # Supprimé du A08 selon note dans HAPI
    },
    "A11": {
        "required": ["MSH", "EVN", "PID", "PV1"],
        "optional": ["SFT", "PD1", "NK1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM",
                     "DB1", "OBX", "DG1", "DRG"],
    },
    "A12": {
        "required": ["MSH", "EVN", "PID", "PV1"],
        "optional": ["SFT", "PD1", "NK1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM",
                     "DB1", "OBX", "DG1"],
    },
    "A13": {
        "required": ["MSH", "EVN", "PID", "PV1"],
        "optional": ["SFT", "PD1", "NK1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM",
                     "DB1", "OBX", "DG1", "DRG"],
    },
    "A21": {
        "required": ["MSH", "EVN", "PID", "PV1"],
        "optional": ["SFT", "PD1", "NK1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM",
                     "DB1", "OBX"],
    },
    "A22": {
        "required": ["MSH", "EVN", "PID", "PV1"],
        "optional": ["SFT", "PD1", "NK1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM",
                     "DB1", "OBX"],
    },
    "A23": {
        "required": ["MSH", "EVN", "PID", "PV1"],
        "optional": ["SFT", "PD1", "NK1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM",
                     "DB1", "OBX", "DG1"],
    },
    "A52": {
        "required": ["MSH", "EVN", "PID", "PV1"],
        "optional": ["SFT", "PD1", "NK1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM",
                     "DB1", "OBX"],
    },
    "A53": {
        "required": ["MSH", "EVN", "PID", "PV1"],
        "optional": ["SFT", "PD1", "NK1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM",
                     "DB1", "OBX"],
    },
    # Événements d'identité (pas de PV1 requis)
    "A28": {
        "required": ["MSH", "EVN", "PID"],
        "optional": ["SFT", "PD1", "NK1", "PV1", "PV2", "ZPA", "AL1", "DG1", "GT1"],
    },
    "A31": {
        "required": ["MSH", "EVN", "PID"],
        "optional": ["SFT", "PD1", "NK1", "PV1", "PV2", "ZPA", "AL1", "DG1", "GT1"],
    },
    "A40": {
        "required": ["MSH", "EVN", "PID"],
        "optional": ["SFT", "PD1", "NK1", "MRG"],
    },
    "A47": {
        "required": ["MSH", "EVN", "PID"],
        "optional": ["SFT", "PD1", "MRG"],
    },
}

# Events that are identity-only in IHE PAM; PV1 is optional
IDENTITY_ONLY = {"A28", "A31", "A40", "A47"}

# Events which normally require a PV1 (visit context)
REQUIRE_PV1 = {
    "A01", "A03", "A04", "A05", "A06", "A07", "A08", "A11",
    "A12", "A13", "A21", "A22", "A23", "A52", "A53"
}

# Ordre attendu des segments principaux selon HAPI structures
# Format: liste ordonnée des segments (requis et optionnels)
SEGMENT_ORDER = {
    "A01": ["MSH", "SFT", "EVN", "PID", "PD1", "NK1", "PV1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM", "DB1", "OBX", "AL1", "DG1", "DRG", "GT1", "ACC", "UB1", "UB2", "PDA", "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
    "A03": ["MSH", "SFT", "EVN", "PID", "PD1", "PV1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM", "DB1", "DG1", "DRG", "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
    "A04": ["MSH", "SFT", "EVN", "PID", "PD1", "NK1", "PV1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM", "OBX", "AL1", "DG1", "DRG", "GT1", "ACC", "UB1", "UB2", "PDA", "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
    "A05": ["MSH", "SFT", "EVN", "PID", "PD1", "PV1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM", "OBX", "AL1", "DG1", "DRG", "GT1", "ACC", "UB1", "UB2", "PDA", "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
    "A06": ["MSH", "SFT", "EVN", "PID", "PD1", "MRG", "PV1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM", "OBX", "AL1", "DG1", "DRG", "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
    "A07": ["MSH", "SFT", "EVN", "PID", "PD1", "MRG", "PV1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM", "OBX", "AL1", "DG1", "DRG", "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
    "A08": ["MSH", "SFT", "EVN", "PID", "PD1", "NK1", "PV1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM", "OBX", "AL1", "DG1", "DRG", "GT1", "ACC", "UB1", "UB2", "PDA", "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
    "A11": ["MSH", "SFT", "EVN", "PID", "PD1", "PV1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM", "OBX", "AL1", "DG1", "DRG", "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
    "A12": ["MSH", "SFT", "EVN", "PID", "PD1", "PV1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM", "OBX", "DG1", "DRG", "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
    "A13": ["MSH", "SFT", "EVN", "PID", "PD1", "PV1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM", "OBX", "AL1", "DG1", "DRG", "GT1", "ACC", "UB1", "UB2", "PDA", "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
    "A21": ["MSH", "SFT", "EVN", "PID", "PD1", "PV1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM", "OBX", "AL1", "DG1", "DRG", "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
    "A22": ["MSH", "SFT", "EVN", "PID", "PD1", "PV1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM", "OBX", "AL1", "DG1", "DRG", "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
    "A23": ["MSH", "SFT", "EVN", "PID", "PD1", "PV1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM", "OBX", "AL1", "DG1", "DRG", "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
    "A28": ["MSH", "SFT", "EVN", "PID", "PD1", "NK1", "PV1", "PV2", "ZBE", "OBX", "AL1", "DG1", "GT1", "ACC", "UB1", "UB2", "ZPA"],
    "A31": ["MSH", "SFT", "EVN", "PID", "PD1", "NK1", "PV1", "PV2", "ZBE", "OBX", "AL1", "DG1", "GT1", "ACC", "UB1", "UB2", "ZPA"],
    "A40": ["MSH", "SFT", "EVN", "PID", "PD1", "MRG", "PV1", "ZPA"],
    "A47": ["MSH", "SFT", "EVN", "PID", "PD1", "MRG", "PV1", "ZPA"],
    "A52": ["MSH", "SFT", "EVN", "PID", "PD1", "PV1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM", "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
    "A53": ["MSH", "SFT", "EVN", "PID", "PD1", "PV1", "PV2", "ZBE", "ZFP", "ZFV", "ZFM", "ZFU", "ZPA", "ZPV", "ZFT", "ZFI"],
}


@dataclass
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"  # error|warn|info


@dataclass
class ValidationResult:
    is_valid: bool
    level: str              # ok|warn|fail
    event: str              # e.g., A01
    message_type: str       # e.g., ADT^A01
    issues: List[ValidationIssue]

    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "level": self.level,
            "event": self.event,
            "message_type": self.message_type,
            "issues": [asdict(i) for i in self.issues],
        }


def _split_lines(msg: str) -> List[str]:
    if not msg:
        return []
    return msg.replace("\r\n", "\r").replace("\n", "\r").split("\r")


def _get_first_segment(msg: str, prefix: str) -> Optional[str]:
    for line in _split_lines(msg):
        if line.startswith(prefix + "|"):
            return line
    return None


def _field(parts: List[str], idx: int) -> str:
    return parts[idx] if len(parts) > idx else ""


def _validate_segment_order(msg: str, trigger: str, issues: List[ValidationIssue]) -> None:
    """Valide l'ordre des segments selon les structures HAPI.
    
    Les segments doivent apparaître dans l'ordre défini par SEGMENT_ORDER.
    Les segments doivent être dans l'ordre croissant de leur position attendue.
    """
    if trigger not in SEGMENT_ORDER:
        return  # Pas d'ordre défini pour ce trigger
    
    expected_order = SEGMENT_ORDER[trigger]
    lines = _split_lines(msg)
    
    # Extraire les segments présents avec leurs positions
    present_segments = []
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        seg_name = line[:3].strip()
        if seg_name and seg_name in expected_order:
            expected_pos = expected_order.index(seg_name)
            present_segments.append((seg_name, idx, expected_pos))
    
    # Vérifier que l'ordre attendu est respecté
    # Pour chaque segment, sa position attendue doit être >= à celle du segment précédent
    for i in range(1, len(present_segments)):
        curr_seg, curr_line, curr_exp = present_segments[i]
        prev_seg, prev_line, prev_exp = present_segments[i-1]
        
        if curr_exp < prev_exp:
            # Le segment actuel a une position attendue AVANT le segment précédent
            # = il est mal placé (devrait venir avant)
            issues.append(ValidationIssue(
                f"SEGMENT_ORDER_{curr_seg}",
                f"Segment {curr_seg} at line {curr_line+1} should appear before {prev_seg} (line {prev_line+1}) according to HAPI {trigger} structure",
                severity="warn"
            ))


def _validate_cx_identifier(cx: str, field_name: str, issues: List[ValidationIssue]) -> None:
    """Valide un identifiant CX (Extended Composite ID with Check Digit).
    
    Format CX: ID^CheckDigit^CheckDigitScheme^AssigningAuthority^IdentifierTypeCode^AssigningFacility
    Composants: ID (requis), reste optionnel
    """
    if not cx or not cx.strip():
        return
    
    components = cx.split("^")
    id_value = components[0] if len(components) > 0 else ""
    
    if not id_value:
        issues.append(ValidationIssue(
            f"{field_name}_CX_ID_EMPTY",
            f"{field_name}: CX ID component (1st) must not be empty",
            severity="error"
        ))
    
    # Check digit scheme si check digit présent
    if len(components) > 1 and components[1]:
        check_digit = components[1]
        check_scheme = components[2] if len(components) > 2 else ""
        if not check_scheme:
            issues.append(ValidationIssue(
                f"{field_name}_CX_SCHEME_MISSING",
                f"{field_name}: CX Check Digit Scheme required when Check Digit present",
                severity="warn"
            ))


def _validate_xpn_name(xpn: str, field_name: str, issues: List[ValidationIssue]) -> None:
    """Valide un nom XPN (Extended Person Name).
    
    Format XPN: FamilyName^GivenName^MiddleName^Suffix^Prefix^Degree^NameTypeCode^...
    Au minimum FamilyName OU GivenName requis.
    """
    if not xpn or not xpn.strip():
        return
    
    components = xpn.split("^")
    family = components[0] if len(components) > 0 else ""
    given = components[1] if len(components) > 1 else ""
    
    if not family and not given:
        issues.append(ValidationIssue(
            f"{field_name}_XPN_INCOMPLETE",
            f"{field_name}: XPN must have at least Family Name or Given Name",
            severity="error"
        ))
    
    # Name Type Code (7ème composant) validation si présent
    if len(components) > 6 and components[6]:
        name_type = components[6]
        valid_types = {"A", "B", "C", "D", "I", "L", "M", "N", "P", "R", "S", "T", "U"}
        if name_type not in valid_types:
            issues.append(ValidationIssue(
                f"{field_name}_XPN_TYPE_INVALID",
                f"{field_name}: XPN Name Type Code '{name_type}' not in HL7 Table 0200",
                severity="warn"
            ))


def _validate_xad_address(xad: str, field_name: str, issues: List[ValidationIssue]) -> None:
    """Valide une adresse XAD (Extended Address).
    
    Format XAD: StreetAddress^OtherDesignation^City^State^Zip^Country^AddressType^...
    Au minimum un composant d'adresse doit être présent.
    """
    if not xad or not xad.strip():
        return
    
    components = xad.split("^")
    
    # Vérifier qu'au moins un composant d'adresse est présent
    has_content = any(
        components[i].strip() if len(components) > i else ""
        for i in range(6)  # Street, Other, City, State, Zip, Country
    )
    
    if not has_content:
        issues.append(ValidationIssue(
            f"{field_name}_XAD_EMPTY",
            f"{field_name}: XAD must have at least one address component",
            severity="warn"
        ))
    
    # Address Type (7ème composant) validation si présent
    if len(components) > 6 and components[6]:
        addr_type = components[6]
        # HL7 Table 0190: B, BA, BDL, BI, BR, C, F, H, L, M, N, O, P, RH, SH
        valid_types = {"B", "BA", "BDL", "BI", "BR", "C", "F", "H", "L", "M", "N", "O", "P", "RH", "SH", "BIR"}
        if addr_type and addr_type not in valid_types:
            issues.append(ValidationIssue(
                f"{field_name}_XAD_TYPE_INVALID",
                f"{field_name}: XAD Address Type '{addr_type}' not in HL7 Table 0190 (or custom)",
                severity="info"
            ))


def _validate_xtn_telecom(xtn: str, field_name: str, issues: List[ValidationIssue]) -> None:
    """Valide un numéro de téléphone XTN (Extended Telecommunication Number).
    
    Format XTN: [CountryCode]^TelephoneNumber^TelecommunicationUseCode^TelecommunicationEquipmentType^...
    Le numéro de téléphone (2ème ou formule complète dans 1er) est requis.
    """
    if not xtn or not xtn.strip():
        return
    
    components = xtn.split("^")
    
    # XTN peut avoir le numéro dans le 1er composant (forme simple) ou 2ème (forme étendue)
    phone = components[0] if len(components) > 0 else ""
    phone_extended = components[1] if len(components) > 1 else ""
    
    if not phone and not phone_extended:
        issues.append(ValidationIssue(
            f"{field_name}_XTN_EMPTY",
            f"{field_name}: XTN must have a telephone number",
            severity="warn"
        ))
    
    # Telecom Use Code (3ème composant) validation
    if len(components) > 2 and components[2]:
        use_code = components[2]
        valid_uses = {"ASN", "BPN", "EMR", "NET", "ORN", "PRN", "PRS", "VHN", "WPN"}
        if use_code not in valid_uses:
            issues.append(ValidationIssue(
                f"{field_name}_XTN_USE_INVALID",
                f"{field_name}: XTN Use Code '{use_code}' not in HL7 Table 0201",
                severity="info"
            ))
    
    # Equipment Type (4ème composant) validation
    if len(components) > 3 and components[3]:
        equip_type = components[3]
        valid_types = {"BP", "CP", "FX", "Internet", "MD", "PH", "SAT", "TDD", "TTY", "X.400"}
        if equip_type not in valid_types:
            issues.append(ValidationIssue(
                f"{field_name}_XTN_EQUIP_INVALID",
                f"{field_name}: XTN Equipment Type '{equip_type}' not in HL7 Table 0202",
                severity="info"
            ))


def _validate_ts_timestamp(ts: str, field_name: str, issues: List[ValidationIssue]) -> None:
    """Valide un timestamp TS (Time Stamp).
    
    Format TS: YYYY[MM[DD[HH[MM[SS[.S[S[S[S]]]]]]]]][+/-ZZZZ]
    Minimum YYYY requis, format strict.
    """
    if not ts or not ts.strip():
        return
    
    # Enlever le timezone pour validation du core
    ts_core = ts.split("+")[0].split("-")[0] if ("+" in ts or "-" in ts[4:]) else ts
    
    # Enlever les fractions de secondes
    if "." in ts_core:
        ts_core = ts_core.split(".")[0]
    
    # Valider longueur et format
    if len(ts_core) < 4:
        issues.append(ValidationIssue(
            f"{field_name}_TS_TOO_SHORT",
            f"{field_name}: TS must be at least YYYY (4 chars), got '{ts}'",
            severity="error"
        ))
        return
    
    # Valider que c'est numérique
    if not ts_core.isdigit():
        issues.append(ValidationIssue(
            f"{field_name}_TS_FORMAT",
            f"{field_name}: TS format invalid '{ts}', expected YYYY[MM[DD[HH[MM[SS]]]]]",
            severity="error"
        ))
        return
    
    # Valider les valeurs selon la longueur
    year = ts_core[:4]
    if len(ts_core) >= 6:
        month = ts_core[4:6]
        if not (1 <= int(month) <= 12):
            issues.append(ValidationIssue(
                f"{field_name}_TS_MONTH_INVALID",
                f"{field_name}: TS month '{month}' not in 01-12",
                severity="error"
            ))
    
    if len(ts_core) >= 8:
        day = ts_core[6:8]
        if not (1 <= int(day) <= 31):
            issues.append(ValidationIssue(
                f"{field_name}_TS_DAY_INVALID",
                f"{field_name}: TS day '{day}' not in 01-31",
                severity="error"
            ))
    
    if len(ts_core) >= 10:
        hour = ts_core[8:10]
        if not (0 <= int(hour) <= 23):
            issues.append(ValidationIssue(
                f"{field_name}_TS_HOUR_INVALID",
                f"{field_name}: TS hour '{hour}' not in 00-23",
                severity="error"
            ))
    
    if len(ts_core) >= 12:
        minute = ts_core[10:12]
        if not (0 <= int(minute) <= 59):
            issues.append(ValidationIssue(
                f"{field_name}_TS_MINUTE_INVALID",
                f"{field_name}: TS minute '{minute}' not in 00-59",
                severity="error"
            ))
    
    if len(ts_core) >= 14:
        second = ts_core[12:14]
        if not (0 <= int(second) <= 59):
            issues.append(ValidationIssue(
                f"{field_name}_TS_SECOND_INVALID",
                f"{field_name}: TS second '{second}' not in 00-59",
                severity="error"
            ))


def _get_all_segments(msg: str) -> Set[str]:
    """Retourne l'ensemble des types de segments présents dans le message."""
    segments = set()
    for line in _split_lines(msg):
        if not line or "|" not in line:
            continue
        seg_type = line.split("|")[0]
        if seg_type:
            segments.add(seg_type)
    return segments


def validate_pam(msg: str, direction: str = "in", profile: str = "IHE_PAM_FR") -> ValidationResult:
    issues: List[ValidationIssue] = []

    if not msg or not msg.startswith("MSH|"):
        issues.append(ValidationIssue("STRUCTURE", "Message must start with MSH"))
        return ValidationResult(False, "fail", event="", message_type="", issues=issues)

    msh = parse_msh_fields(msg)
    if not msh:
        issues.append(ValidationIssue("MSH_PARSE", "Unable to parse MSH segment"))
        return ValidationResult(False, "fail", event="", message_type="", issues=issues)

    msg_type = f"{msh.get('type','')}^{msh.get('trigger','')}".strip("^")
    trigger = msh.get("trigger") or ""

    # HL7 v2.5 base rules: MSH validation
    msh_line = _get_first_segment(msg, "MSH")
    if msh_line:
        # MSH-1 (Field Separator) should be |
        if len(msh_line) < 4 or msh_line[3] != "|":
            issues.append(ValidationIssue("MSH1_INVALID", "MSH-1 (Field Separator) must be '|'", severity="error"))
        
        # MSH-2 (Encoding Characters) should be ^~\& (standard HL7)
        msh_parts = msh_line.split("|")
        if len(msh_parts) > 1:
            encoding = msh_parts[1]
            if encoding not in ("^~\\&", "^~\\&"):  # Accept both with/without escape
                issues.append(ValidationIssue("MSH2_NONSTANDARD", f"MSH-2 (Encoding Characters) is '{encoding}', standard is '^~\\&'", severity="warn"))
        
        # MSH-9 (Message Type) format
        msg_type_field = _field(msh_parts, 8) if len(msh_parts) > 8 else ""
        if not msg_type_field or "^" not in msg_type_field:
            issues.append(ValidationIssue("MSH9_FORMAT", "MSH-9 (Message Type) must be in format type^trigger[^structure]", severity="error"))
        
        # MSH-10 (Message Control ID) non vide
        control_id = _field(msh_parts, 9) if len(msh_parts) > 9 else ""
        if not control_id:
            issues.append(ValidationIssue("MSH10_EMPTY", "MSH-10 (Message Control ID) is required", severity="error"))
        
        # MSH-11 (Processing ID) valide
        proc_id = _field(msh_parts, 10) if len(msh_parts) > 10 else ""
        if proc_id and proc_id not in ("P", "D", "T"):
            issues.append(ValidationIssue("MSH11_INVALID", f"MSH-11 (Processing ID) '{proc_id}' not in (P, D, T)", severity="warn"))
        
        # MSH-12 (Version ID) présent
        version = _field(msh_parts, 11) if len(msh_parts) > 11 else ""
        if not version:
            issues.append(ValidationIssue("MSH12_MISSING", "MSH-12 (Version ID) is recommended", severity="info"))

    # EVN presence and consistency
    evn = _get_first_segment(msg, "EVN")
    if not evn:
        issues.append(ValidationIssue("EVN_MISSING", "EVN segment is required"))
    else:
        evn_parts = evn.split("|")
        evn_code = _field(evn_parts, 1)
        if trigger and evn_code and evn_code != trigger:
            issues.append(ValidationIssue("EVN_MISMATCH", f"EVN-1 ({evn_code}) differs from MSH-9 trigger ({trigger})", severity="warn"))
        
        # EVN-2 (Recorded Date/Time) - TS type validation
        evn2 = _field(evn_parts, 2)
        if evn2:
            _validate_ts_timestamp(evn2, "EVN2", issues)
        
        # EVN-6 (Event Occurred) - TS type validation
        evn6 = _field(evn_parts, 6)
        if evn6:
            _validate_ts_timestamp(evn6, "EVN6", issues)

    # PID presence and HL7 v2.5 base rules
    pid = _get_first_segment(msg, "PID")
    if not pid:
        issues.append(ValidationIssue("PID_MISSING", "PID segment is required"))
    else:
        pid_parts = pid.split("|")
        
        # PID-3 (Patient Identifier List) - CX type validation
        pid3 = _field(pid_parts, 3)
        if not pid3:
            issues.append(ValidationIssue("PID3_EMPTY", "PID-3 (Patient Identifier List) must not be empty"))
        else:
            # Répétitions séparées par ~ pour PID-3
            for idx, cx_id in enumerate(pid3.split("~")):
                if cx_id:
                    _validate_cx_identifier(cx_id, f"PID3[{idx}]", issues)
        
        # PID-5 (Patient Name) - XPN type validation
        pid5 = _field(pid_parts, 5)
        if not pid5:
            issues.append(ValidationIssue("PID5_MISSING", "PID-5 (Patient Name) is strongly recommended", severity="warn"))
        else:
            # Répétitions séparées par ~ pour PID-5
            for idx, xpn_name in enumerate(pid5.split("~")):
                if xpn_name:
                    _validate_xpn_name(xpn_name, f"PID5[{idx}]", issues)
        
        # PID-7 (Date of Birth) - TS type validation
        pid7 = _field(pid_parts, 7)
        if pid7:
            _validate_ts_timestamp(pid7, "PID7", issues)
        
        # PID-11 (Patient Address) - XAD type validation
        pid11 = _field(pid_parts, 11)
        if pid11:
            # Répétitions séparées par ~ pour PID-11
            for idx, xad_addr in enumerate(pid11.split("~")):
                if xad_addr:
                    _validate_xad_address(xad_addr, f"PID11[{idx}]", issues)
        
        # PID-13 (Phone Number - Home) - XTN type validation
        pid13 = _field(pid_parts, 13)
        if pid13:
            # Répétitions séparées par ~ pour PID-13
            for idx, xtn_phone in enumerate(pid13.split("~")):
                if xtn_phone:
                    _validate_xtn_telecom(xtn_phone, f"PID13[{idx}]", issues)
        
        # PID-14 (Phone Number - Business) - XTN type validation
        pid14 = _field(pid_parts, 14)
        if pid14:
            # Répétitions séparées par ~ pour PID-14
            for idx, xtn_phone in enumerate(pid14.split("~")):
                if xtn_phone:
                    _validate_xtn_telecom(xtn_phone, f"PID14[{idx}]", issues)

    # Validation structure HAPI détaillée (si trigger connu)
    if trigger in SEGMENT_RULES:
        rules = SEGMENT_RULES[trigger]
        present = _get_all_segments(msg)
        
        # Vérifier segments requis
        for seg in rules.get("required", []):
            if seg not in present:
                issues.append(ValidationIssue(
                    f"{seg}_MISSING",
                    f"Segment {seg} requis pour {trigger} (structure HAPI)",
                    severity="error"
                ))
        
        # Vérifier segments interdits
        for seg in rules.get("forbidden", []):
            if seg in present:
                issues.append(ValidationIssue(
                    f"{seg}_FORBIDDEN",
                    f"Segment {seg} interdit pour {trigger} (structure HAPI)",
                    severity="error"
                ))
        
        # Valider l'ordre des segments selon HAPI
        _validate_segment_order(msg, trigger, issues)
        
        # Info: segments optionnels présents (pour traçabilité détaillée)
        optional = rules.get("optional", [])
        present_optional = [s for s in optional if s in present]
        if present_optional:
            issues.append(ValidationIssue(
                "OPTIONAL_SEGMENTS",
                f"Segments optionnels présents: {', '.join(sorted(present_optional))}",
                severity="info"
            ))
    else:
        # Trigger inconnu: validation générique (legacy)
        pv1 = _get_first_segment(msg, "PV1")
        if trigger in REQUIRE_PV1 and not pv1:
            issues.append(ValidationIssue("PV1_MISSING", f"PV1 segment is required for event {trigger}"))
        if trigger in IDENTITY_ONLY and pv1:
            issues.append(ValidationIssue("PV1_UNEXPECTED", f"PV1 is generally not expected for identity-only event {trigger}", severity="info"))
    
    # Validation des champs PV1 (types de données complexes) si présent
    pv1 = _get_first_segment(msg, "PV1")
    if pv1:
        pv1_parts = pv1.split("|")
        
        # PV1-2 (Patient Class) - requis
        pv1_2 = _field(pv1_parts, 2)
        if not pv1_2:
            issues.append(ValidationIssue("PV1_2_MISSING", "PV1-2 (Patient Class) is required", severity="error"))
        else:
            # HL7 Table 0004: E, I, O, P, R, B, C, N, U
            valid_classes = {"E", "I", "O", "P", "R", "B", "C", "N", "U"}
            if pv1_2 not in valid_classes:
                issues.append(ValidationIssue("PV1_2_INVALID", f"PV1-2 (Patient Class) '{pv1_2}' not in HL7 Table 0004", severity="warn"))
        
        # PV1-3 (Assigned Patient Location) - PL type (recommandé)
        pv1_3 = _field(pv1_parts, 3)
        if pv1_3:
            # Format PL: PointOfCare^Room^Bed^Facility^LocationStatus^PersonLocationType^Building^Floor
            pl_comps = pv1_3.split("^")
            if not any(pl_comps[:4]):  # Au moins un des 4 premiers composants
                issues.append(ValidationIssue("PV1_3_EMPTY", "PV1-3 (Assigned Patient Location) should have at least PointOfCare, Room, Bed or Facility", severity="warn"))
        
        # PV1-7 (Attending Doctor) - XCN type
        pv1_7 = _field(pv1_parts, 7)
        if pv1_7:
            # Format XCN: ID^FamilyName^GivenName^MiddleName^Suffix^Prefix^Degree^SourceTable^AssigningAuthority^NameTypeCode^...
            for idx, xcn in enumerate(pv1_7.split("~")):
                if xcn:
                    xcn_comps = xcn.split("^")
                    xcn_id = xcn_comps[0] if len(xcn_comps) > 0 else ""
                    xcn_family = xcn_comps[1] if len(xcn_comps) > 1 else ""
                    if not xcn_id and not xcn_family:
                        issues.append(ValidationIssue(f"PV1_7_XCN_{idx}_INCOMPLETE", f"PV1-7[{idx}] (Attending Doctor) must have ID or Family Name", severity="warn"))
        
        # PV1-19 (Visit Number) - CX type (recommandé)
        pv1_19 = _field(pv1_parts, 19)
        if pv1_19:
            _validate_cx_identifier(pv1_19, "PV1_19", issues)
        
        # PV1-44 (Admit Date/Time) - TS type
        pv1_44 = _field(pv1_parts, 44)
        if pv1_44:
            _validate_ts_timestamp(pv1_44, "PV1_44", issues)
        
        # PV1-45 (Discharge Date/Time) - TS type
        pv1_45 = _field(pv1_parts, 45)
        if pv1_45:
            _validate_ts_timestamp(pv1_45, "PV1_45", issues)

    # Determine overall level
    has_error = any(i.severity == "error" for i in issues)
    has_warn = any(i.severity == "warn" for i in issues)
    level = "fail" if has_error else ("warn" if has_warn else "ok")
    is_valid = not has_error

    return ValidationResult(is_valid=is_valid, level=level, event=trigger, message_type=msg_type, issues=issues)


__all__ = ["validate_pam", "ValidationResult", "ValidationIssue"]
