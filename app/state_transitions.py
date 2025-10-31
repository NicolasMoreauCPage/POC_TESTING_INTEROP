# Définition des transitions valides pour les états IHE PAM
VALID_TRANSITIONS = {
    "Pas de venue courante": ["A05", "A38"],
    "Pré-admis consult.ext.": ["A04", "A11"],
    "Pré-admis hospit.": ["A01", "A11"],
    "Hospitalisé": ["A03", "A13", "A21", "A52", "A53"],
    "Absence temporaire": ["A22", "A52"],
    "Consultant externe": ["A06", "A07"],
    # Notes spécifiques du tableau
    "A11": ["A01", "A04", "A05"],  # Note 1 : A11 annule tout sauf pré-admission
    "Z80": ["A01", "A04", "A05"],  # Note 2 : Z80 nécessite une hospitalisation préalable
    "A38": ["A11"],  # Note 3 : A38 ne peut pas suivre A11
}

def is_valid_transition(current_state, event_code):
    """
    Vérifie si une transition est valide pour un état donné et un code d'événement.
    """
    return event_code in VALID_TRANSITIONS.get(current_state, [])