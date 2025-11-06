"""Pipeline de traitement des messages HL7v2 entrants (IHE PAM).

Fonctions principales
- Validation et parsing des segments MSH/PID/PD1/PV1
- Application d'updates Z99 tolérantes (POC) sur des entités manquantes
- Routage métier via `IHEMessageRouter`
- Journalisation dans `MessageLog` et génération des ACK HL7 (AA/AE/AR)

Transactions & sessions
- Utilise la session SQLModel fournie (voir `session_factory` côté MLLP)
    et enchaîne les opérations dans un contexte transactionnel `session.begin()`
    lorsque nécessaire.
"""

# app/services/transport_inbound.py
from datetime import datetime
import re
from typing import Dict, List, Optional, Tuple
import logging

from sqlmodel import Session, select

from app.models_endpoints import MessageLog
from app.services.mllp import parse_msh_fields, build_ack
from app.services.pam_validation import validate_pam
import json
from app.models import Patient, Dossier, Venue, Mouvement
from app.models_identifiers import Identifier, IdentifierType
from app.db import get_next_sequence
from app.services.emit_on_create import emit_to_senders
from app.services.identifier_manager import (
    create_identifier_from_hl7,
    merge_identifiers,
    get_main_identifier
)
from app.services.message_router import IHEMessageRouter
from app.state_transitions import is_valid_transition, assert_transition

logger = logging.getLogger("transport_inbound")


def _parse_patient_identifiers(pid_segment: str) -> List[Tuple[str, str]]:
    """Parse les identifiants patients du segment PID"""
    identifiers = []
    try:
        parts = pid_segment.split("|")
        if len(parts) <= 3:
            return []
            
        # PID-3 contient une liste d'identifiants séparés par ~
        id_list = parts[3].split("~")
        for cx in id_list:
            if not cx:
                continue
            # Détecter le type d'identifiant
            id_type = "PI"  # Par défaut Patient Internal
            if "^" in cx:
                cx_parts = cx.split("^")
                if len(cx_parts) > 4:
                    id_type = cx_parts[4]
            identifiers.append((cx, id_type))
            
    except Exception as e:
        logger.error(f"Erreur parsing identifiants PID: {str(e)}")
        
    return identifiers


