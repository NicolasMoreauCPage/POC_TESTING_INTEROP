"""
Gestion des transitions IHE PAM.

Les transitions sont exprimées directement sous forme message -> message, en
se basant sur le tableau métier fourni (annulations, permissions, mouvements,
etc.). Les notes du tableau sont intégrées :

* A11 annule la venue : seul un nouveau A01/A04/A05 peut suivre.
* A38 annule la pré-admission et ne peut pas suivre un A11.
* Les Z80/Z81/Z84/Z85 ne peuvent survenir qu'en contexte d'hospitalisation.

Les clés sont les codes d'événements ADT (A01, A02, …, Z99). Une valeur
``None`` représente l'absence d'événement précédent (début de parcours).
"""

from __future__ import annotations

from typing import Dict, Iterable, Optional, Set

# Evenements possibles au démarrage (aucun historique)
INITIAL_EVENTS: Set[str] = {
    "A01",  # Admission directe
    "A04",  # Enregistrement externe
    "A05",  # Pré-admission
    "A38",  # Annulation pré-admission (cas de nettoyage)
}

# Transitions autorisées message -> message
ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    "A01": {
        "A02",
        "A03",
        "A11",
        "A21",
        "A44",
        "A52",
        "A53",
        "A54",
        "A55",
        "Z99",
    },
    "A04": {
        # Note: A03 (discharge/absence) NOT allowed from A04 (outpatient) per IHE PAM
        # A03 is only allowed from inpatient encounters (A01, A02)
        "A04",
        "A06",
        "A07",
        "A11",
        "Z99",
    },
    "A05": {
        "A01",
        "A04",
        "A38",
        "Z99",
    },
    "A02": {
        "A02",
        "A03",
        "A12",
        "A21",
        "A44",
        "A52",
        "A53",
        "A54",
        "A55",
        "Z99",
    },
    "A06": {"A06", "A07", "A11", "A01", "Z99"},
    "A07": {"A06", "A07", "A11", "A01", "Z99"},
    "A11": {"A01", "A04", "A05"},  # note 1
    "A12": {
        "A02",
        "A03",
        "A11",
        "A13",
        "A21",
        "A22",
        "A52",
        "A53",
        "Z80",
        "Z81",
        "Z84",
        "Z85",
        "Z99",
    },
    "A13": {
        "A02",
        "A03",
        "A11",
        "A21",
        "A22",
        "A44",
        "A52",
        "A53",
        "A54",
        "A55",
        "Z80",
        "Z81",
        "Z84",
        "Z85",
        "Z99",
    },
    "A21": {"A22", "A52", "A03", "Z80", "Z81", "Z84", "Z85", "Z99"},
    "A22": {
        "A02",
        "A03",
        "A11",
        "A13",
        "A21",
        "A22",
        "A44",
        "A52",
        "A53",
        "A54",
        "A55",
        "Z80",
        "Z81",
        "Z84",
        "Z85",
        "Z99",
    },
    "A31": {"A01", "A04", "A05", "A06", "A07", "A31", "A38", "Z99"},
    "A03": {
        "A01",
        "A03",
        "A04",
        "A05",
        "A06",
        "A12",
        "A13",
        "A21",
        "A22",
        "A31",
        "Z99",
    },
    "A38": {"A05", "A01", "A04"},  # note 3
    "A40": {"A01", "A04", "A05"},
    "A44": {
        "A02",
        "A03",
        "A11",
        "A21",
        "A22",
        "A44",
        "A52",
        "A53",
        "A54",
        "A55",
        "Z80",
        "Z81",
        "Z84",
        "Z85",
        "Z99",
    },
    "A52": {
        "A02",
        "A03",
        "A11",
        "A13",
        "A21",
        "A22",
        "A44",
        "A52",
        "A53",
        "A54",
        "A55",
        "Z80",
        "Z81",
        "Z84",
        "Z85",
        "Z99",
    },
    "A53": {"A22", "A03"},
    "A54": {
        "A02",
        "A03",
        "A11",
        "A13",
        "A21",
        "A22",
        "A44",
        "A52",
        "A53",
        "A54",
        "A55",
        "Z80",
        "Z81",
        "Z84",
        "Z85",
        "Z99",
    },
    "A55": {
        "A02",
        "A03",
        "A11",
        "A13",
        "A21",
        "A22",
        "A44",
        "A52",
        "A53",
        "A54",
        "A55",
        "Z80",
        "Z81",
        "Z84",
        "Z85",
        "Z99",
    },
    "Z80": {
        "A02",
        "A03",
        "A11",
        "A13",
        "A21",
        "A22",
        "A44",
        "A52",
        "A53",
        "A54",
        "A55",
        "Z80",
        "Z81",
        "Z84",
        "Z85",
        "Z99",
    },
    "Z81": {
        "A02",
        "A03",
        "A11",
        "A13",
        "A21",
        "A22",
        "A44",
        "A52",
        "A53",
        "A54",
        "A55",
        "Z80",
        "Z81",
        "Z84",
        "Z85",
        "Z99",
    },
    "Z84": {
        "A02",
        "A03",
        "A11",
        "A13",
        "A21",
        "A22",
        "A44",
        "A52",
        "A53",
        "A54",
        "A55",
        "Z80",
        "Z81",
        "Z84",
        "Z85",
        "Z99",
    },
    "Z85": {
        "A02",
        "A03",
        "A11",
        "A13",
        "A21",
        "A22",
        "A44",
        "A52",
        "A53",
        "A54",
        "A55",
        "Z80",
        "Z81",
        "Z84",
        "Z85",
        "Z99",
    },
    "Z99": {
        "A01",
        "A02",
        "A03",
        "A04",
        "A05",
        "A06",
        "A07",
        "A11",
        "A13",
        "A21",
        "A22",
        "A44",
        "A52",
        "A53",
        "A54",
        "A55",
        "Z80",
        "Z81",
        "Z84",
        "Z85",
        "Z99",
    },
}


