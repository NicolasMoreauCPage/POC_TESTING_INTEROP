from typing import Dict, List, Optional, Tuple
from sqlmodel import Session
from datetime import datetime
import importlib
import logging
import re

from app.models import Dossier, Patient, Venue, Mouvement
from app.db import get_next_sequence
from app.services.identifier_manager import create_identifier_from_hl7

logger = logging.getLogger(__name__)

_adapter_module = None

try:
    _adapter_module = importlib.import_module("adapters.hl7_pam_fr")
except ModuleNotFoundError:
    build_message_for_movement = None  # pragma: no cover
else:
    build_message_for_movement = getattr(_adapter_module, "build_message_for_movement", None)

MOVEMENT_KIND_BY_TRIGGER = {
    "A01": "admission",
    "A04": "registration",
    "A05": "preadmission",
    "A06": "class-change",
    "A07": "class-change",
    "A11": "admission-cancel",
    "A23": "registration-cancel",
    "A28": "update",
    "A29": "update",
    "A31": "update",
    "A38": "preadmission-cancel",
    "A02": "transfer",
    "A12": "transfer-cancel",
    "A03": "discharge",
    "A13": "discharge-cancel",
    "A21": "leave-out",
    "A52": "leave-out",
    "A22": "leave-return",
    "A53": "leave-return",
    "A54": "doctor-change",
    "A55": "doctor-change-cancel",
}

MOVEMENT_STATUS_BY_TRIGGER = {
    "A05": "planned",
    "A11": "cancelled",
    "A23": "cancelled",
    "A38": "cancelled",
    "A12": "cancelled",
    "A13": "cancelled",
    "A21": "leave",
    "A52": "leave",
    "A22": "completed",
    "A53": "completed",
    "A54": "completed",
    "A55": "cancelled",
}


def _parse_zbe_segment(message: str) -> Optional[Dict]:
    """
    Parse le segment ZBE (mouvement patient - spécifique IHE PAM France).
    
    ZBE fields (selon IHE PAM France):
    - ZBE-1: Identifiant du mouvement (format: ID^NAMESPACE^OID^ISO ou simple ID)
    - ZBE-2: Date/heure du mouvement (HL7 timestamp: YYYYMMDDHHmmss)
    - ZBE-3: Action (généralement vide)
    - ZBE-4: Type d'action (INSERT / UPDATE / CANCEL)
    - ZBE-5: Indicateur annulation (Y/N)
    - ZBE-6: Événement d'origine (ex: "A01" pour un A11 qui annule un A01)
    - ZBE-7: UF médical responsable (format complexe: ^^^^^^UF^^^CODE_UF, code en position 10)
    - ZBE-8: Vide
    - ZBE-9: Mode de traitement (HMS, etc.)
    
    Returns:
        Dict with movement_id, movement_datetime, action_type, cancel_flag, origin_event, uf_responsable
    """
    out = {
        "movement_id": None,
        "movement_datetime": None,
        "action_type": None,
        "cancel_flag": None,
        "origin_event": None,
        "uf_responsable": None,
        "mode_traitement": None,
    }
    
    try:
        lines = re.split(r"\r|\n", message)
        zbe = next((l for l in lines if l.startswith("ZBE")), None)
        if not zbe:
            return None
            
        parts = zbe.split("|")
        
        # ZBE-1: Identifiant du mouvement (format: ID^NAMESPACE^OID^ISO)
        if len(parts) > 1 and parts[1]:
            movement_id_field = parts[1].strip()
            # Extraire juste l'ID (composant 1)
            out["movement_id"] = movement_id_field.split("^")[0] if "^" in movement_id_field else movement_id_field
        
        # ZBE-2: Date/heure du mouvement
        if len(parts) > 2 and parts[2]:
            out["movement_datetime"] = parts[2].strip()
        
        # ZBE-3: Action (généralement vide, on skip)
        
        # ZBE-4: Type d'action (INSERT, UPDATE, CANCEL)
        if len(parts) > 4 and parts[4]:
            out["action_type"] = parts[4].strip()
        
        # ZBE-5: Indicateur annulation (Y/N)
        if len(parts) > 5 and parts[5]:
            out["cancel_flag"] = parts[5].strip()
        
        # ZBE-6: Événement d'origine
        if len(parts) > 6 and parts[6]:
            out["origin_event"] = parts[6].strip()
        
        # ZBE-7: UF responsable (format: ^^^^^^UF^^^CODE_UF)
        # Le code UF est en position 10 (composant 10 du champ composite)
        if len(parts) > 7 and parts[7]:
            uf_field = parts[7].strip()
            uf_components = uf_field.split("^")
            if len(uf_components) >= 10 and uf_components[9]:
                out["uf_responsable"] = uf_components[9]
        
        # ZBE-8: Vide (on skip)
        
        # ZBE-9: Mode de traitement
        if len(parts) > 9 and parts[9]:
            out["mode_traitement"] = parts[9].strip()
        
        return out if out["movement_id"] else None
        
    except Exception as e:
        logger.warning(f"Failed to parse ZBE segment: {e}")
        return None


def generate_pam_messages_for_dossier(dossier: Dossier) -> List[str]:
    patient: Patient = dossier.patient
    venues: List[Venue] = sorted(dossier.venues, key=lambda v: v.start_time or "")
    messages: List[str] = []

    for v in venues:
        mouvements: List[Mouvement] = sorted(v.mouvements, key=lambda m: m.when)
        for m in mouvements:
            if build_message_for_movement:
                messages.append(build_message_for_movement(dossier=dossier, venue=v, movement=m, patient=patient))
            else:
                # Choose a stable primary patient identifier (prefer patient.identifier, fallback external_id, then patient_seq)
                primary_id = patient.identifier or patient.external_id or (f"PSEQ{patient.patient_seq}" if patient.patient_seq is not None else f"PID{patient.id}")
                # Emit PID-3 as CX with system tag for source context + type PI
                pid_cx = f"{primary_id}^^^SRC-PAM&1.2.250.1.211.99.1&ISO^PI"
                msh = f"MSH|^~\\&|POC|POC|DST|DST|{m.when:%Y%m%d%H%M%S}||{m.type}|{dossier.dossier_seq}|P|2.5"
                pid = f"PID|||{pid_cx}||{patient.family}^{patient.given}||{patient.birth_date}|{patient.gender}"
                pv1_loc = m.location or v.code or "UNKNOWN"
                pv1 = f"PV1||I|{pv1_loc}|||^^^^^{v.uf_responsabilite}"
                messages.append("\r".join([msh, pid, pv1]))
    return messages


