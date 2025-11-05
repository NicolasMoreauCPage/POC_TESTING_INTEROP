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

    # PID presence and HL7 v2.5 base rules
    pid = _get_first_segment(msg, "PID")
    if not pid:
        issues.append(ValidationIssue("PID_MISSING", "PID segment is required"))
    else:
        pid_parts = pid.split("|")
        
        # PID-3 (Patient Identifier List) non vide (HL7 v2.5 required)
        pid3 = _field(pid_parts, 3)
        if not pid3:
            issues.append(ValidationIssue("PID3_EMPTY", "PID-3 (Patient Identifier List) must not be empty"))
        
        # PID-5 (Patient Name) présent (HL7 v2.5 strongly recommended)
        pid5 = _field(pid_parts, 5)
        if not pid5:
            issues.append(ValidationIssue("PID5_MISSING", "PID-5 (Patient Name) is strongly recommended", severity="warn"))
        
        # PID-7 (Date of Birth) format si présent
        pid7 = _field(pid_parts, 7)
        if pid7 and len(pid7) >= 8:
            # Vérifier format YYYYMMDD minimum
            try:
                int(pid7[:8])
            except ValueError:
                issues.append(ValidationIssue("PID7_FORMAT", f"PID-7 (Date of Birth) '{pid7}' format invalide (attendu: YYYYMMDD[HHMM[SS]])", severity="warn"))

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

    # Determine overall level
    has_error = any(i.severity == "error" for i in issues)
    has_warn = any(i.severity == "warn" for i in issues)
    level = "fail" if has_error else ("warn" if has_warn else "ok")
    is_valid = not has_error

    return ValidationResult(is_valid=is_valid, level=level, event=trigger, message_type=msg_type, issues=issues)


__all__ = ["validate_pam", "ValidationResult", "ValidationIssue"]