def get_allowed_transitions(previous_event: Optional[str]) -> Set[str]:
    """Retourne l'ensemble des événements autorisés après ``previous_event``."""
    if previous_event is None:
        return set(INITIAL_EVENTS)
    return ALLOWED_TRANSITIONS.get(previous_event, set())


def is_valid_transition(previous_event: Optional[str], new_event: str) -> bool:
    """
    Vérifie si ``new_event`` est autorisé après ``previous_event``.

    Args:
        previous_event: Code de l'événement précédent (ou ``None``).
        new_event: Code de l'événement à valider.
    """
    return new_event in get_allowed_transitions(previous_event)


def assert_transition(previous_event: Optional[str], new_event: str) -> None:
    """
    Soulève une ``ValueError`` si la transition n'est pas autorisée.
    Utile pour centraliser les contrôles dans les handlers.
    """
    if not is_valid_transition(previous_event, new_event):
        allowed = ", ".join(sorted(get_allowed_transitions(previous_event))) or "aucun"
        context = previous_event or "début de parcours"
        raise ValueError(
            f"Transition IHE invalide : {context} -> {new_event} (attendu: {allowed})"
        )


# ---------------------------
# Visualisation / ergonomie
# ---------------------------

WORKFLOW_GRAPH = {
    "states": [
        {
            "id": "no_current",
            "label": "Pas de venue\ncourante",
            "x": 120,
            "y": 300,
        },
        {
            "id": "pre_admis_consult",
            "label": "Pré-admis\nconsult. externe",
            "x": 340,
            "y": 140,
        },
        {
            "id": "pre_admis_hospit",
            "label": "Pré-admis\nhospitalisation",
            "x": 340,
            "y": 360,
        },
        {
            "id": "consultant_urg",
            "label": "Consultant\nurgences",
            "x": 560,
            "y": 60,
        },
        {
            "id": "hospitalise",
            "label": "Hospitalisé\n(complet / partiel)",
            "x": 560,
            "y": 300,
        },
        {
            "id": "consultant_externe",
            "label": "Consultant\nexterne",
            "x": 780,
            "y": 140,
        },
        {
            "id": "absence_temp",
            "label": "Absence\ntemporaire",
            "x": 780,
            "y": 420,
        },
    ],
    "transitions": [
        {"source": "no_current", "target": "pre_admis_hospit", "event": "A05"},
        {"source": "no_current", "target": "pre_admis_consult", "event": "A04"},
        {"source": "no_current", "target": "hospitalise", "event": "A01"},
        {"source": "pre_admis_hospit", "target": "hospitalise", "event": "A01"},
        {"source": "pre_admis_hospit", "target": "no_current", "event": "A38"},
        {"source": "pre_admis_consult", "target": "consultant_externe", "event": "A04"},
        {"source": "pre_admis_consult", "target": "hospitalise", "event": "A01"},
        {"source": "hospitalise", "target": "absence_temp", "event": "A21"},
        {"source": "absence_temp", "target": "hospitalise", "event": "A22"},
        {"source": "hospitalise", "target": "consultant_externe", "event": "A06"},
        {"source": "consultant_externe", "target": "hospitalise", "event": "A07"},
        {"source": "hospitalise", "target": "consultant_urg", "event": "A06"},
        {"source": "consultant_urg", "target": "hospitalise", "event": "A07"},
        {"source": "hospitalise", "target": "no_current", "event": "A03"},
        {"source": "hospitalise", "target": "hospitalise", "event": "A02", "category": "neutral"},
        {"source": "hospitalise", "target": "hospitalise", "event": "A54", "category": "neutral"},
        {"source": "hospitalise", "target": "hospitalise", "event": "A55", "category": "neutral"},
        {"source": "hospitalise", "target": "hospitalise", "event": "Z80", "category": "neutral"},
    ],
}