async def _handle_cancel_admission(
    session: Session,
    trigger: str,
    pid_data: dict,
    pv1_data: dict,
    message: Optional[str]
) -> Tuple[bool, Optional[str]]:
    """
    Gère les annulations d'admission (A11, A23, A38).
    
    Parse le segment ZBE-1 pour identifier le mouvement à annuler,
    puis crée un nouveau mouvement d'annulation.
    """
    try:
        # Parser ZBE pour obtenir le movement_id à annuler
        zbe_data = _parse_zbe_segment(message) if message else None
        
        if not zbe_data or not zbe_data.get("movement_id"):
            logger.warning(f"[pam][cancel] {trigger}: No ZBE segment or movement_id found, fallback to last movement")
            # Fallback: chercher le dernier mouvement du patient
            identifiers = pid_data.get("identifiers", [])
            if not identifiers:
                return False, "No patient identifier found"
            identifier = identifiers[0][0].split("^")[0]
            
            from sqlmodel import select
            patient = session.exec(select(Patient).where(Patient.identifier == identifier)).first()
            if not patient:
                return False, "Patient not found"
            
            dossier = session.exec(select(Dossier).where(Dossier.patient_id == patient.id)).first()
            if not dossier:
                return False, "Dossier not found"
            
            venue = session.exec(
                select(Venue)
                .where(Venue.dossier_id == dossier.id)
                .order_by(Venue.venue_seq.desc())
            ).first()
            if not venue:
                return False, "Venue not found"
            
            # Trouver le dernier mouvement d'admission
            original_mouvement = session.exec(
                select(Mouvement)
                .where(Mouvement.venue_id == venue.id)
                .where(Mouvement.movement_type.in_(["admission", "preadmission", "registration"]))
                .order_by(Mouvement.when.desc())
            ).first()
        else:
            # Utiliser ZBE-1 pour trouver le mouvement spécifique
            movement_id_str = zbe_data["movement_id"]
            logger.info(f"[pam][cancel] {trigger}: Looking for movement with seq={movement_id_str}")
            
            from sqlmodel import select
            original_mouvement = session.exec(
                select(Mouvement)
                .where(Mouvement.mouvement_seq == int(movement_id_str))
            ).first()
            
            if not original_mouvement:
                logger.warning(f"[pam][cancel] {trigger}: Movement seq={movement_id_str} not found, trying fallback by patient")
                # Fallback: chercher le dernier mouvement du patient
                identifiers = pid_data.get("identifiers", [])
                if not identifiers:
                    return False, f"Movement with seq={movement_id_str} not found (no patient identifier for fallback)"
                identifier = identifiers[0][0].split("^")[0]
                
                patient = session.exec(select(Patient).where(Patient.identifier == identifier)).first()
                if not patient:
                    return False, f"Movement with seq={movement_id_str} not found (patient not found for fallback)"
                
                dossier = session.exec(select(Dossier).where(Dossier.patient_id == patient.id)).first()
                if not dossier:
                    return False, f"Movement with seq={movement_id_str} not found (dossier not found for fallback)"
                
                venue = session.exec(
                    select(Venue)
                    .where(Venue.dossier_id == dossier.id)
                    .order_by(Venue.venue_seq.desc())
                ).first()
                if not venue:
                    return False, f"Movement with seq={movement_id_str} not found (venue not found for fallback)"
                
                # Trouver le dernier mouvement d'admission
                original_mouvement = session.exec(
                    select(Mouvement)
                    .where(Mouvement.venue_id == venue.id)
                    .where(Mouvement.movement_type.in_(["admission", "preadmission", "registration"]))
                    .order_by(Mouvement.when.desc())
                ).first()
                
                if not original_mouvement:
                    return False, f"Movement with seq={movement_id_str} not found (no admission movement for fallback)"
            else:
                venue = original_mouvement.venue
        
        if not original_mouvement:
            return False, "No admission movement found to cancel"
        
        # Créer un nouveau mouvement d'annulation
        m_seq = get_next_sequence(session, "mouvement")
        cancel_mouvement = Mouvement(
            mouvement_seq=m_seq,
            venue_id=venue.id,
            type=f"ADT^{trigger}",
            when=datetime.utcnow(),
            status=MOVEMENT_STATUS_BY_TRIGGER.get(trigger, "cancelled"),
            movement_type=MOVEMENT_KIND_BY_TRIGGER.get(trigger, "admission-cancel"),
            trigger_event=trigger,  # Pour validation des transitions IHE PAM
            location=original_mouvement.location,
            from_location=original_mouvement.from_location,
            to_location=original_mouvement.to_location,
        )
        session.add(cancel_mouvement)
        
        # Mettre à jour le statut du mouvement original
        original_mouvement.status = "cancelled"
        session.add(original_mouvement)
        
        # Mettre à jour le statut de la venue
        venue.operational_status = "cancelled"
        session.add(venue)
        
        session.flush()
        
        logger.info(
            f"[pam][cancel] {trigger}: Created cancel movement seq={cancel_mouvement.mouvement_seq} "
            f"cancelling original movement seq={original_mouvement.mouvement_seq}"
        )
        
        return True, None
        
    except Exception as e:
        logger.error(f"[pam][cancel] {trigger} failed: {e}", exc_info=True)
        return False, str(e)


