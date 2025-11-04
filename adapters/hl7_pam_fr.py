"""
Génération de messages HL7 PAM spécifiques au profil France.

Ce module fournit une implémentation par défaut de `build_message_for_movement`
afin que l'import dynamique réalisé dans `app.services.pam` ne lève plus
`ModuleNotFoundError` lors des tests en local.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _format_ts(value: datetime | None) -> str:
    if not value:
        return datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return value.strftime("%Y%m%d%H%M%S")


def build_message_for_movement(
    *,
    dossier: Any,
    venue: Any,
    movement: Any,
    patient: Any,
    movement_namespace: Any = None,
) -> str:
    """
    Construit un message HL7 minimal pour un mouvement patient.
    
    Args:
        dossier: Dossier patient
        venue: Venue/séjour
        movement: Mouvement patient
        patient: Patient
        movement_namespace: Namespace pour l'identifiant du mouvement (optionnel)
    
    Returns:
        Message HL7 PAM avec segment ZBE pour le mouvement
    """
    when = _format_ts(getattr(movement, "when", None))
    control_id = getattr(movement, "mouvement_seq", getattr(movement, "id", ""))
    location = (
        getattr(movement, "location", None)
        or getattr(venue, "code", None)
        or "UNKNOWN"
    )
    uf_responsabilite = (
        getattr(venue, "uf_responsabilite", None)
        or getattr(dossier, "uf_responsabilite", None)
        or "UF-UNKNOWN"
    )

    msh = (
        "MSH|^~\\&|POC|POC|DST|DST|"
        f"{when}||ADT^{movement.type or 'A02'}|{control_id}|P|2.5"
    )
    pid = (
        "PID|||"
        f"{getattr(patient, 'external_id', '')}||"
        f"{getattr(patient, 'family', '')}^{getattr(patient, 'given', '')}"
        f"||{getattr(patient, 'birth_date', '')}|{getattr(patient, 'gender', '')}"
    )
    pv1 = f"PV1||I|{location}|||^^^^^{uf_responsabilite}"
    
    # Construction du segment ZBE (mouvement)
    # ZBE-1: Identifiant du mouvement au format: ID^AUTHORITY^OID^ISO
    movement_id = getattr(movement, "mouvement_seq", getattr(movement, "id", ""))
    
    if movement_namespace:
        # Utiliser le namespace fourni
        authority = getattr(movement_namespace, "name", "UNKNOWN")
        oid = getattr(movement_namespace, "oid", "")
        zbe_1 = f"{movement_id}^{authority}^{oid}^ISO"
    else:
        # Fallback si pas de namespace
        zbe_1 = str(movement_id)
    
    # ZBE-2: Date/heure du mouvement
    zbe_2 = when
    
    # ZBE-3: Action (vide par défaut)
    zbe_3 = ""
    
    # ZBE-4: Type d'action (INSERT, UPDATE, CANCEL)
    zbe_4 = "INSERT"
    
    # ZBE-5: Indicateur annulation (N par défaut)
    zbe_5 = "N"
    
    # ZBE-6: Évènement d'origine (vide ou type de mouvement)
    zbe_6 = ""
    
    # ZBE-7: UF responsable (format: ^^^^^^UF^^^CODE_UF)
    zbe_7 = f"^^^^^^UF^^^{uf_responsabilite}"
    
    # ZBE-8: Vide
    zbe_8 = ""
    
    # ZBE-9: Mode de traitement (HMS par défaut = Hospitalisation Médecine/Chirurgie)
    zbe_9 = "HMS"
    
    zbe = f"ZBE|{zbe_1}|{zbe_2}|{zbe_3}|{zbe_4}|{zbe_5}|{zbe_6}|{zbe_7}|{zbe_8}|{zbe_9}"
    
    return "\r".join((msh, pid, pv1, zbe))