# Métadonnées des événements supportés côté UI (mouvements actionnables)
SUPPORTED_WORKFLOW_EVENTS: Dict[str, Dict[str, object]] = {
    "A01": {
        "label": "Admission",
        "description": "Démarrer ou basculer une venue en hospitalisation.",
        "requires_location": True,
        "group": "change_state",
    },
    "A02": {
        "label": "Transfert / mise en lit",
        "description": "Déplacer le patient vers un autre lit ou une autre unité.",
        "requires_location": True,
        "group": "neutral",
    },
    "A03": {
        "label": "Sortie",
        "description": "Clôturer la venue en cours (retour au domicile, transfert externe, etc.).",
        "requires_location": False,
        "group": "change_state",
    },
    "A04": {
        "label": "Consultation externe",
        "description": "Créer une consultation externe (sans admission complète).",
        "requires_location": False,
        "group": "change_state",
    },
    "A05": {
        "label": "Pré-admission",
        "description": "Initier une pré-admission en hospitalisation.",
        "requires_location": False,
        "group": "change_state",
    },
    "A06": {
        "label": "Mutation vers consultation / urgence",
        "description": "Envoyer le patient vers une consultation ou une urgence.",
        "requires_location": False,
        "group": "neutral",
    },
    "A07": {
        "label": "Retour de consultation",
        "description": "Ramener un patient d'une consultation/urgence vers l'hospitalisation.",
        "requires_location": True,
        "group": "neutral",
    },
    "A21": {
        "label": "Permission (sortie temporaire)",
        "description": "Marquer une absence temporaire (permission).",
        "requires_location": False,
        "group": "change_state",
    },
    "A22": {
        "label": "Retour de permission",
        "description": "Fin d'une absence temporaire (permission).",
        "requires_location": True,
        "group": "change_state",
    },
    "A38": {
        "label": "Annuler pré-admission",
        "description": "Annule la pré-admission en cours.",
        "requires_location": False,
        "group": "change_state",
    },
}