async def _handle_cancel_discharge(
    session: Session,
    trigger: str,
    pid_data: dict,
    pv1_data: dict,
    message: Optional[str]
) -> Tuple[bool, Optional[str]]:
    """
    Gère l'annulation de sortie (A13).
    
    Parse le segment ZBE-1 pour identifier le mouvement à annuler,
    puis crée un nouveau mouvement d'annulation.
    """
    try:
        # Parser ZBE pour obtenir le movement_id à annuler
        zbe_data = _parse_zbe_segment(message) if message else None
        
        if not zbe_data or not zbe_data.get("movement_id"):
            logger.warning(f"[pam][cancel-discharge] No ZBE segment, fallback to last discharge")
            # Fallback: chercher la dernière sortie
            identifiers = pid_data.get("identifiers", [])
            if not identifiers:
                return False, "No patient identifier found"
            identifier = identifiers[0][0].split("^")[0]
            
            from sqlmodel import select
            patient = session.exec(select(Patient).where(Patient.identifier == identifier)).first()
            if not patient:
                return False, "Patient not found"
            
            dossier = session.exec(select(Dossier).where(Dossier.patient_id == patient.id)).first()
            if not dossier:
                return False, "Dossier not found"
            
            venue = session.exec(
                select(Venue)
                .where(Venue.dossier_id == dossier.id)
                .order_by(Venue.venue_seq.desc())
            ).first()
            if not venue:
                return False, "Venue not found"
            
            # Trouver la dernière sortie
            original_mouvement = session.exec(
                select(Mouvement)
                .where(Mouvement.venue_id == venue.id, Mouvement.type == "ADT^A03")
                .order_by(Mouvement.when.desc())
            ).first()
        else:
            # Utiliser ZBE-1
            movement_id_str = zbe_data["movement_id"]
            logger.info(f"[pam][cancel-discharge] Looking for movement seq={movement_id_str}")
            
            from sqlmodel import select
            original_mouvement = session.exec(
                select(Mouvement)
                .where(Mouvement.mouvement_seq == int(movement_id_str))
            ).first()
            
            if not original_mouvement:
                logger.warning(f"[pam][cancel-discharge]: Movement seq={movement_id_str} not found, trying fallback")
                # Fallback: chercher la dernière sortie
                identifiers = pid_data.get("identifiers", [])
                if not identifiers:
                    return False, f"Movement with seq={movement_id_str} not found (no patient identifier for fallback)"
                identifier = identifiers[0][0].split("^")[0]
                
                patient = session.exec(select(Patient).where(Patient.identifier == identifier)).first()
                if not patient:
                    return False, f"Movement with seq={movement_id_str} not found (patient not found for fallback)"
                
                dossier = session.exec(select(Dossier).where(Dossier.patient_id == patient.id)).first()
                if not dossier:
                    return False, f"Movement with seq={movement_id_str} not found (dossier not found for fallback)"
                
                venue = session.exec(
                    select(Venue)
                    .where(Venue.dossier_id == dossier.id)
                    .order_by(Venue.venue_seq.desc())
                ).first()
                if not venue:
                    return False, f"Movement with seq={movement_id_str} not found (venue not found for fallback)"
                
                # Trouver la dernière sortie
                original_mouvement = session.exec(
                    select(Mouvement)
                    .where(Mouvement.venue_id == venue.id, Mouvement.type == "ADT^A03")
                    .order_by(Mouvement.when.desc())
                ).first()
                
                if not original_mouvement:
                    return False, f"Movement with seq={movement_id_str} not found (no discharge movement for fallback)"
            else:
                venue = original_mouvement.venue
        
        if not original_mouvement:
            return False, "No discharge movement found to cancel"
        
        # Déterminer la date du mouvement d'annulation : priorité ZBE-2 puis now
        cancel_datetime = datetime.utcnow()
        if zbe_data and zbe_data.get("movement_datetime"):
            try:
                dt_str = zbe_data["movement_datetime"]
                cancel_datetime = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
            except Exception as e:
                logger.warning(f"[pam][cancel-discharge] Failed to parse ZBE-2 datetime '{dt_str}': {e}")

        # Créer mouvement d'annulation
        m_seq = get_next_sequence(session, "mouvement")
        cancel_mouvement = Mouvement(
            mouvement_seq=m_seq,
            venue_id=venue.id,
            type=f"ADT^{trigger}",
            when=cancel_datetime,
            status="cancelled",
            movement_type="discharge-cancel",
            trigger_event=trigger,  # Pour validation des transitions IHE PAM
            location=original_mouvement.location,
            from_location=original_mouvement.from_location,
            to_location=original_mouvement.to_location,
            cancelled_movement_seq=original_mouvement.mouvement_seq,
        )
        session.add(cancel_mouvement)
        
        # Annuler le mouvement original
        original_mouvement.status = "cancelled"
        session.add(original_mouvement)
        
        # Réactiver la venue
        venue.operational_status = "active"
        dossier = venue.dossier
        dossier.discharge_time = None
        
        session.add(venue)
        session.add(dossier)
        session.flush()
        
        logger.info(
            f"[pam][cancel-discharge] Created cancel movement seq={cancel_mouvement.mouvement_seq} "
            f"cancelling discharge seq={original_mouvement.mouvement_seq}"
        )
        
        return True, None
        
    except Exception as e:
        logger.error(f"[pam][cancel-discharge] failed: {e}", exc_info=True)
        return False, str(e)