def _parse_pid(message: str) -> dict:
    """Parse le segment PID avec support complet des identifiants"""
    out = {
        "identifiers": [],
        "external_id": None,
        "account_number": None,
        "family": "",
        "given": "",
        "middle": None,
        "prefix": None,
        "suffix": None,
        "birth_date": None,
        "gender": None,
        "address": None,
        "city": None,
        "state": None,
        "postal_code": None,
        "country": None,
        "phone": None,
        "email": None,
        "ssn": None,
        "marital_status": None,
        # Nouveaux champs multi-valués
        "names": [],
        "addresses": [],
        "phones": [],
        # Champs adresse de naissance
        "birth_family": None,
        "birth_address": None,
        "birth_city": None,
        "birth_state": None,
        "birth_postal_code": None,
        "birth_country": None,
        "birth_place": None,
        # Champs téléphones supplémentaires
        "mobile": None,
        "work_phone": None,
        # PID-32: Identity Reliability Code
        "identity_reliability_code": None
    }
    try:
        lines = re.split(r"\r|\n", message)
        pid = next((l for l in lines if l.startswith("PID")), None)
        if not pid:
            return out
            
        parts = pid.split("|")
        
        # Identifiants (PID-3)
        out["identifiers"] = _parse_patient_identifiers(pid)
        
        # Nom (PID-5) - XPN multi-valué (répétitions ~)
        if len(parts) > 5 and parts[5]:
            # Parser toutes les répétitions de noms
            name_repetitions = parts[5].split("~")
            all_names = []
            for name_rep in name_repetitions:
                name_parts = name_rep.split("^")
                name_data = {
                    "family": name_parts[0] if len(name_parts) > 0 else "",
                    "given": name_parts[1] if len(name_parts) > 1 else "",
                    "middle": name_parts[2] if len(name_parts) > 2 else None,
                    "suffix": name_parts[3] if len(name_parts) > 3 else None,
                    "prefix": name_parts[4] if len(name_parts) > 4 else None,
                    # XPN : family^given^middle^suffix^prefix^degree^type
                    "type": name_parts[6] if len(name_parts) > 6 else None  # D=usuel, L=naissance
                }
                all_names.append(name_data)
            
            # Stocker toutes les répétitions
            out["names"] = all_names
            
            # Pour compatibilité, garder le premier nom dans les champs simples
            if all_names:
                out["family"] = all_names[0]["family"]
                out["given"] = all_names[0]["given"]
                out["middle"] = all_names[0]["middle"]
                out["prefix"] = all_names[0]["prefix"]
                out["suffix"] = all_names[0]["suffix"]
                
                # Chercher nom de naissance (type L) si présent
                birth_name = next((n for n in all_names if n.get("type") == "L"), None)
                if birth_name:
                    out["birth_family"] = birth_name["family"]
                
        # Date naissance (PID-7)
        if len(parts) > 7 and parts[7]:
            # Keep the raw HL7 date string for tests and also provide a
            # parsed datetime as birth_date_dt when possible.
            out["birth_date"] = parts[7]
            try:
                out["birth_date_dt"] = datetime.strptime(parts[7], "%Y%m%d")
            except Exception:
                out["birth_date_dt"] = None

        # External id: first CX in PID-3 (raw value before component separators)
        if len(parts) > 3 and parts[3]:
            out["external_id"] = parts[3].split("^")[0]

        # Genre (PID-8)
        if len(parts) > 8:
            out["gender"] = parts[8]
            
        # Adresse (PID-11) - XAD multi-valué (répétitions ~)
        if len(parts) > 11 and parts[11]:
            # Parser toutes les répétitions d'adresses
            addr_repetitions = parts[11].split("~")
            all_addresses = []
            for addr_rep in addr_repetitions:
                addr_parts = addr_rep.split("^")
                addr_data = {
                    "street": addr_parts[0] if len(addr_parts) > 0 else None,
                    "other": addr_parts[1] if len(addr_parts) > 1 else None,
                    "city": addr_parts[2] if len(addr_parts) > 2 else None,
                    "state": addr_parts[3] if len(addr_parts) > 3 else None,
                    "postal_code": addr_parts[4] if len(addr_parts) > 4 else None,
                    "country": addr_parts[5] if len(addr_parts) > 5 else None,
                    "type": addr_parts[6] if len(addr_parts) > 6 else None  # H=home, O=office, etc.
                }
                all_addresses.append(addr_data)
            
            # Stocker toutes les répétitions
            out["addresses"] = all_addresses
            
            # Pour compatibilité, garder la première adresse dans les champs simples
            if all_addresses:
                out["address"] = all_addresses[0]["street"]
                out["city"] = all_addresses[0]["city"]
                out["state"] = all_addresses[0]["state"]
                out["postal_code"] = all_addresses[0]["postal_code"]
                out["country"] = all_addresses[0].get("country")
                
                # Si 2e adresse présente, la considérer comme adresse de naissance
                if len(all_addresses) > 1:
                    birth_addr = all_addresses[1]
                    out["birth_address"] = birth_addr["street"]
                    out["birth_city"] = birth_addr["city"]
                    out["birth_state"] = birth_addr["state"]
                    out["birth_postal_code"] = birth_addr["postal_code"]
                    out["birth_country"] = birth_addr.get("country")
            
        # Téléphone (PID-13) - XTN multi-valué (répétitions ~)
        if len(parts) > 13 and parts[13]:
            # Parser toutes les répétitions de téléphones
            phone_repetitions = parts[13].split("~")
            all_phones = []
            for phone_rep in phone_repetitions:
                phone_parts = phone_rep.split("^")
                phone_data = {
                    "number": phone_parts[0] if len(phone_parts) > 0 else None,
                    "type": phone_parts[2] if len(phone_parts) > 2 else None,  # PRN=primary, ORN=other, etc.
                    "use": phone_parts[1] if len(phone_parts) > 1 else None   # HOME, WORK, CELL
                }
                all_phones.append(phone_data)
            
            # Stocker toutes les répétitions
            out["phones"] = all_phones
            
            # Pour compatibilité, garder le premier téléphone dans le champ simple
            if all_phones:
                out["phone"] = all_phones[0]["number"]
                
                # Si d'autres téléphones présents, les stocker dans des champs dédiés
                for i, phone_data in enumerate(all_phones[1:], start=1):
                    if phone_data.get("use") == "CELL" or phone_data.get("type") == "CP":
                        out["mobile"] = phone_data["number"]
                    elif phone_data.get("use") == "WORK" or phone_data.get("type") == "WP":
                        out["work_phone"] = phone_data["number"]
            
        # Champs spécifiques (PID-16 marital_status). PID-19 est interdit dans le profil FR
        if len(parts) > 16 and parts[16]:
            out["marital_status"] = parts[16]
        # PID-18 = Patient Account Number (often used to reference a dossier)
        if len(parts) > 18 and parts[18]:
            out["account_number"] = parts[18]
        
        # PID-23: Lieu de naissance (Birth Place)
        if len(parts) > 23 and parts[23]:
            out["birth_place"] = parts[23]
            # Si birth_city n'est pas déjà renseigné par une adresse, utiliser PID-23
            if not out.get("birth_city"):
                out["birth_city"] = parts[23]
        
        # PID-32: Identity Reliability Code (HL7 Table 0445)
        if len(parts) > 32 and parts[32]:
            out["identity_reliability_code"] = parts[32]
            
    except Exception as e:
        logger.error(f"Erreur parsing PID: {str(e)}")
        
    return out


