"""
Services pour la gestion des profils IHE PIX/PDQ et FHIR PIXm/PDQm.
Implémente :
- PIX : Cross-referencing des identifiants patients entre domaines
- PDQ : Recherche démographique de patients
- PIXm/PDQm : Équivalents FHIR des profils ci-dessus
"""
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging
from sqlmodel import Session, select

from app.models import Patient
from app.models_identifiers import Identifier, IdentifierType
from app.services.identifier_manager import (
    create_identifier_from_hl7,
    create_fhir_identifier,
    get_main_identifier
)

logger = logging.getLogger(__name__)

class PIXPDQManager:
    """Gestionnaire central des services PIX/PDQ."""
    
    def handle_pix_query(self, msg: str, session: Session) -> Tuple[bool, Optional[str], Optional[List[Identifier]]]:
        """
        Traite une requête PIX (QBP^Q23).
        
        Args:
            msg: Message HL7v2 QPB^Q23
            session: Session SQLModel active
            
        Returns:
            (success, error_message, identifiers_found)
        """
        try:
            # Parser QPD (Query Parameter Definition)
            qpd = self._parse_qpd(msg)
            if not qpd.get("patient_id"):
                return False, "Missing QPD-3 (patient identifier)", None
                
            # Rechercher le patient
            patient = self._find_patient_by_identifier(qpd["patient_id"], session)
            if not patient:
                return False, "Patient not found", None
                
            # Récupérer tous les identifiants
            identifiers = session.exec(
                select(Identifier)
                .where(Identifier.patient_id == patient.id)
            ).all()
            
            return True, None, identifiers
            
        except Exception as e:
            logger.exception("PIX query error")
            return False, str(e), None
            
    def handle_pdq_query(self, msg: str, session: Session) -> Tuple[bool, Optional[str], Optional[List[Patient]]]:
        """
        Traite une requête PDQ (QBP^Q22).
        
        Args:
            msg: Message HL7v2 QBP^Q22
            session: Session SQLModel active
            
        Returns:
            (success, error_message, patients_found)
        """
        try:
            # Parser les critères de recherche du QPD
            qpd = self._parse_qpd(msg)
            if not qpd:
                return False, "No search criteria in QPD", None
                
            # Construire la requête
            query = select(Patient)
            
            if qpd.get("family"):
                query = query.where(Patient.family.ilike(f"%{qpd['family']}%"))
            if qpd.get("given"):
                query = query.where(Patient.given.ilike(f"%{qpd['given']}%"))
            if qpd.get("birth_date"):
                query = query.where(Patient.birth_date == qpd["birth_date"])
                
            patients = session.exec(query).all()
            return True, None, patients
            
        except Exception as e:
            logger.exception("PDQ query error")
            return False, str(e), None

    def handle_pixm_query(self, params: Dict, session: Session) -> Dict:
        """
        Traite une requête PIXm (/$ihe-pix).
        Implémente le profil IHE PIXm.
        
        Args:
            params: Paramètres de la requête FHIR
            session: Session SQLModel active
            
        Returns:
            Bundle FHIR avec les identifiants trouvés
        """
        try:
            sourceIdentifier = params.get("sourceIdentifier")
            if not sourceIdentifier:
                raise ValueError("Missing required parameter: sourceIdentifier")
                
            # Rechercher le patient
            patient = self._find_patient_by_identifier(sourceIdentifier, session)
            if not patient:
                return {
                    "resourceType": "Bundle",
                    "type": "searchset",
                    "total": 0,
                    "entry": []
                }
                
            # Récupérer tous les identifiants
            identifiers = session.exec(
                select(Identifier)
                .where(Identifier.patient_id == patient.id)
            ).all()
            
            # Construire le Bundle de réponse
            entries = []
            for identifier in identifiers:
                param = create_fhir_identifier(identifier)
                entries.append({
                    "fullUrl": f"urn:uuid:{identifier.id}",
                    "resource": {
                        "resourceType": "Parameters",
                        "parameter": [{
                            "name": "targetIdentifier",
                            "valueIdentifier": param
                        }]
                    }
                })
                
            return {
                "resourceType": "Bundle",
                "type": "searchset",
                "total": len(entries),
                "entry": entries
            }
            
        except Exception as e:
            logger.exception("PIXm query error")
            raise ValueError(str(e))

    def handle_pdqm_query(self, params: Dict, session: Session) -> Dict:
        """
        Traite une requête PDQm (recherche Patient FHIR).
        Implémente le profil IHE PDQm.
        
        Args:
            params: Paramètres de recherche FHIR
            session: Session SQLModel active
            
        Returns:
            Bundle FHIR avec les patients trouvés
        """
        try:
            # Construire la requête
            query = select(Patient)
            
            if params.get("family"):
                query = query.where(Patient.family.ilike(f"%{params['family']}%"))
            if params.get("given"):
                query = query.where(Patient.given.ilike(f"%{params['given']}%"))
            if params.get("birthdate"):
                query = query.where(Patient.birth_date == params["birthdate"])
            if params.get("gender"):
                query = query.where(Patient.gender == params["gender"])
            if params.get("identifier"):
                # Format attendu: system|value
                system, value = params["identifier"].split("|")
                query = query.join(Identifier).where(
                    (Identifier.system == system) & (Identifier.value == value)
                )
                
            patients = session.exec(query).all()
            
            # Construire le Bundle de réponse
            entries = []
            for patient in patients:
                resource = {
                    "resourceType": "Patient",
                    "id": f"pat-{patient.id}",
                    "identifier": [],
                    "name": [{
                        "family": patient.family,
                        "given": [patient.given] if patient.given else []
                    }],
                    "birthDate": patient.birth_date,
                    "gender": patient.gender
                }
                
                # Ajouter les identifiants
                identifiers = session.exec(
                    select(Identifier)
                    .where(Identifier.patient_id == patient.id)
                ).all()
                
                for identifier in identifiers:
                    resource["identifier"].append(
                        create_fhir_identifier(identifier)
                    )
                    
                entries.append({
                    "fullUrl": f"urn:uuid:pat-{patient.id}",
                    "resource": resource
                })
                
            return {
                "resourceType": "Bundle",
                "type": "searchset",
                "total": len(entries),
                "entry": entries
            }
            
        except Exception as e:
            logger.exception("PDQm query error")
            raise ValueError(str(e))

    def _parse_qpd(self, msg: str) -> Dict:
        """Parse le segment QPD pour extraire les paramètres de recherche."""
        out = {}
        try:
            lines = msg.split("\r")
            qpd = next((l for l in lines if l.startswith("QPD")), None)
            if not qpd:
                return out
                
            parts = qpd.split("|")
            
            # QPD-3 : Patient Identifier
            if len(parts) > 3 and parts[3]:
                out["patient_id"] = parts[3]
                
            # QPD-3 peut contenir plusieurs critères séparés par ~ (IHE PDQ)
            if len(parts) > 3 and parts[3]:
                criteria = parts[3].split("~")
                for crit in criteria:
                    # Format: @PID.5.1^DUPONT ou ID^^^System
                    if crit.startswith("@PID"):
                        # IHE PDQ demo query format
                        comp = crit.split("^")
                        if len(comp) >= 2:
                            field = comp[0].lower()
                            value = comp[1]
                            # @PID.5.1 -> family, @PID.7 -> birth_date
                            if ".5.1" in field:
                                out["family"] = value
                            elif ".7" in field:
                                out["birth_date"] = value
                    else:
                        # Standard CX identifier
                        out["patient_id"] = crit
                        
        except Exception as e:
            logger.error(f"QPD parsing error: {e}")
            
        return out

    def _find_patient_by_identifier(self, cx_value: str, session: Session) -> Optional[Patient]:
        """Recherche un patient par son identifiant HL7 CX."""
        try:
            identifier = create_identifier_from_hl7(cx_value, "patient", 0)
            result = session.exec(
                select(Patient)
                .join(Identifier)
                .where(
                    (Identifier.system == identifier.system) &
                    (Identifier.value == identifier.value)
                )
            ).first()
            return result
        except Exception:
            return None