async def _handle_cancel_transfer(
    session: Session,
    trigger: str,
    pid_data: dict,
    pv1_data: dict,
    message: Optional[str]
) -> Tuple[bool, Optional[str]]:
    """
    Gère l'annulation de transfert (A12).
    
    Parse le segment ZBE-1 pour identifier le mouvement à annuler,
    puis crée un nouveau mouvement d'annulation.
    """
    try:
        # Parser ZBE pour obtenir le movement_id à annuler
        zbe_data = _parse_zbe_segment(message) if message else None
        
        if not zbe_data or not zbe_data.get("movement_id"):
            logger.warning(f"[pam][cancel-transfer] No ZBE segment, fallback to last transfer")
            # Fallback: chercher le dernier transfert
            identifiers = pid_data.get("identifiers", [])
            if not identifiers:
                return False, "No patient identifier found"
            identifier = identifiers[0][0].split("^")[0]
            
            from sqlmodel import select
            patient = session.exec(select(Patient).where(Patient.identifier == identifier)).first()
            if not patient:
                return False, "Patient not found"
            
            dossier = session.exec(select(Dossier).where(Dossier.patient_id == patient.id)).first()
            if not dossier:
                return False, "Dossier not found"
            
            venue = session.exec(
                select(Venue)
                .where(Venue.dossier_id == dossier.id)
                .order_by(Venue.venue_seq.desc())
            ).first()
            if not venue:
                return False, "Venue not found"
            
            # Trouver le dernier transfert
            original_mouvement = session.exec(
                select(Mouvement)
                .where(Mouvement.venue_id == venue.id, Mouvement.type == "ADT^A02")
                .order_by(Mouvement.when.desc())
            ).first()
        else:
            # Utiliser ZBE-1
            movement_id_str = zbe_data["movement_id"]
            logger.info(f"[pam][cancel-transfer] Looking for movement seq={movement_id_str}")
            
            from sqlmodel import select
            original_mouvement = session.exec(
                select(Mouvement)
                .where(Mouvement.mouvement_seq == int(movement_id_str))
            ).first()
            
            if not original_mouvement:
                logger.warning(f"[pam][cancel-transfer]: Movement seq={movement_id_str} not found, trying fallback")
                # Fallback: chercher le dernier transfert
                identifiers = pid_data.get("identifiers", [])
                if not identifiers:
                    return False, f"Movement with seq={movement_id_str} not found (no patient identifier for fallback)"
                identifier = identifiers[0][0].split("^")[0]
                
                patient = session.exec(select(Patient).where(Patient.identifier == identifier)).first()
                if not patient:
                    return False, f"Movement with seq={movement_id_str} not found (patient not found for fallback)"
                
                dossier = session.exec(select(Dossier).where(Dossier.patient_id == patient.id)).first()
                if not dossier:
                    return False, f"Movement with seq={movement_id_str} not found (dossier not found for fallback)"
                
                venue = session.exec(
                    select(Venue)
                    .where(Venue.dossier_id == dossier.id)
                    .order_by(Venue.venue_seq.desc())
                ).first()
                if not venue:
                    return False, f"Movement with seq={movement_id_str} not found (venue not found for fallback)"
                
                # Trouver le dernier transfert
                original_mouvement = session.exec(
                    select(Mouvement)
                    .where(Mouvement.venue_id == venue.id, Mouvement.type == "ADT^A02")
                    .order_by(Mouvement.when.desc())
                ).first()
                
                if not original_mouvement:
                    return False, f"Movement with seq={movement_id_str} not found (no transfer movement for fallback)"
            else:
                venue = original_mouvement.venue
        
        if not original_mouvement:
            return False, "No transfer movement found to cancel"
        
        # Déterminer la date du mouvement d'annulation : priorité ZBE-2 puis now
        cancel_datetime = datetime.utcnow()
        if zbe_data and zbe_data.get("movement_datetime"):
            try:
                dt_str = zbe_data["movement_datetime"]
                cancel_datetime = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
            except Exception as e:
                logger.warning(f"[pam][cancel-transfer] Failed to parse ZBE-2 datetime '{dt_str}': {e}")

        # Créer mouvement d'annulation
        m_seq = get_next_sequence(session, "mouvement")
        cancel_mouvement = Mouvement(
            mouvement_seq=m_seq,
            venue_id=venue.id,
            type=f"ADT^{trigger}",
            when=cancel_datetime,
            status="cancelled",
            movement_type="transfer-cancel",
            trigger_event=trigger,  # Pour validation des transitions IHE PAM
            location=original_mouvement.from_location,
            from_location=original_mouvement.to_location,
            to_location=original_mouvement.from_location,
            cancelled_movement_seq=original_mouvement.mouvement_seq,
        )
        session.add(cancel_mouvement)
        
        # Annuler le mouvement original
        original_mouvement.status = "cancelled"
        session.add(original_mouvement)
        
        # Restaurer la location précédente
        if original_mouvement.from_location:
            venue.assigned_location = original_mouvement.from_location
            session.add(venue)
        
        session.flush()
        
        logger.info(
            f"[pam][cancel-transfer] Created cancel movement seq={cancel_mouvement.mouvement_seq} "
            f"cancelling transfer seq={original_mouvement.mouvement_seq}"
        )
        
        return True, None
        
    except Exception as e:
        logger.error(f"[pam][cancel-transfer] failed: {e}", exc_info=True)
        return False, str(e)