def _parse_pd1(message: str) -> dict:
    """Parse PD1 segment for a couple of useful POC fields.
    Returns dict with keys: primary_care_provider, religion, language
    PD1 is optional; be tolerant.
    """
    out = {"primary_care_provider": None, "religion": None, "language": None}
    try:
        lines = re.split(r"\r|\n", message)
        pd1 = next((l for l in lines if l.startswith("PD1")), None)
        if not pd1:
            return out
        parts = pd1.split("|")
        # PD1-3 = patient primary care provider
        if len(parts) > 3 and parts[3]:
            out["primary_care_provider"] = parts[3].split("^")[0]
        # PD1-2 = living arrangement (not used) ; religion sometimes in PID but check PD1-4
        if len(parts) > 4 and parts[4]:
            out["religion"] = parts[4]
        # PD1-6 or PD1-7 may contain language; be tolerant and check PD1-6
        if len(parts) > 6 and parts[6]:
            out["language"] = parts[6]
    except Exception:
        pass
    return out


def _parse_hl7_datetime(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    s = s.strip()
    # common HL7 formats: YYYYMMDDHHMMSS or YYYYMMDD
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y%m%d"):
        try:
            return datetime.strptime(s[: len(fmt.replace("%", ""))], fmt)
        except Exception:
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
    # fallback: ignore timezone/extra and try first 14 chars
    try:
        return datetime.strptime(s[:14], "%Y%m%d%H%M%S")
    except Exception:
        return None


def _parse_pv1(message: str) -> dict:
    """Extract a few PV1 fields we need: location, hospital_service, admit/discharge datetimes, patient_class."""
    out = {
        "location": "",
        "previous_location": "",
        "hospital_service": "",
        "admit_time": None,
        "discharge_time": None,
        "patient_class": "",
        "visit_number": None,
    }
    try:
        lines = re.split(r"\r|\n", message)
        pv1 = next((l for l in lines if l.startswith("PV1")), None)
        if not pv1:
            return out
        parts = pv1.split("|")
        # PV1 fields commonly: 2=patient class, 3=assigned patient location, 10=hospital service
        if len(parts) > 2 and parts[2]:
            out["patient_class"] = parts[2]
        if len(parts) > 3 and parts[3]:
            out["location"] = parts[3]
        if len(parts) > 6 and parts[6]:
            out["previous_location"] = parts[6]
        if len(parts) > 10 and parts[10]:
            out["hospital_service"] = parts[10]
        # admit/discharge times
        if len(parts) > 44 and parts[44]:
            out["admit_time"] = _parse_hl7_datetime(parts[44])
        if len(parts) > 45 and parts[45]:
            out["discharge_time"] = _parse_hl7_datetime(parts[45])
        # PV1-19 = Visit Number / Visit ID (often CX format)
        if len(parts) > 19 and parts[19]:
            out["visit_number"] = parts[19]
    except Exception:
        pass
    return out


def _parse_zbe(message: str) -> dict:
    """Parse segment ZBE (extension IHE PAM France).
    
    Retourne:
        dict avec clés: movement_id (ZBE-1), movement_datetime (ZBE-2), 
        original_trigger (ZBE-6), movement_indicator (ZBE-9)
    """
    out = {
        "movement_id": None,
        "movement_datetime": None,
        "original_trigger": None,
        "movement_indicator": None,
    }
    try:
        lines = re.split(r"\r|\n", message)
        zbe = next((l for l in lines if l.startswith("ZBE")), None)
        if not zbe:
            return out
        parts = zbe.split("|")
        # ZBE-1: Identifiant du mouvement
        if len(parts) > 1 and parts[1]:
            out["movement_id"] = parts[1]
        # ZBE-2: Date/heure du mouvement
        if len(parts) > 2 and parts[2]:
            out["movement_datetime"] = _parse_hl7_datetime(parts[2])
        # ZBE-6: Type d'événement original (pour Z99)
        if len(parts) > 6 and parts[6]:
            out["original_trigger"] = parts[6]
        # ZBE-9: Mode de traitement / Indicateur de mouvement
        if len(parts) > 9 and parts[9]:
            out["movement_indicator"] = parts[9].strip().upper()
    except Exception:
        pass
    return out


def _handle_z99_updates(message: str, session: Session) -> None:
    """Apply Z99 partial updates received over HL7.

    For the sandbox/test environment we tolerate references to unknown
    structures (dossiers, venues, mouvements, patients) by creating
    placeholder records on-the-fly so that subsequent updates succeed.
    """

    def _ensure_patient(seq_hint: int, updates: dict) -> Patient:
        identifier = updates.get("identifier") or f"Z99-{seq_hint:06d}"
        patient = session.exec(select(Patient).where(Patient.identifier == identifier)).first()
        if patient:
            return patient

        patient = Patient(
            patient_seq=get_next_sequence(session, "patient"),
            identifier=identifier,
            external_id=identifier,
            family=updates.get("nom") or f"Patient Z99 {seq_hint}",
            given=updates.get("prenom") or "Auto",
            gender=updates.get("sexe") or "unknown",
            birth_date=updates.get("date_naissance"),
        )
        session.add(patient)
        session.flush()
        logger.info("Created placeholder patient for Z99 update", extra={"identifier": identifier})
        return patient

    def _ensure_dossier(seq_value: int, updates: dict) -> Dossier:
        dossier = session.exec(select(Dossier).where(Dossier.dossier_seq == seq_value)).first()
        if dossier:
            return dossier

        patient = _ensure_patient(seq_value, updates)
        dossier = Dossier(
            dossier_seq=seq_value,
            patient_id=patient.id,
            uf_responsabilite=updates.get("uf_responsabilite") or "Z99-UF",
            admit_time=datetime.utcnow(),
        )
        session.add(dossier)
        session.flush()
        logger.info("Created placeholder dossier for Z99 update", extra={"dossier_seq": seq_value})
        return dossier

    def _ensure_venue(seq_value: int, updates: dict) -> Venue:
        venue = session.exec(select(Venue).where(Venue.venue_seq == seq_value)).first()
        if venue:
            return venue

        dossier_seq_hint = updates.get("dossier_seq")
        try:
            dossier_seq_value = int(dossier_seq_hint) if dossier_seq_hint else seq_value
        except Exception:
            dossier_seq_value = seq_value
        dossier = _ensure_dossier(dossier_seq_value, updates)
        venue = Venue(
            venue_seq=seq_value,
            dossier_id=dossier.id,
            uf_responsabilite=updates.get("uf_responsabilite") or dossier.uf_responsabilite,
            start_time=datetime.utcnow(),
            code=updates.get("code") or f"VEN-{seq_value}",
            label=updates.get("label") or f"Venue Z99 {seq_value}",
        )
        session.add(venue)
        session.flush()
        logger.info("Created placeholder venue for Z99 update", extra={"venue_seq": seq_value})
        return venue

    def _ensure_mouvement(seq_value: int, updates: dict) -> Mouvement:
        mouvement = session.exec(select(Mouvement).where(Mouvement.mouvement_seq == seq_value)).first()
        if mouvement:
            return mouvement

        venue_seq_hint = updates.get("venue_seq")
        try:
            venue_seq_value = int(venue_seq_hint) if venue_seq_hint else seq_value
        except Exception:
            venue_seq_value = seq_value
        venue = _ensure_venue(venue_seq_value, updates)
        mouvement = Mouvement(
            mouvement_seq=seq_value,
            venue_id=venue.id,
            type=updates.get("type") or "Z99",
            when=datetime.utcnow(),
            location=updates.get("location") or getattr(venue, "code", None),
        )
        session.add(mouvement)
        session.flush()
        logger.info("Created placeholder mouvement for Z99 update", extra={"mouvement_seq": seq_value})
        return mouvement

    try:
        lines = re.split(r"\r|\n", message)
        for seg in (l for l in lines if l.startswith("Z99")):
            parts = seg.split("|")
            if len(parts) < 4:
                continue

            entity = (parts[1] or "").strip()
            seq_raw = (parts[2] or "").strip()
            if not entity or not seq_raw:
                continue

            try:
                seq_value = int(seq_raw)
            except Exception:
                logger.warning("Invalid sequence identifier in Z99 segment", extra={"segment": seg})
                continue

            updates: Dict[str, Optional[str]] = {}
            fields = parts[3:]
            for idx in range(0, len(fields), 2):
                field_name = fields[idx].strip() if idx < len(fields) else ""
                if not field_name:
                    continue
                updates[field_name] = fields[idx + 1] if idx + 1 < len(fields) else None

            obj = None
            entity_lc = entity.lower()
            if entity_lc.startswith("doss"):
                obj = _ensure_dossier(seq_value, updates)
            elif entity_lc.startswith("ven"):
                obj = _ensure_venue(seq_value, updates)
            elif entity_lc.startswith("mouv") or entity_lc.startswith("mvt"):
                obj = _ensure_mouvement(seq_value, updates)
            elif entity_lc.startswith("pat"):
                obj = _ensure_patient(seq_value, updates)
            else:
                logger.warning("Unsupported Z99 entity encountered", extra={"entity": entity})
                continue

            if not obj:
                continue

            for field_name, value in updates.items():
                if hasattr(obj, field_name) and value is not None:
                    setattr(obj, field_name, value)
            session.add(obj)

        session.flush()
    except Exception:
        logger.exception("Error handling Z99 updates")


def _validate_message_structure(msg: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """Valide la structure d'un message HL7v2 et retourne les champs MSH.
    
    Args:
        msg: Message HL7 déframé
        
    Returns:
        (is_valid, error_text, msh_fields)
    """
    try:
        # Vérification basique de la structure
        if not msg or not msg.startswith("MSH"):
            return False, "Invalid message structure", None
            
        # Parser l'en-tête
        msh = parse_msh_fields(msg)
        if not msh:
            return False, "Failed to parse MSH segment", None
            
        # Vérifier les champs obligatoires
        required_fields = ["sending_app", "sending_facility", "msg_type", "control_id"]
        missing = [f for f in required_fields if not msh.get(f)]
        if missing:
            return False, f"Missing required MSH fields: {', '.join(missing)}", None
            
        return True, None, msh
    except Exception as e:
        return False, f"Message validation error: {str(e)}", None

async def on_message_inbound_async(msg: str, session, endpoint) -> str:
    """
    Point d'entrée principal pour les messages HL7v2 IHE PAM entrants.
    Implémente le profil IHE PAM (ITI-30/31) avec support des annulations.
    
    Types de messages supportés :
    1. Gestion des admissions (ADT) :
       - A01/A11 : Admission/Annulation
       - A04/A23 : Inscription/Suppression
       - A05/A38 : Pré-admission/Annulation
       - A06/A07 : Changement type patient
       
    2. Mouvements patients :
       - A02/A12 : Transfert/Annulation
       - A21/A52 : Permission/Annulation
       - A22/A53 : Retour/Annulation
       
    3. Sorties :
       - A03/A13 : Sortie/Annulation
       
    4. Autres :
       - A54/A55 : Changement médecin/Annulation
       - Z99 : Mises à jour partielles (extension FR)
       
    Le traitement est transactionnel et journalisé via MessageLog.
    Les acquittements sont construits selon les règles HL7v2.5.
    
    Args:
        msg: Message HL7v2 déframé
        session: Session SQLModel active
        endpoint: Point de terminaison source (peut être None)
        
    Returns:
        Message ACK formaté HL7v2 (AA=succès, AE=erreur applicative, AR=erreur système)
    """
    log = None
    
    # 1. Validation structurelle
    is_valid, error_text, msh = _validate_message_structure(msg)
    if not is_valid:
        return build_ack(msg, ack_code="AR", text=error_text)
        
    ctrl_id = msh["control_id"]
    msg_family = msh.get("type", "")
    trigger = msh.get("trigger", "")

    # 2. Validation du type de message
    if msg_family != "ADT":
        return build_ack(
            msg, 
            ack_code="AE",
            text=f"Unsupported message type: {msg_family} (only ADT supported)"
        )
        
    # 3. Initialisation du traitement transactionnel
    try:
        from contextlib import nullcontext
        ctx = session.begin() if not session.in_transaction() else nullcontext()

        with ctx:
            log = MessageLog(
                direction="in",
                kind="MLLP",
                endpoint_id=endpoint.id if endpoint else None,
                correlation_id=ctrl_id,
                payload=msg,
                status="processing",
                message_type=f"{msg_family}^{trigger}",
                created_at=datetime.utcnow(),
            )
            session.add(log)

            # PAM validation (configurable per endpoint)
            try:
                val = validate_pam(msg, direction="in", profile=(getattr(endpoint, "pam_profile", None) or "IHE_PAM_FR"))
                log.pam_validation_status = val.level
                log.pam_validation_issues = json.dumps(val.to_dict().get("issues", []), ensure_ascii=False)
                # Enforce rejection if configured and validation failed
                if endpoint and getattr(endpoint, "pam_validate_enabled", False) and (getattr(endpoint, "pam_validate_mode", "warn") == "reject"):
                    if val.level == "fail":
                        log.status = "rejected"
                        first_issue = (val.issues[0].message if val.issues else "Règles IHE PAM non respectées")
                        ack = build_ack(msg, ack_code="AE", text=f"Validation IHE PAM échouée: {first_issue}")
                        log.ack_payload = ack
                        return ack
            except Exception:
                # Never block processing due to validator errors; log as warn-level issue
                try:
                    log.pam_validation_status = "warn"
                    log.pam_validation_issues = json.dumps([{"code": "VALIDATOR_ERROR", "message": "Erreur interne du validateur", "severity": "warn"}], ensure_ascii=False)
                except Exception:
                    pass

            if trigger == "Z99":
                try:
                    _handle_z99_updates(msg, session)
                    log.status = "processed"
                    ack = build_ack(msg, ack_code="AA", text="Z99 updates applied")
                except Exception as exc:
                    logger.exception("Error processing Z99 message")
                    log.status = "error"
                    ack = build_ack(msg, ack_code="AE", text=f"Z99 processing failed: {str(exc)[:80]}")
                log.ack_payload = ack
                return ack

            pid_data = _parse_pid(msg)
            pv1_data = _parse_pv1(msg)
            zbe_data = _parse_zbe(msg)
            
            # Contrôle additionnel pour ZBE-9="C" : vérifier l'état du dossier
            # La correction de statut sans création de nouveau mouvement (valeur C)
            # ne peut être utilisée que si la venue est en état d'admission ou préadmission
            if zbe_data.get("movement_indicator") == "C":
                if trigger == "Z99":
                    # Récupérer la venue via PV1-19
                    visit_num_str = pv1_data.get("visit_number")
                    if visit_num_str:
                        try:
                            venue_seq = int(visit_num_str.split("^")[0]) if "^" in visit_num_str else int(visit_num_str)
                            venue = session.exec(
                                select(Venue).where(Venue.venue_seq == venue_seq)
                            ).first()
                            if venue:
                                # Vérifier que l'état opérationnel est "planned" (préadmission) ou "active" (admission)
                                if venue.operational_status not in {"planned", "active"}:
                                    log.status = "rejected"
                                    error_text = f"ZBE-9='C' (correction de statut) non autorisé: la venue {venue_seq} n'est pas en état d'admission ou préadmission (état actuel: {venue.operational_status or 'non défini'})"
                                    ack = build_ack(msg, ack_code="AE", text=error_text)
                                    log.ack_payload = ack
                                    logger.warning(
                                        "Message Z99 avec ZBE-9='C' rejeté: état de venue invalide",
                                        extra={
                                            "venue_seq": venue_seq,
                                            "operational_status": venue.operational_status,
                                            "trigger": trigger
                                        }
                                    )
                                    return ack
                            else:
                                # Venue non trouvée
                                log.status = "rejected"
                                error_text = f"ZBE-9='C': venue {venue_seq} non trouvée"
                                ack = build_ack(msg, ack_code="AE", text=error_text)
                                log.ack_payload = ack
                                return ack
                        except (ValueError, IndexError) as e:
                            # Numéro de venue invalide
                            log.status = "rejected"
                            error_text = f"ZBE-9='C': numéro de venue invalide dans PV1-19 ({visit_num_str})"
                            ack = build_ack(msg, ack_code="AE", text=error_text)
                            log.ack_payload = ack
                            return ack
                    else:
                        # PV1-19 manquant pour un Z99 avec C
                        log.status = "rejected"
                        error_text = "ZBE-9='C' requiert un numéro de venue (PV1-19) pour valider l'état d'admission"
                        ack = build_ack(msg, ack_code="AE", text=error_text)
                        log.ack_payload = ack
                        return ack
            
            # Validation des transitions IHE PAM
            # Récupérer le dernier événement du dossier/venue si applicable
            previous_event = None
            if pv1_data.get("visit_number"):
                # Rechercher la venue existante pour connaître le dernier événement
                visit_num_str = pv1_data["visit_number"]
                # Extract ID part if CX format (ID^^^system^type)
                visit_num_id = visit_num_str.split("^^^")[0] if "^^^" in visit_num_str else visit_num_str
                try:
                    venue = session.exec(
                        select(Venue).where(Venue.venue_seq == int(visit_num_id))
                    ).first()
                except ValueError:
                    # If not numeric, try as string identifier
                    venue = session.exec(
                        select(Venue).where(Venue.code == visit_num_id)
                    ).first()
                if venue:
                    # Récupérer le dernier mouvement pour connaître le dernier événement
                    last_mouvement = session.exec(
                        select(Mouvement)
                        .where(Mouvement.venue_id == venue.id)
                        .order_by(Mouvement.mouvement_seq.desc())
                    ).first()
                    if last_mouvement and hasattr(last_mouvement, 'trigger_event'):
                        previous_event = last_mouvement.trigger_event
            else:
                # Si pas de visit_number, chercher le dernier événement du patient
                # pour permettre des enchaînements sans numéro de venue explicite
                if pid_data.get("identifiers"):
                    first_ident = pid_data["identifiers"][0][0] if pid_data["identifiers"] else None
                    if first_ident:
                        # Extraire l'ID du CX (partie avant ^^^)
                        patient_id = first_ident.split("^^^")[0] if "^^^" in first_ident else first_ident
                        # Chercher le patient par identifier
                        patient = session.exec(
                            select(Patient).where(Patient.identifier == patient_id)
                        ).first()
                        if patient:
                            # Chercher le dernier mouvement de ce patient
                            last_mouvement = session.exec(
                                select(Mouvement)
                                .join(Venue)
                                .join(Dossier)
                                .where(Dossier.patient_id == patient.id)
                                .order_by(Mouvement.mouvement_seq.desc())
                            ).first()
                            if last_mouvement and hasattr(last_mouvement, 'trigger_event'):
                                previous_event = last_mouvement.trigger_event
            
            # Valider la transition (lève ValueError si invalide),
            # sauf pour les messages d'identité purs (A28/A31/A40/A47) qui
            # ne font pas partie du workflow de venue IHE PAM.
            identity_only_triggers = {"A28", "A31", "A40", "A47"}
            if trigger not in identity_only_triggers:
                try:
                    assert_transition(previous_event, trigger)
                except ValueError as ve:
                    # Transition invalide : rejeter avec ACK AE
                    log.status = "rejected"
                    error_text = str(ve)
                    ack = build_ack(msg, ack_code="AE", text=error_text)
                    log.ack_payload = ack
                    logger.warning(
                        "Transition IHE PAM invalide rejetée",
                        extra={
                            "trigger": trigger,
                            "previous_event": previous_event,
                            "error": error_text
                        }
                    )
                    return ack
            
            logger.info(
                "Routing ADT message",
                extra={"trigger": trigger, "patient_identifiers": pid_data.get("identifiers")},
            )
            success, err = await IHEMessageRouter.route_message(session, trigger, pid_data, pv1_data, message=msg)

            if success:
                log.status = "processed"
                text = f"Message {trigger} traité avec succès"
                ack = build_ack(msg, ack_code="AA", text=text)
            else:
                log.status = "error"
                text = err or f"Handler returned no result for {trigger}"
                ack = build_ack(msg, ack_code="AE", text=text)

            log.ack_payload = ack
            return ack

    except ValueError as ve:
        logger.exception("Validation error while processing message")
        error_text = f"Validation error: {str(ve)[:80]}"
        ack = build_ack(msg, ack_code="AE", text=error_text)
        if log:
            log.status = "error"
            log.ack_payload = ack
        return ack

    except Exception as e:
        logger.exception("Critical error during message processing")
        error_text = f"System error: {str(e)[:100]}"
        ack = build_ack(msg, ack_code="AR", text=error_text)
        try:
            error_log = MessageLog(
                direction="in",
                kind="MLLP",
                endpoint_id=endpoint.id if endpoint else None,
                correlation_id=msh.get("control_id", ""),
                message_type=f"{msg_family}^{trigger}",
                status="error",
                payload=msg,
                ack_payload=ack,
                created_at=datetime.utcnow(),
            )
            session.add(error_log)
            session.commit()
        except Exception:
            logger.exception("Failed to write error MessageLog")
        return ack


class _OnMessageInboundCallable:
    """Callable and awaitable wrapper for on_message_inbound.

    Allows existing sync tests to call `on_message_inbound(msg, session, endpoint)`
    and get a dict result, while also being awaitable for async tests that do
    `await on_message_inbound(msg, session, endpoint)`.
    """
    def __init__(self, async_callable):
        self._async = async_callable

    def __call__(self, msg: str, session, endpoint=None):
        """Sync call path: run the async handler in a new event loop."""
        import asyncio

        # Create the coroutine
        coro = self._async(msg, session, endpoint)
        try:
            # If there's an existing running loop, return the coroutine so
            # the caller (an async test or async code path) can await it.
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop: safe to run and return the sync-compatible dict
            ack = asyncio.run(coro)
            if isinstance(ack, str) and "MSA|AA" in ack:
                return {"status": "success", "ack": ack}
            else:
                return {"status": "error", "ack": ack}
        else:
            # Return coroutine to be awaited by caller
            return coro

    def __await__(self):
        # Support `await on_message_inbound(...)` usage by returning the
        # coroutine's awaitable. This method will be called when the
        # instance is awaited; but we must capture the parameters.
        raise TypeError("Use 'await on_message_inbound_async(msg, session, endpoint)' instead")


# Keep the explicit async function for awaited usage and for internal calls
on_message_inbound = _OnMessageInboundCallable(on_message_inbound_async)

# Also export the async function directly for tests that want to await it
__all__ = ["on_message_inbound_async", "on_message_inbound"]
