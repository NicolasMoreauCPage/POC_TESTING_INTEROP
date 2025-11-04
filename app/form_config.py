from enum import Enum
from typing import Dict, List, Any
from app.models import DossierType

# Énumérations pour les champs de type select
class AdmissionType(str, Enum):
    EMERGENCY = "emergency"
    ELECTIVE = "elective"
    NEWBORN = "newborn"
    URGENT = "urgent"
    OTHER = "other"

    @classmethod
    def choices(cls) -> List[Dict[str, str]]:
        return [{"value": e.value, "label": e.value.capitalize()} for e in cls]

class EndpointKind(str, Enum):
    MLLP = "MLLP"
    FHIR = "FHIR"

    @classmethod
    def choices(cls) -> List[Dict[str, str]]:
        return [{"value": e.value, "label": e.value} for e in cls]

class EndpointRole(str, Enum):
    SENDER = "sender"
    RECEIVER = "receiver"
    BOTH = "both"

    @classmethod
    def choices(cls) -> List[Dict[str, str]]:
        return [{"value": e.value, "label": e.value.capitalize()} for e in cls]

class AuthKind(str, Enum):
    NONE = "none"
    BEARER = "bearer"

    @classmethod
    def choices(cls) -> List[Dict[str, str]]:
        return [{"value": e.value, "label": e.value.capitalize()} for e in cls]

class MovementType(str, Enum):
    """Types de mouvements ADT (Admission/Discharge/Transfer) selon IHE PAM"""
    ADT_A01 = "ADT^A01"  # Admission
    ADT_A02 = "ADT^A02"  # Transfert
    ADT_A03 = "ADT^A03"  # Sortie définitive
    ADT_A04 = "ADT^A04"  # Admission aux urgences / consultation externe
    ADT_A05 = "ADT^A05"  # Pré-admission
    ADT_A06 = "ADT^A06"  # Changement de statut ambulatoire vers hospitalisé
    ADT_A07 = "ADT^A07"  # Changement de statut hospitalisé vers ambulatoire
    ADT_A11 = "ADT^A11"  # Annulation d'admission
    ADT_A12 = "ADT^A12"  # Annulation de transfert
    ADT_A13 = "ADT^A13"  # Annulation de sortie
    ADT_A21 = "ADT^A21"  # Permission de sortie (patient absent temporairement)
    
    @classmethod
    def choices(cls) -> List[Dict[str, str]]:
        labels = {
            "ADT^A01": "Admission en hospitalisation",
            "ADT^A02": "Transfert du patient",
            "ADT^A03": "Sortie définitive",
            "ADT^A04": "Admission urgences / consultation externe",
            "ADT^A05": "Pré-admission",
            "ADT^A06": "Mutation vers consultation / urgence",
            "ADT^A07": "Retour de consultation",
            "ADT^A11": "Annulation d'admission",
            "ADT^A12": "Annulation de transfert",
            "ADT^A13": "Annulation de sortie",
            "ADT^A21": "Permission de sortie",
        }
        return [{"value": e.value, "label": labels.get(e.value, e.value)} for e in cls]

class MouvementStatus(str, Enum):
    """Statuts possibles d'un mouvement"""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    
    @classmethod
    def choices(cls) -> List[Dict[str, str]]:
        labels = {
            "pending": "En attente",
            "active": "En cours",
            "completed": "Terminé",
            "cancelled": "Annulé",
        }
        return [{"value": e.value, "label": labels.get(e.value, e.value.capitalize())} for e in cls]

# Configuration des champs par modèle
MODEL_FIELDS = {
    "Patient": {
        "required": ["family", "given"],
        "select": {},
        "help": {
            "family": "Nom de famille du patient",
            "given": "Prénom du patient",
            "external_id": "Identifiant externe (ex: IPP)",
            "birth_date": "Date de naissance (YYYYMMDD)",
            "gender": "Genre (M/F/O)",
        }
    },
    "Dossier": {
        "required": ["patient_id", "uf_responsabilite", "admit_time"],
        "select": {
            "admission_type": AdmissionType,
            "dossier_type": DossierType,
        },
        "help": {
            "patient_id": "ID du patient existant dans la base",
            "uf_responsabilite": "Unité fonctionnelle responsable du dossier",
            "admit_time": "Date et heure d'admission",
            "admission_type": "Type d'admission du patient",
            "dossier_type": "Type de dossier (hospitalisé/externe/urgence)",
        }
    },
    "SystemEndpoint": {
        "required": ["name", "kind", "role"],
        "select": {
            "kind": EndpointKind,
            "role": EndpointRole,
            "auth_kind": AuthKind,
        },
        "help": {
            "name": "Nom du système distant",
            "kind": "Type de protocole (MLLP/FHIR)",
            "role": "Rôle de l'endpoint (sender/receiver/both)",
            "host": "Hôte pour MLLP (ex: 0.0.0.0 pour receiver)",
            "port": "Port TCP pour MLLP",
            "base_url": "URL de base pour FHIR (ex: https://fhir.example.com/fhir)",
            "auth_kind": "Type d'authentification pour FHIR",
        }
    },
    "Mouvement": {
        "required": ["venue_id", "type", "when"],
        "select": {
            "type": MovementType,
            "status": MouvementStatus,
        },
        "help": {
            "venue_id": "Venue (séjour) concerné par le mouvement",
            "type": "Type de mouvement ADT selon la norme IHE PAM",
            "when": "Date et heure du mouvement",
            "location": "Localisation complète du patient",
            "from_location": "Localisation de départ (pour les transferts)",
            "to_location": "Localisation d'arrivée (pour les transferts)",
            "reason": "Motif ou raison du mouvement",
            "performer": "Nom de l'intervenant ayant effectué le mouvement",
            "status": "Statut actuel du mouvement",
            "note": "Commentaire ou remarque libre",
            "movement_type": "Type de mouvement (classification interne)",
            "movement_reason": "Raison détaillée du mouvement",
            "performer_role": "Rôle ou fonction de l'intervenant",
        }
    }
}

def get_field_config(model_name: str, field_name: str) -> Dict[str, Any]:
    """Retourne la configuration d'un champ pour un modèle donné."""
    if model_name not in MODEL_FIELDS:
        return {}
    
    config = {"required": field_name in MODEL_FIELDS[model_name]["required"]}
    
    if field_name in MODEL_FIELDS[model_name]["select"]:
        enum_class = MODEL_FIELDS[model_name]["select"][field_name]
        config["type"] = "select"
        config["options"] = enum_class.choices()
    
    if field_name in MODEL_FIELDS[model_name]["help"]:
        config["help"] = MODEL_FIELDS[model_name]["help"][field_name]
    
    return config