async def handle_admission_message(
    session: Session, 
    trigger: str, 
    pid_data: dict, 
    pv1_data: dict, 
    message: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """Traitement des messages d'admission et d'annulation.

    - Pour les admissions normales (A01, A04, A05, A06, A07): crée Patient/Dossier/Venue/Mouvement
    - Pour les messages d'identité (A28, A31): mise à jour patient SANS mouvement
    - Pour les annulations (A11, A23, A38): parse ZBE-1 pour trouver le mouvement à annuler
    
    Args:
        session: Session DB
        trigger: Code trigger (A01, A04, A11, A28, A31, etc.)
        pid_data: Données PID parsées
        pv1_data: Données PV1 parsées
        message: Message HL7 complet (requis pour parser ZBE segment sur messages de mouvements)
    
    Returns:
        Tuple[bool, Optional[str]]: (succès, message d'erreur)
    """
    try:
        # Parser le segment ZBE (présent uniquement dans les messages de MOUVEMENTS)
        # Les messages d'identité (A28, A31, A40, A47) n'ont PAS de segment ZBE
        zbe_data = None
        if message and trigger not in ["A28", "A31", "A40", "A47"]:
            zbe_data = _parse_zbe_segment(message)
            if zbe_data:
                logger.info(f"[pam][admission] ZBE parsed: {zbe_data}")
        
        # Gestion des annulations (A11, A23, A38)
        if trigger in ["A11", "A23", "A38"]:
            return await _handle_cancel_admission(session, trigger, pid_data, pv1_data, message)
        
        # Gestion normale des admissions
        # Identifier patient (prendre le premier identifiant PID-3)
        identifiers = pid_data.get("identifiers", [])
        if identifiers:
            raw = identifiers[0][0]
            identifier = raw.split("^")[0]
        else:
            identifier = None

        # Nom / prénom
        family = pid_data.get("family") or ""
        given = pid_data.get("given") or ""

        # Créer ou mettre à jour le patient
        print(f"[pam] identifiers={pid_data.get('identifiers')} family={family} given={given} trigger={trigger}")

        reused_patient = None
        if identifier:
            from sqlmodel import select
            from app.services.patient_update_helper import update_patient_from_pid_data
            existing = session.exec(select(Patient).where(Patient.identifier == identifier)).first()
            if existing:
                update_patient_from_pid_data(existing, pid_data, session, create_mode=False)
                session.add(existing)
                session.flush()
                print(f"[pam] Updated patient id={existing.id} identifier={existing.identifier} family={existing.family} given={existing.given}")
                # Persist all PID-3 identifiers (avoid duplicates)
                try:
                    from sqlmodel import select
                    from app.models_identifiers import Identifier as IdModel
                    for raw_cx, _ in identifiers:
                        try:
                            ident = create_identifier_from_hl7(raw_cx, "patient", existing.id)
                            exists_dup = session.exec(select(IdModel).where(IdModel.system == ident.system, IdModel.value == ident.value)).first()
                            if not exists_dup:
                                session.add(ident)
                        except Exception:
                            continue
                    session.flush()
                except Exception:
                    pass
                reused_patient = existing
                if trigger in ("A28", "A31"):
                    # Identity-only update: no new dossier/venue/mouvement. Return early.
                    return True, None

        # Si patient déjà mis à jour et trigger identité (A28/A31) on aurait quitté.
        # Si patient existe mais trigger mouvement admission (A01/A04/A05/A06/A07) on réutilise.
        if reused_patient:
            patient = reused_patient
        else:
            from app.services.patient_update_helper import create_patient_from_pid_data
            patient = create_patient_from_pid_data(pid_data, session, identifier, identifier)
            session.add(patient)
            session.flush()
            print(f"[pam] Created patient id={patient.id} identifier={patient.identifier} family={patient.family} given={patient.given}")

        # Persist all identifiers from PID-3 as Identifier records
        try:
            from sqlmodel import select
            from app.models_identifiers import Identifier as IdModel
            for raw_cx, _ in identifiers:
                try:
                    ident = create_identifier_from_hl7(raw_cx, "patient", patient.id)
                    # Check duplicate by (system,value)
                    exists = session.exec(select(IdModel).where(IdModel.system == ident.system, IdModel.value == ident.value)).first()
                    if not exists:
                        session.add(ident)
                except Exception:
                    continue
            session.flush()
        except Exception:
            # if identifiers persistence fails, continue; not fatal for POC
            pass
        # Créer un dossier et une venue
        d_seq = get_next_sequence(session, "dossier")
        # Use parsed datetime if available (pid parser provides birth_date_dt),
        # otherwise attempt to parse HL7 YYYYMMDD string, or fallback to now.
        admit_time = pv1_data.get("admit_time")
        if not admit_time and pid_data.get("birth_date_dt"):
            admit_time = pid_data.get("birth_date_dt")
        elif not admit_time and pid_data.get("birth_date"):
            try:
                admit_time = datetime.strptime(pid_data.get("birth_date"), "%Y%m%d")
            except Exception:
                admit_time = None
        if not admit_time:
            admit_time = datetime.utcnow()

        dossier = Dossier(
            dossier_seq=d_seq,
            patient_id=patient.id,
            uf_responsabilite=pv1_data.get("hospital_service") or "UNKNOWN",
            admit_time=admit_time,
        )
        session.add(dossier)
        session.flush()
        print(f"[pam] Created dossier id={dossier.id} dossier_seq={dossier.dossier_seq} patient_id={dossier.patient_id}")

        # If PID-18 (account number) was provided, persist it as a Dossier identifier
        try:
            acc_raw = pid_data.get("account_number")
            if acc_raw:
                from sqlmodel import select
                from app.models_identifiers import Identifier as IdModel
                try:
                    ident = create_identifier_from_hl7(acc_raw, "dossier", dossier.id)
                    # Ensure PID-18 is recorded as AN (Account Number) when no explicit type present
                    try:
                        from app.models_identifiers import IdentifierType as _IdType
                        if ident.type == _IdType.PI:
                            ident.type = _IdType.AN
                    except Exception:
                        pass
                    exists = session.exec(select(IdModel).where(IdModel.system == ident.system, IdModel.value == ident.value)).first()
                    if not exists:
                        session.add(ident)
                        session.flush()
                except Exception:
                    # tolerate bad format
                    pass
        except Exception:
            pass

        v_seq = get_next_sequence(session, "venue")
        location_raw = (pv1_data.get("location") or "").strip()
        location_value = location_raw or None
        previous_location = (pv1_data.get("previous_location") or "").strip() or None
        hospital_service = (pv1_data.get("hospital_service") or "").strip() or None
        movement_code = f"ADT^{trigger}"
        movement_kind = MOVEMENT_KIND_BY_TRIGGER.get(trigger, "admission")
        movement_status = MOVEMENT_STATUS_BY_TRIGGER.get(trigger, "completed")

        operational_status = "active"
        if movement_status == "planned":
            operational_status = "planned"
        elif movement_status == "cancelled":
            operational_status = "cancelled"

        venue = Venue(
            venue_seq=v_seq,
            dossier_id=dossier.id,
            uf_responsabilite=dossier.uf_responsabilite,
            start_time=datetime.utcnow(),
            operational_status=operational_status,
            assigned_location=location_value,
            hospital_service=hospital_service or pv1_data.get("hospital_service") or dossier.uf_responsabilite,
        )
        session.add(venue)
        session.flush()
        print(f"[pam] Created venue id={venue.id} venue_seq={venue.venue_seq} dossier_id={venue.dossier_id}")

        # If PV1-19 (visit number) was provided, persist it as a Venue identifier
        try:
            visit_raw = pv1_data.get("visit_number")
            if visit_raw:
                from sqlmodel import select
                from app.models_identifiers import Identifier as IdModel
                try:
                    ident = create_identifier_from_hl7(visit_raw, "venue", venue.id)
                    # Ensure PV1-19 is recorded as VN (Visit Number) when no explicit type present
                    try:
                        from app.models_identifiers import IdentifierType as _IdType
                        if ident.type == _IdType.PI:
                            ident.type = _IdType.VN
                    except Exception:
                        pass
                    exists = session.exec(select(IdModel).where(IdModel.system == ident.system, IdModel.value == ident.value)).first()
                    if not exists:
                        session.add(ident)
                        session.flush()
                except Exception:
                    # tolerate bad format
                    pass
        except Exception:
            pass

        # Déterminer la date du mouvement : priorité ZBE-2, puis PV1, puis now
        movement_datetime = datetime.utcnow()
        if zbe_data and zbe_data.get("movement_datetime"):
            try:
                # Parse HL7 timestamp: YYYYMMDDHHmmss
                dt_str = zbe_data["movement_datetime"]
                movement_datetime = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
            except Exception as e:
                logger.warning(f"[pam][admission] Failed to parse ZBE-2 datetime '{dt_str}': {e}")
        elif pv1_data.get("admit_time"):
            movement_datetime = pv1_data["admit_time"]
        
        # Déterminer l'UF responsabilité : priorité ZBE-7, puis PV1-10
        uf_resp = dossier.uf_responsabilite
        uf_code_from_zbe = None
        if zbe_data and zbe_data.get("uf_responsable"):
            uf_code_from_zbe = zbe_data["uf_responsable"]
            uf_resp = uf_code_from_zbe
            
            # Vérifier que l'UF existe dans la structure associée à l'EJ
            # Récupérer l'EJ depuis le patient (via un identifiant de type système)
            try:
                from sqlmodel import select
                from app.models_structure import UniteFonctionnelle
                from app.models_structure_fhir import EntiteJuridique
                
                # Chercher l'UF dans la structure
                uf_found = session.exec(
                    select(UniteFonctionnelle)
                    .where(UniteFonctionnelle.identifier == uf_code_from_zbe)
                ).first()
                
                if not uf_found:
                    # Option d'auto-création contrôlée par variable d'environnement
                    import os
                    if os.getenv("PAM_AUTO_CREATE_UF", "0") in ("1", "true", "True"):
                        try:
                            from app.models_structure import (
                                UniteFonctionnelle, Service, Pole, LocationPhysicalType
                            )
                            from app.models_structure_fhir import EntiteGeographique
                            from sqlmodel import select

                            # Récupérer/Créer une entité géographique (placeholder si absente)
                            eg = session.exec(select(EntiteGeographique)).first()
                            if not eg:
                                eg = EntiteGeographique(
                                    identifier="AUTO_EG", name="Entité Géographique Auto",
                                    finess="000000000"
                                )
                                session.add(eg)
                                session.flush()

                            # Récupérer/Créer un pôle virtuel
                            from app.models_structure import Pole as _PoleModel
                            pole = session.exec(select(_PoleModel).where(_PoleModel.identifier == "AUTO_POLE")).first()
                            if not pole:
                                pole = _PoleModel(
                                    identifier="AUTO_POLE",
                                    name="Pôle Auto",
                                    physical_type=LocationPhysicalType.SI,
                                    entite_geo_id=eg.id,
                                    is_virtual=True,
                                )
                                session.add(pole)
                                session.flush()

                            # Récupérer/Créer un service virtuel
                            from app.models_structure import Service as _ServiceModel, LocationServiceType
                            service = session.exec(select(_ServiceModel).where(_ServiceModel.identifier == "AUTO_SERVICE")).first()
                            if not service:
                                service = _ServiceModel(
                                    identifier="AUTO_SERVICE",
                                    name="Service Auto",
                                    physical_type=LocationPhysicalType.SI,
                                    service_type=LocationServiceType.MCO,
                                    pole_id=pole.id,
                                    is_virtual=True,
                                )
                                session.add(service)
                                session.flush()

                            # Créer l'UF minimale
                            uf_found = UniteFonctionnelle(
                                identifier=uf_code_from_zbe,
                                name=f"UF {uf_code_from_zbe}",
                                physical_type=LocationPhysicalType.SI,
                                service_id=service.id,
                                is_virtual=True,
                            )
                            session.add(uf_found)
                            session.flush()
                            logger.warning(
                                f"[pam][admission] UF '{uf_code_from_zbe}' auto-créée (placeholder) sous service 'AUTO_SERVICE'"
                            )
                        except Exception as _auto_e:
                            error_msg = (
                                f"UF Responsable '{uf_code_from_zbe}' (ZBE-7) introuvable et échec auto-création: {_auto_e}"
                            )
                            logger.error(f"[pam][admission] {error_msg}", exc_info=True)
                            return False, error_msg
                    else:
                        error_msg = (
                            f"UF Responsable '{uf_code_from_zbe}' (ZBE-7) introuvable dans la structure. "
                            f"Activer PAM_AUTO_CREATE_UF=1 pour auto-création placeholder ou importer via MFN^M05 avant."
                        )
                        logger.error(f"[pam][admission] {error_msg}")
                        return False, error_msg
                
                logger.info(f"[pam][admission] UF Responsable '{uf_code_from_zbe}' validée: {uf_found.name}")
                
            except Exception as e:
                logger.error(f"[pam][admission] Erreur validation UF: {e}", exc_info=True)
                return False, f"Erreur validation UF Responsable: {str(e)}"
        
        # Mettre à jour l'UF responsabilité du dossier et de la venue
        dossier.uf_responsabilite = uf_resp
        venue.uf_responsabilite = uf_resp
        session.add(dossier)
        session.add(venue)
        
        m_seq = get_next_sequence(session, "mouvement")
        mouvement = Mouvement(
            mouvement_seq=m_seq,
            venue_id=venue.id,
            type=movement_code,
            when=movement_datetime,
            status=movement_status,
            movement_type=movement_kind,
            trigger_event=trigger,  # Pour validation des transitions IHE PAM
            from_location=previous_location,
            to_location=location_value,
            location=location_value,  # PV1-3: Localisation actuelle
        )
        session.add(mouvement)
        session.flush()
        logger.info(
            f"[pam] Created mouvement mouv_seq={mouvement.mouvement_seq} venue_id={mouvement.venue_id} "
            f"movement_type={mouvement.movement_type} when={mouvement.when} "
            f"location={mouvement.location} uf_responsable={uf_resp}"
        )

        # Note: Message emission is now automatic via entity_events.py listeners

        return True, None
    except Exception as e:
        return False, str(e)


async def handle_transfer_message(
    session: Session, 
    trigger: str, 
    pid_data: dict, 
    pv1_data: dict, 
    message: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Gère les messages de transfert et d'annulation de transfert.
    
    - A02: Transfert
    - A12: Annulation de transfert (parse ZBE-1 pour l'ID du mouvement)
    """
    try:
        # Parser le segment ZBE (présent dans TOUS les messages IHE PAM)
        zbe_data = _parse_zbe_segment(message) if message else None
        if zbe_data:
            logger.info(f"[pam][transfer] ZBE parsed: {zbe_data}")
        
        # Gestion de l'annulation de transfert (A12)
        if trigger == "A12":
            return await _handle_cancel_transfer(session, trigger, pid_data, pv1_data, message)
        
        # Gestion normale du transfert (A02)
        identifiers = pid_data.get("identifiers", [])
        if not identifiers:
            return False, "No patient identifier found"
        identifier = identifiers[0][0].split("^")[0]

        from sqlmodel import select

        patient = session.exec(select(Patient).where(Patient.identifier == identifier)).first()
        if not patient:
            return False, "Patient not found"

        # Find last venue for this patient (by dossier/venue_seq)
        dossier = session.exec(select(Dossier).where(Dossier.patient_id == patient.id)).first()
        if not dossier:
            return False, "Dossier not found"

        venue = session.exec(select(Venue).where(Venue.dossier_id == dossier.id).order_by(Venue.venue_seq.desc())).first()
        if not venue:
            return False, "Venue not found"

        previous_location_msg = (pv1_data.get("previous_location") or "").strip()
        previous_location = previous_location_msg or venue.assigned_location
        new_location_raw = (pv1_data.get("location") or "").strip()
        new_location = new_location_raw or previous_location or venue.assigned_location
        hospital_service = (pv1_data.get("hospital_service") or "").strip() or None

        # Déterminer la date du mouvement : priorité ZBE-2, puis now
        movement_datetime = datetime.utcnow()
        if zbe_data and zbe_data.get("movement_datetime"):
            try:
                dt_str = zbe_data["movement_datetime"]
                movement_datetime = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
            except Exception as e:
                logger.warning(f"[pam][transfer] Failed to parse ZBE-2 datetime '{dt_str}': {e}")
        
        print(f"[pam][transfer] patient_id={patient.id} venue_id={venue.id} creating mouvement")
        m_seq = get_next_sequence(session, "mouvement")
        mouvement = Mouvement(
            mouvement_seq=m_seq,
            venue_id=venue.id,
            type=f"ADT^{trigger}",
            when=movement_datetime,
            status=MOVEMENT_STATUS_BY_TRIGGER.get(trigger, "completed"),
            movement_type=MOVEMENT_KIND_BY_TRIGGER.get(trigger, "transfer"),
            trigger_event=trigger,  # Pour validation des transitions IHE PAM
            from_location=previous_location,
            to_location=new_location,
            location=new_location,
        )
        session.add(mouvement)

        venue.assigned_location = new_location
        if hospital_service:
            venue.hospital_service = hospital_service
            dossier.uf_responsabilite = hospital_service
            session.add(dossier)
        session.add(venue)

        session.flush()
        print(f"[pam][transfer] Created mouvement id={mouvement.id} seq={mouvement.mouvement_seq} from={previous_location} to={new_location}")
        
        # Note: Message emission is now automatic via entity_events.py listeners
        
        return True, None
    except Exception as e:
        return False, str(e)


async def handle_discharge_message(
    session: Session, 
    trigger: str, 
    pid_data: dict, 
    pv1_data: dict, 
    message: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Gère les messages de sortie et d'annulation de sortie.
    
    - A03: Sortie
    - A13: Annulation de sortie (parse ZBE-1 pour l'ID du mouvement)
    """
    try:
        # Parser le segment ZBE (présent dans TOUS les messages IHE PAM)
        zbe_data = _parse_zbe_segment(message) if message else None
        if zbe_data:
            logger.info(f"[pam][discharge] ZBE parsed: {zbe_data}")
        
        # Gestion de l'annulation de sortie (A13)
        if trigger == "A13":
            return await _handle_cancel_discharge(session, trigger, pid_data, pv1_data, message)
        
        # Gestion normale de la sortie (A03)
        identifiers = pid_data.get("identifiers", [])
        if not identifiers:
            return False, "No patient identifier found"
        identifier = identifiers[0][0].split("^")[0]

        from sqlmodel import select

        patient = session.exec(select(Patient).where(Patient.identifier == identifier)).first()
        if not patient:
            return False, "Patient not found"

        dossier = session.exec(select(Dossier).where(Dossier.patient_id == patient.id)).first()
        if not dossier:
            return False, "Dossier not found"

        venue = session.exec(select(Venue).where(Venue.dossier_id == dossier.id).order_by(Venue.venue_seq.desc())).first()
        if not venue:
            return False, "Venue not found"

        previous_location = venue.assigned_location
        discharge_time = pv1_data.get("discharge_time") or datetime.utcnow()
        hospital_service = (pv1_data.get("hospital_service") or "").strip() or None

        # Déterminer la date du mouvement : priorité ZBE-2, puis discharge_time, puis now
        movement_datetime = datetime.utcnow()
        if zbe_data and zbe_data.get("movement_datetime"):
            try:
                dt_str = zbe_data["movement_datetime"]
                movement_datetime = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
            except Exception as e:
                logger.warning(f"[pam][discharge] Failed to parse ZBE-2 datetime '{dt_str}': {e}")
        elif discharge_time:
            movement_datetime = discharge_time
        
        # Create a sortie mouvement and mark venue completed
        m_seq = get_next_sequence(session, "mouvement")
        mouvement = Mouvement(
            mouvement_seq=m_seq,
            venue_id=venue.id,
            type=f"ADT^{trigger}",
            when=movement_datetime,
            location=previous_location,
            status=MOVEMENT_STATUS_BY_TRIGGER.get(trigger, "completed"),
            movement_type=MOVEMENT_KIND_BY_TRIGGER.get(trigger, "discharge"),
            trigger_event=trigger,  # Pour validation des transitions IHE PAM
            from_location=previous_location,
            to_location=None,
        )
        session.add(mouvement)
        venue.operational_status = "completed"
        venue.assigned_location = None
        if hospital_service:
            venue.hospital_service = hospital_service
            dossier.uf_responsabilite = hospital_service
        dossier.discharge_time = discharge_time
        session.add(venue)
        session.add(dossier)
        session.flush()
        print(f"[pam][discharge] Created sortie mouvement seq={mouvement.mouvement_seq} and set venue {venue.id} status=completed")
        
        # Note: Message emission is now automatic via entity_events.py listeners
        
        return True, None
    except Exception as e:
        return False, str(e)


async def handle_leave_message(
    session: Session, 
    trigger: str, 
    pid_data: dict, 
    pv1_data: dict,
    message: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Gère les messages de permission (A21/A52 = sortie temporaire, A22/A53 = retour).
    IHE PAM: Leave of Absence
    
    A21/A52: Patient part en permission temporaire
    A22/A53: Patient revient de permission
    """
    try:
        # Parser le segment ZBE (présent dans TOUS les messages IHE PAM)
        zbe_data = _parse_zbe_segment(message) if message else None
        if zbe_data:
            logger.info(f"[pam][leave] ZBE parsed: {zbe_data}")
        
        identifiers = pid_data.get("identifiers", [])
        if not identifiers:
            return False, "No patient identifier found"
        identifier = identifiers[0][0].split("^")[0]

        from sqlmodel import select

        patient = session.exec(select(Patient).where(Patient.identifier == identifier)).first()
        if not patient:
            return False, "Patient not found"

        # Find active dossier
        dossier = session.exec(select(Dossier).where(Dossier.patient_id == patient.id)).first()
        if not dossier:
            return False, "Dossier not found"

        # Find current venue
        venue = session.exec(
            select(Venue)
            .where(Venue.dossier_id == dossier.id)
            .order_by(Venue.venue_seq.desc())
        ).first()
        if not venue:
            return False, "Venue not found"

        # Get location info
        location = (pv1_data.get("location") or "").strip() or venue.assigned_location
        hospital_service = (pv1_data.get("hospital_service") or "").strip() or venue.hospital_service
        
        # Déterminer la date du mouvement : priorité ZBE-2, puis now
        movement_datetime = datetime.utcnow()
        if zbe_data and zbe_data.get("movement_datetime"):
            try:
                dt_str = zbe_data["movement_datetime"]
                movement_datetime = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
            except Exception as e:
                logger.warning(f"[pam][leave] Failed to parse ZBE-2 datetime '{dt_str}': {e}")
        
        # Create mouvement for leave of absence
        m_seq = get_next_sequence(session, "mouvement")
        movement_type = "leave-out" if trigger in ["A21", "A52"] else "leave-return"
        status = "leave" if trigger in ["A21", "A52"] else "completed"
        
        mouvement = Mouvement(
            mouvement_seq=m_seq,
            venue_id=venue.id,
            type=f"ADT^{trigger}",
            when=movement_datetime,
            status=status,
            movement_type=movement_type,
            trigger_event=trigger,  # Pour validation des transitions IHE PAM
            location=location,
        )
        session.add(mouvement)
        
        # Update venue status if leaving
        if trigger in ["A21", "A52"]:
            venue.status = "leave"
        elif trigger in ["A22", "A53"]:
            venue.status = "active"
        
        if hospital_service:
            venue.hospital_service = hospital_service
        
        session.add(venue)
        session.flush()
        
        logger.info(f"[pam][leave] Created mouvement id={mouvement.id} seq={mouvement.mouvement_seq} type={movement_type}")
        
        # Note: Message emission is now automatic via entity_events.py listeners
        
        return True, None
    except Exception as e:
        logger.error(f"[pam][leave] Error: {e}", exc_info=True)
        return False, str(e)


async def handle_doctor_message(
    session: Session, 
    trigger: str, 
    pid_data: dict, 
    pv1_data: dict,
    message: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Gère les messages de changement de médecin (A54/A55).
    IHE PAM: Change attending doctor
    
    A54: Changement de médecin responsable
    A55: Annulation du changement de médecin
    """
    try:
        # Parser le segment ZBE (présent dans TOUS les messages IHE PAM)
        zbe_data = _parse_zbe_segment(message) if message else None
        if zbe_data:
            logger.info(f"[pam][doctor] ZBE parsed: {zbe_data}")
        
        identifiers = pid_data.get("identifiers", [])
        if not identifiers:
            return False, "No patient identifier found"
        identifier = identifiers[0][0].split("^")[0]

        from sqlmodel import select

        patient = session.exec(select(Patient).where(Patient.identifier == identifier)).first()
        if not patient:
            return False, "Patient not found"

        # Find active dossier
        dossier = session.exec(select(Dossier).where(Dossier.patient_id == patient.id)).first()
        if not dossier:
            return False, "Dossier not found"

        # Find current venue
        venue = session.exec(
            select(Venue)
            .where(Venue.dossier_id == dossier.id)
            .order_by(Venue.venue_seq.desc())
        ).first()
        if not venue:
            return False, "Venue not found"

        # Get attending doctor from PV1-7 or PV1-17
        attending_doctor = (pv1_data.get("attending_doctor") or "").strip()
        
        # Déterminer la date du mouvement : priorité ZBE-2, puis now
        movement_datetime = datetime.utcnow()
        if zbe_data and zbe_data.get("movement_datetime"):
            try:
                dt_str = zbe_data["movement_datetime"]
                movement_datetime = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
            except Exception as e:
                logger.warning(f"[pam][doctor] Failed to parse ZBE-2 datetime '{dt_str}': {e}")
        
        if trigger == "A54":
            # Change attending doctor
            if attending_doctor:
                venue.attending_doctor = attending_doctor
                dossier.attending_provider = attending_doctor
            
            # Create mouvement for doctor change
            m_seq = get_next_sequence(session, "mouvement")
            mouvement = Mouvement(
                mouvement_seq=m_seq,
                venue_id=venue.id,
                type=f"ADT^{trigger}",
                when=movement_datetime,
                status="completed",
                movement_type="doctor-change",
                trigger_event=trigger,  # Pour validation des transitions IHE PAM
                location=venue.assigned_location,
            )
            session.add(mouvement)
            
        elif trigger == "A55":
            # Cancel doctor change - revert to previous
            # In real implementation, would need to track previous doctor
            # For now, just create a cancel mouvement
            m_seq = get_next_sequence(session, "mouvement")
            mouvement = Mouvement(
                mouvement_seq=m_seq,
                venue_id=venue.id,
                type=f"ADT^{trigger}",
                when=movement_datetime,
                status="cancelled",
                movement_type="doctor-change-cancel",
                trigger_event=trigger,  # Pour validation des transitions IHE PAM
                location=venue.assigned_location,
            )
            session.add(mouvement)
        
        session.add(venue)
        session.add(dossier)
        session.flush()
        
        logger.info(f"[pam][doctor] Processed {trigger} for venue_id={venue.id}")
        
        # Note: Message emission is now automatic via entity_events.py listeners
        
        return True, None
    except Exception as e:
        logger.error(f"[pam][doctor] Error: {e}", exc_info=True)
        return False, str(e)
