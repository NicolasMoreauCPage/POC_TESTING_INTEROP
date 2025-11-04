from typing import List, Dict, Set, Tuple
from sqlmodel import Session, select
from app.models import DossierType, Dossier, Mouvement, Venue

# Définition des mouvements autorisés par type de dossier et leurs transitions possibles
ALLOWED_MOVEMENTS_BY_TYPE = {
    DossierType.HOSPITALISE: {
        "A01",  # Admission
        "A02",  # Transfert
        "A03",  # Sortie
        "A06",  # Changement de classe
        "A07",  # Changement de classe
        "A21",  # Absence temporaire
        "A22",  # Retour d'absence
    },
    DossierType.EXTERNE: {
        "A04",  # Inscription
        "A06",  # Changement de classe
        "A07",  # Changement de classe
    },
    DossierType.URGENCE: {
        "A04",  # Arrivée aux urgences
        "A03",  # Sortie des urgences
        "A06",  # Passage en hospitalisation
    }
}

# Transitions autorisées entre types de dossier
ALLOWED_TYPE_TRANSITIONS = {
    DossierType.URGENCE: {
        DossierType.HOSPITALISE: {"A04"}  # Passage des urgences vers l'hospitalisation est toujours permis
    },
    DossierType.HOSPITALISE: {
        DossierType.EXTERNE: set()  # Pas de mouvements spécifiques requis
    },
    DossierType.EXTERNE: {
        DossierType.HOSPITALISE: set()  # Pas de mouvements spécifiques requis
    }
}

def check_movements_compatibility(
    session: Session,
    dossier: Dossier,
    new_type: DossierType
) -> Tuple[bool, List[str]]:
    """
    Vérifie si les mouvements existants sont compatibles avec le nouveau type de dossier.
    
    Returns:
        Tuple[bool, List[str]]: (compatible, liste des incompatibilités)
    """
    incompatibilities = []
    
    # Récupérer toutes les venues du dossier avec leurs mouvements
    stmt = select(Venue).where(Venue.dossier_id == dossier.id)
    venues = session.exec(stmt).all()
    
    # Vérifier si c'est une transition spéciale autorisée
    if dossier.dossier_type in ALLOWED_TYPE_TRANSITIONS:
        transition_rules = ALLOWED_TYPE_TRANSITIONS[dossier.dossier_type]
        if new_type in transition_rules:
            required_movements = transition_rules[new_type]
            if required_movements:
                # Vérifier que les mouvements requis sont présents
                found_movements = set()
                for venue in venues:
                    for mvt in venue.mouvements:
                        event_type = mvt.type.split("^")[1] if "^" in mvt.type else mvt.type
                        found_movements.add(event_type)
                
                if required_movements.issubset(found_movements):
                    # Les mouvements requis sont présents, la transition est autorisée
                    return True, []
                else:
                    missing = required_movements - found_movements
                    incompatibilities.append(
                        f"La transition de {dossier.dossier_type.value} vers {new_type.value} "
                        f"requiert les mouvements : {', '.join(missing)}"
                    )
    
    # Dans tous les autres cas, vérifier que les mouvements existants sont compatibles
    allowed_movements = ALLOWED_MOVEMENTS_BY_TYPE[new_type]
    
    for venue in venues:
        for mvt in venue.mouvements:
            event_type = mvt.type.split("^")[1] if "^" in mvt.type else mvt.type
            if event_type not in allowed_movements:
                incompatibilities.append(
                    f"Mouvement {mvt.mouvement_seq} (type {mvt.type}) "
                    f"non compatible avec le type {new_type.value}"
                )
    
    return len(incompatibilities) == 0, incompatibilities
    
    return len(incompatibilities) == 0, incompatibilities

def validate_dossier_type_change(
    session: Session,
    dossier: Dossier,
    new_type: DossierType
) -> Tuple[bool, List[str]]:
    """
    Valide le changement de type de dossier et retourne les avertissements.
    
    Returns:
        Tuple[bool, List[str]]: (changement possible, liste des avertissements)
    """
    warnings = []
    blocking = False
    
    # Si le type ne change pas, pas besoin de vérification
    if dossier.dossier_type == new_type:
        return True, []
    
    # Vérifier la compatibilité des mouvements
    compatible, incompatibilities = check_movements_compatibility(session, dossier, new_type)
    if not compatible:
        blocking = True
        warnings.extend(incompatibilities)
        warnings.append("Le changement de type est bloqué en raison des mouvements incompatibles.")
    
    return not blocking, warnings