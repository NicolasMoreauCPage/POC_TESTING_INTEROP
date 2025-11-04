"""
Gestion de la fusion de patients (A40 - Merge Patient).

IHE PAM Profile - ITI-30/31:
Le message A40 permet de fusionner deux identités patients lorsqu'un doublon
est détecté. L'identité "source" (MRG) est retirée et toutes ses données
(dossiers, venues, mouvements, identifiants) sont rattachées à l'identité
"survivante" (PID).

Structure HL7:
- PID : Patient survivant (identité conservée)
- MRG : Patient source (identité à fusionner/retirer)
  - MRG-1 : Prior Patient Identifier List (identifiants à retirer)
  - MRG-7 : Prior Patient Name (nom précédent)

Traitement:
1. Identifier le patient survivant (via PID-3)
2. Identifier le(s) patient(s) source(s) (via MRG-1)
3. Ré-attribuer tous les dossiers/venues/mouvements du patient source au survivant
4. Fusionner les identifiants (marquer les anciens comme "old", copier vers survivant)
5. Désactiver/archiver le patient source
6. Logger l'opération de fusion
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

from sqlmodel import Session, select

from app.models import Patient, Dossier, Venue, Mouvement
from app.models_identifiers import Identifier
from app.services.identifier_manager import merge_identifiers, parse_hl7_cx_identifier

logger = logging.getLogger("patient_merge")


def _parse_mrg_segment(message: str) -> Optional[Dict]:
    """
    Parse le segment MRG (Merge Patient Information).
    
    MRG fields:
    - MRG-1: Prior Patient Identifier List (CX repeating)
    - MRG-2: Prior Alternate Patient ID (deprecated)
    - MRG-3: Prior Patient Account Number
    - MRG-4: Prior Patient ID
    - MRG-5: Prior Visit Number
    - MRG-6: Prior Alternate Visit ID
    - MRG-7: Prior Patient Name (XPN)
    
    Returns:
        Dict with "identifiers" (list of CX strings), "name", "account_number"
    """
    out = {
        "identifiers": [],
        "name": None,
        "account_number": None,
    }
    
    try:
        lines = re.split(r"\r|\n", message)
        mrg = next((l for l in lines if l.startswith("MRG")), None)
        if not mrg:
            return None
            
        parts = mrg.split("|")
        
        # MRG-1: Prior Patient Identifier List (repeating CX)
        if len(parts) > 1 and parts[1]:
            id_list = parts[1].split("~")
            out["identifiers"] = [cx for cx in id_list if cx]
        
        # MRG-3: Prior Patient Account Number
        if len(parts) > 3 and parts[3]:
            out["account_number"] = parts[3]
        
        # MRG-7: Prior Patient Name
        # Note: Some implementations place name at MRG-7, but in practice it can be at index 7-9
        # Check both MRG-7 (parts[7]) and further positions
        for idx in range(7, min(len(parts), 12)):
            if parts[idx] and "^" in parts[idx]:  # Name typically contains ^
                out["name"] = parts[idx]
                break
        
        return out
        
    except Exception as e:
        logger.error(f"Error parsing MRG segment: {str(e)}")
        return None


def _find_patient_by_identifiers(session: Session, cx_list: List[str]) -> Optional[Patient]:
    """
    Trouve un patient à partir d'une liste d'identifiants CX HL7.
    Teste d'abord les identifiants puis les champs direct (external_id, identifier).
    """
    if not cx_list:
        return None
    
    # 1. Recherche via la table Identifier
    for cx in cx_list:
        value, system, _, type_code = parse_hl7_cx_identifier(cx)
        if not value:
            continue
        
        # Chercher un identifiant actif correspondant
        identifier_obj = session.exec(
            select(Identifier)
            .where(Identifier.value == value)
            .where(Identifier.status == "active")
            .where(Identifier.patient_id.isnot(None))
        ).first()
        
        if identifier_obj and identifier_obj.patient_id:
            patient = session.get(Patient, identifier_obj.patient_id)
            if patient:
                return patient
    
    # 2. Fallback: recherche directe par external_id ou identifier (premier composant)
    for cx in cx_list:
        id_value = cx.split("^")[0] if "^" in cx else cx
        if not id_value:
            continue
        
        # Chercher par external_id
        patient = session.exec(
            select(Patient).where(Patient.external_id == id_value)
        ).first()
        if patient:
            return patient
        
        # Chercher par identifier
        patient = session.exec(
            select(Patient).where(Patient.identifier == id_value)
        ).first()
        if patient:
            return patient
    
    return None


async def handle_merge_patient(
    session: Session,
    trigger: str,
    pid_data: Dict,
    pv1_data: Dict,
    message: str
) -> Tuple[bool, Optional[str]]:
    """
    Gère un message A40 de fusion de patients.
    
    Args:
        session: Session de base de données
        trigger: "A40"
        pid_data: Données du patient survivant (segment PID)
        pv1_data: Données PV1 (optionnel pour A40)
        message: Message HL7 complet (pour parser MRG)
    
    Returns:
        (success, error_message)
    """
    try:
        # 1. Parser le segment MRG
        mrg_data = _parse_mrg_segment(message)
        if not mrg_data or not mrg_data["identifiers"]:
            return False, "MRG segment manquant ou invalide (MRG-1 requis)"
        
        logger.info(
            f"Processing A40 merge: {len(mrg_data['identifiers'])} source identifiers",
            extra={"mrg_identifiers": mrg_data["identifiers"]}
        )
        
        # 2. Identifier le patient survivant (PID)
        surviving_patient = None
        if pid_data.get("identifiers"):
            surviving_patient = _find_patient_by_identifiers(session, [cx for cx, _ in pid_data["identifiers"]])
        
        # Si non trouvé, créer le patient survivant (cas rare mais possible selon profil IHE)
        if not surviving_patient:
            from app.db import get_next_sequence
            surviving_patient = Patient(
                patient_seq=get_next_sequence(session, "patient"),
                identifier=pid_data.get("external_id") or f"MERGED-{get_next_sequence(session, 'patient')}",
                external_id=pid_data.get("external_id"),
                family=pid_data.get("family", ""),
                given=pid_data.get("given", ""),
                gender=pid_data.get("gender", "unknown"),
                birth_date=pid_data.get("birth_date"),
            )
            session.add(surviving_patient)
            session.flush()
            logger.info(f"Created surviving patient: {surviving_patient.identifier}")
        
        # 3. Identifier le(s) patient(s) source(s) (MRG)
        source_patients: List[Patient] = []
        source_patient = _find_patient_by_identifiers(session, mrg_data["identifiers"])
        if source_patient and source_patient.id != surviving_patient.id:
            source_patients.append(source_patient)
        
        if not source_patients:
            return False, "Patient source (MRG) introuvable ou identique au patient survivant"
        
        # 4. Pour chaque patient source, fusionner vers le survivant
        merged_count = 0
        for source_patient in source_patients:
            logger.info(
                f"Merging patient {source_patient.identifier} -> {surviving_patient.identifier}",
                extra={
                    "source_id": source_patient.id,
                    "surviving_id": surviving_patient.id
                }
            )
            
            # 4.1. Ré-attribuer tous les dossiers
            dossiers = session.exec(
                select(Dossier).where(Dossier.patient_id == source_patient.id)
            ).all()
            for dossier in dossiers:
                dossier.patient_id = surviving_patient.id
                session.add(dossier)
            
            logger.info(f"Reassigned {len(dossiers)} dossiers to surviving patient")
            
            # 4.2. Fusionner les identifiants
            # Marquer les identifiants du patient source comme "old"
            source_identifiers = session.exec(
                select(Identifier).where(Identifier.patient_id == source_patient.id)
            ).all()
            for ident in source_identifiers:
                ident.status = "old"
                ident.patient_id = surviving_patient.id  # Rattacher au survivant pour historique
                session.add(ident)
            
            logger.info(f"Marked {len(source_identifiers)} source identifiers as 'old'")
            
            # 4.3. Copier les identifiants manquants du source vers le survivant (si nécessaire)
            surviving_identifiers = session.exec(
                select(Identifier).where(Identifier.patient_id == surviving_patient.id)
            ).all()
            
            # Fusionner (garder les actifs du survivant, ajouter les "old" du source)
            merged_ids = merge_identifiers(
                existing=surviving_identifiers,
                new=source_identifiers,
                keep_inactive=True
            )
            
            # 4.4. Désactiver/archiver le patient source
            source_patient.family = f"[MERGED] {source_patient.family}"
            source_patient.identifier = f"ARCHIVED-{source_patient.identifier}"
            # On pourrait aussi ajouter un champ "merged_into_id" ou "is_merged" si le modèle le supporte
            session.add(source_patient)
            
            merged_count += 1
        
        # 5. Commit et retour
        session.flush()
        
        logger.info(
            f"A40 merge completed: {merged_count} patient(s) merged into {surviving_patient.identifier}",
            extra={
                "surviving_patient_id": surviving_patient.id,
                "merged_count": merged_count
            }
        )
        
        return True, None
        
    except Exception as e:
        logger.exception("Error processing A40 merge")
        return False, f"Merge failed: {str(e)}"
