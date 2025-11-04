"""
Routeur de messages pour la gestion des triggers events IHE PAM
"""
from typing import Dict, Tuple, Optional
import logging

from sqlmodel import Session

from app.services.pam import (
    handle_admission_message,
    handle_transfer_message,
    handle_discharge_message,
    handle_leave_message,
    handle_doctor_message
)
from app.services.patient_merge import handle_merge_patient

logger = logging.getLogger(__name__)

class IHEMessageRouter:
    """Route les messages selon leur trigger event"""
    
    # Mapping des triggers vers les handlers
    HANDLERS = {
        # Admission/Enregistrement/Pré-admission
        "A01": ("admission", handle_admission_message),
        "A11": ("admission", handle_admission_message),
        "A04": ("admission", handle_admission_message),
        "A23": ("admission", handle_admission_message),
        "A05": ("admission", handle_admission_message),
        "A38": ("admission", handle_admission_message),
        
        # Changements de type
        "A06": ("admission", handle_admission_message),
        "A07": ("admission", handle_admission_message),
    "A31": ("admission", handle_admission_message),
    # Add person / demographic updates (A28/A29) -> map to admission handler
    "A28": ("admission", handle_admission_message),
    "A29": ("admission", handle_admission_message),
        
        # Transferts
        "A02": ("transfer", handle_transfer_message),
        "A12": ("transfer", handle_transfer_message),
        
        # Permissions
        "A21": ("leave", handle_leave_message),
        "A52": ("leave", handle_leave_message),
        "A22": ("leave", handle_leave_message),
        "A53": ("leave", handle_leave_message),
        
        # Sorties
        "A03": ("discharge", handle_discharge_message),
        "A13": ("discharge", handle_discharge_message),
        
        # Changement médecin
        "A54": ("doctor", handle_doctor_message),
        "A55": ("doctor", handle_doctor_message),
        
        # Fusion de patients
        "A40": ("merge", None),  # Handler spécial (nécessite le message complet)
    }
    
    @classmethod
    async def route_message(
        cls,
        session: Session,
        trigger: str,
        pid_data: Dict,
        pv1_data: Dict,
        message: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Route un message vers son handler approprié
        
        Args:
            session: Session base de données
            trigger: Code trigger event (A01, A02, etc)
            pid_data: Données du segment PID parsé
            pv1_data: Données du segment PV1 parsé
            message: Message HL7 complet (optionnel, requis pour A40, A11, A12, A13)
            
        Returns:
            Tuple[bool, Optional[str]]: (succès, message d'erreur)
        """
        try:
            # Trouver le handler approprié
            if trigger not in cls.HANDLERS:
                return False, f"Trigger event non supporté: {trigger}"
                
            category, handler = cls.HANDLERS[trigger]
            
            # Logger l'événement
            logger.info(
                f"Routing {trigger} message to {category} handler"
            )
            
            # Cas spécial: A40 nécessite le message complet pour parser MRG
            if trigger == "A40":
                if not message:
                    return False, "A40 merge requires full message to parse MRG segment"
                return await handle_merge_patient(session, trigger, pid_data, pv1_data, message)
            
            # Tous les handlers IHE PAM reçoivent le message complet pour parser ZBE
            # (segment ZBE TOUJOURS présent dans les messages IHE PAM mouvements)
            return await handler(session, trigger, pid_data, pv1_data, message)
            
        except Exception as e:
            logger.error(f"Erreur routage message: {str(e)}")
            return False, str(e)