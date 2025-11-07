"""
Gestion des mises à jour Z99 selon la spécification IHE PAM France
"""
from typing import Dict, Tuple, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class Z99EntityType(str, Enum):
    PATIENT = "Patient"
    VENUE = "Venue"
    MOUVEMENT = "Mouvement"
    DOSSIER = "Dossier"

class Z99Field:
    def __init__(self, name: str, required: bool = False, max_length: Optional[int] = None):
        self.name = name
        self.required = required
        self.max_length = max_length

class Z99EntitySpec:
    """Spécification des champs modifiables par Z99 pour chaque entité"""
    SPECS = {
        Z99EntityType.PATIENT: {
            "nom": Z99Field("nom", True, 50),
            "prenom": Z99Field("prenom", False, 30),
            "date_naissance": Z99Field("date_naissance"),
            "sexe": Z99Field("sexe"),
            "adresse": Z99Field("adresse"),
        },
        Z99EntityType.VENUE: {
            "date_entree": Z99Field("date_entree", True),
            "mode_entree": Z99Field("mode_entree"),
            "type_venue": Z99Field("type_venue"),
            "uf_medicale": Z99Field("uf_medicale"),
            "uf_soins": Z99Field("uf_soins"),
            "uf_medicale": Z99Field("uf_medicale"),
        },
        Z99EntityType.MOUVEMENT: {
            "date_mouvement": Z99Field("date_mouvement", True),
            "type": Z99Field("type"),
            "uf_medicale": Z99Field("uf_medicale"),
            "uf_soins": Z99Field("uf_soins"),
            "uf_medicale": Z99Field("uf_medicale"),
        },
        Z99EntityType.DOSSIER: {
            "motif": Z99Field("motif"),
            "type_sejour": Z99Field("type_sejour"),
            "status": Z99Field("status"),
        }
    }

def parse_z99(message: str) -> Tuple[Z99EntityType, str, Dict[str, str]]:
    """
    Parse un segment Z99 selon la spec IHE PAM France
    Format: Z99|type_entite|id_entite|champ1|valeur1|champ2|valeur2...
    
    Returns:
        Tuple[type_entite, id_entite, dict_modifications]
    """
    try:
        parts = message.split("|")
        if len(parts) < 4 or parts[0] != "Z99":
            raise ValueError("Format Z99 invalide")
            
        entity_type = Z99EntityType(parts[1])
        entity_id = parts[2]
        
        # Parser les paires champ/valeur
        updates = {}
        for i in range(3, len(parts)-1, 2):
            field = parts[i]
            value = parts[i+1] if i+1 < len(parts) else None
            
            # Vérifier que le champ est autorisé
            if field not in Z99EntitySpec.SPECS[entity_type]:
                logger.warning(f"Champ Z99 non autorisé ignoré: {field}")
                continue
                
            # Vérifier la longueur si spécifiée
            spec = Z99EntitySpec.SPECS[entity_type][field]
            if spec.max_length and value and len(value) > spec.max_length:
                logger.warning(f"Valeur trop longue pour {field}, tronquée")
                value = value[:spec.max_length]
                
            updates[field] = value
            
        return entity_type, entity_id, updates
        
    except Exception as e:
        logger.error(f"Erreur parsing Z99: {str(e)}")
        raise ValueError(f"Format Z99 invalide: {str(e)}")
        
def validate_z99_updates(entity_type: Z99EntityType, updates: Dict[str, str]) -> bool:
    """Valide les mises à jour Z99 selon les règles métier"""
    spec = Z99EntitySpec.SPECS[entity_type]
    
    # Vérifier les champs requis
    required_fields = {f for f, s in spec.items() if s.required}
    if updates.keys() & required_fields != required_fields:
        missing = required_fields - updates.keys()
        logger.error(f"Champs requis manquants: {missing}")
        return False
        
    return True