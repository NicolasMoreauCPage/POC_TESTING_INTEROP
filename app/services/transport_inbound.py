# app/services/transport_inbound.py
from datetime import datetime
from typing import Optional
import logging

from sqlmodel import select

from app.models_endpoints import MessageLog
from app.services.mllp import parse_msh_fields, build_ack
from app.models import Patient, Dossier, Venue, Mouvement
from app.db import get_next_sequence
from app.services.emit_on_create import emit_to_senders
from app.state_transitions import is_valid_transition

logger = logging.getLogger("transport_inbound")


def _parse_pid(message: str) -> dict:
    """Parse minimal PID fields from an HL7 message.
    Returns a dict with keys: external_id, family, given, birth_date, gender.
    This is intentionally small and tolerant (POC).
    """
    out = {
        "external_id": "",
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
        "phone": None,
        "email": None,
        "ssn": None,
        "marital_status": None,
        "mothers_maiden_name": None,
        "race": None,
    }
    try:
        lines = message.split("\r")
        pid = next((l for l in lines if l.startswith("PID")), None)
        if not pid:
            return out
        parts = pid.split("|")
        # HL7 PID fields: 3=PatientIdentifierList, 5=PatientName, 7=BirthDate, 8=Gender
        if len(parts) > 3 and parts[3]:
            # take first identifier component (before ^)
            out["external_id"] = parts[3].split("~")[0].split("^")[0]
        if len(parts) > 5 and parts[5]:
            name_comp = parts[5].split("^")
            out["family"] = name_comp[0] if len(name_comp) > 0 else ""
            out["given"] = name_comp[1] if len(name_comp) > 1 else ""
            out["middle"] = name_comp[2] if len(name_comp) > 2 else None
            out["suffix"] = name_comp[3] if len(name_comp) > 3 else None
            out["prefix"] = name_comp[4] if len(name_comp) > 4 else None
        if len(parts) > 7 and parts[7]:
            out["birth_date"] = parts[7]
        if len(parts) > 8 and parts[8]:
            out["gender"] = parts[8]
        # PID-11 = Patient Address (XAD) -> street^other^city^state^zip^country
        if len(parts) > 11 and parts[11]:
            addr = parts[11].split("^")
            out["address"] = addr[0] if len(addr) > 0 and addr[0] else None
            out["city"] = addr[2] if len(addr) > 2 and addr[2] else None
            out["state"] = addr[3] if len(addr) > 3 and addr[3] else None
            out["postal_code"] = addr[4] if len(addr) > 4 and addr[4] else None
        # PID-13 = Phone
        if len(parts) > 13 and parts[13]:
            out["phone"] = parts[13].split("^")[0]
        # PID-19 = SSN (or national id) and PID-16 marital status, PID-6 mother's maiden name, PID-10 race
        if len(parts) > 19 and parts[19]:
            out["ssn"] = parts[19]
        if len(parts) > 16 and parts[16]:
            out["marital_status"] = parts[16]
        if len(parts) > 6 and parts[6]:
            out["mothers_maiden_name"] = parts[6].split("^")[0]
        if len(parts) > 10 and parts[10]:
            out["race"] = parts[10]
    except Exception:
        pass
    return out


def _parse_pd1(message: str) -> dict:
    """Parse PD1 segment for a couple of useful POC fields.
    Returns dict with keys: primary_care_provider, religion, language
    PD1 is optional; be tolerant.
    """
    out = {"primary_care_provider": None, "religion": None, "language": None}
    try:
        lines = message.split("\r")
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
            return datetime.strptime(s[: len(fmt.replace('%', '')) + 6], fmt)
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
    out = {"location": "", "hospital_service": "", "admit_time": None, "discharge_time": None, "patient_class": ""}
    try:
        lines = message.split("\r")
        pv1 = next((l for l in lines if l.startswith("PV1")), None)
        if not pv1:
            return out
        parts = pv1.split("|")
        # PV1 fields commonly: 2=patient class, 3=assigned patient location, 10=hospital service
        if len(parts) > 2 and parts[2]:
            out["patient_class"] = parts[2]
        if len(parts) > 3 and parts[3]:
            out["location"] = parts[3]
        if len(parts) > 10 and parts[10]:
            out["hospital_service"] = parts[10]
        # admit/discharge times
        if len(parts) > 44 and parts[44]:
            out["admit_time"] = _parse_hl7_datetime(parts[44])
        if len(parts) > 45 and parts[45]:
            out["discharge_time"] = _parse_hl7_datetime(parts[45])
    except Exception:
        pass
    return out


def _handle_z99_updates(message: str, session) -> None:
    """Look for Z99 segments with simple structured updates.

    Supported pattern (POC): Z99|Entity|seq|field|value
    where Entity in (Dossier, Venue, Mouvement)
    """
    try:
        lines = message.split("\r")
        for seg in [l for l in lines if l.startswith("Z99")]:
            parts = seg.split("|")
            if len(parts) < 4:
                continue
            entity = parts[1]
            seq = parts[2] if len(parts) > 2 else None
            field = parts[3] if len(parts) > 3 else None
            value = parts[4] if len(parts) > 4 else None
            if not entity or not seq:
                continue
            try:
                sid = int(seq)
            except Exception:
                continue
            if entity.lower().startswith("doss"):
                obj = session.exec(select(Dossier).where(Dossier.dossier_seq == sid)).first()
            elif entity.lower().startswith("ven"):
                obj = session.exec(select(Venue).where(Venue.venue_seq == sid)).first()
            elif entity.lower().startswith("mouv") or entity.lower().startswith("mvt"):
                obj = session.exec(select(Mouvement).where(Mouvement.mouvement_seq == sid)).first()
            else:
                obj = None
            if obj and field and value is not None:
                # apply if attribute exists
                if hasattr(obj, field):
                    setattr(obj, field, value)
                    session.add(obj)
                    session.commit()
    except Exception:
        logger.exception("Error handling Z99 updates")


async def on_message_inbound(msg: str, session, endpoint) -> str:
    """Receive an HL7 v2 message (deframed), optionally persist domain objects, and return an ACK.

    Notes:
    - `session` is a SQLModel Session provided by `session_factory()` from `app/db_session_factory.py`.
    - For ADT patient create/update messages (A04/A28/A08), this function will create a `Patient` record
      when possible. It uses `get_next_sequence(session, "patient")` to populate `patient_seq`.
    """
    try:
        f = parse_msh_fields(msg)
        ctrl_id = f.get("control_id", "")

        # Basic MSH-9 validation
        if not f.get("msg_type"):
            ack_code, text = "AE", "Missing/invalid MSH-9"
        else:
            ack_code, text = ("AA", "Message received") if ctrl_id else ("AE", "Missing MSH-10")

        # If ACK is OK, attempt domain persistence according to ADT triggers in an atomic transaction
        pid = _parse_pid(msg)
        pd1 = _parse_pd1(msg)
        if ack_code == "AA":
            comp = f.get("msg_type", "").split("^")
            msg_family = comp[0] if len(comp) > 0 else ""
            trigger = comp[1] if len(comp) > 1 else ""

            try:
                # Use a transaction span: domain objects + message log are committed atomically.
                with session.begin():
                    # --- Patient creation/update (A04/A08/A28) ---
                    if msg_family == "ADT" and trigger in ("A04", "A08", "A28"):
                        existing = None
                        if pid.get("external_id"):
                            existing = session.exec(
                                select(Patient).where(Patient.external_id == pid["external_id"])
                            ).first()
                        if existing:
                            logger.info(f"Patient exists (external_id={pid.get('external_id')}) -> id={existing.id}")
                        else:
                            seq = get_next_sequence(session, "patient")
                            p = Patient(
                                patient_seq=seq,
                                external_id=pid.get("external_id") or "",
                                family=pid.get("family") or "",
                                given=pid.get("given") or "",
                                middle=pid.get("middle"),
                                prefix=pid.get("prefix"),
                                suffix=pid.get("suffix"),
                                birth_date=pid.get("birth_date"),
                                gender=pid.get("gender"),
                                address=pid.get("address"),
                                city=pid.get("city"),
                                state=pid.get("state"),
                                postal_code=pid.get("postal_code"),
                                phone=pid.get("phone"),
                                ssn=pid.get("ssn"),
                                marital_status=pid.get("marital_status"),
                                mothers_maiden_name=pid.get("mothers_maiden_name"),
                                race=pid.get("race"),
                                religion=pd1.get("religion") if pd1 else None,
                                primary_care_provider=pd1.get("primary_care_provider") if pd1 else None,
                            )
                            session.add(p)
                            session.flush()
                            session.refresh(p)
                            logger.info(f"Created Patient id={p.id} seq={p.patient_seq} external_id={p.external_id}")

                    # parse PV1 for dossier/venue/mouvement mapping
                    pv1 = _parse_pv1(msg)

                    # --- Dossier & Venue (A01/A04/A05) ---
                    dossier_obj = None
                    venue_obj = None
                    if msg_family == "ADT" and trigger in ("A01", "A04", "A05"):
                        # find patient
                        patient_obj = None
                        if pid.get("external_id"):
                            patient_obj = session.exec(
                                select(Patient).where(Patient.external_id == pid["external_id"])
                            ).first()
                        if not patient_obj:
                            logger.warning("No patient found for Dossier creation; skipping Dossier/Venue creation")
                        else:
                            if pv1.get("admit_time"):
                                dossier_obj = session.exec(
                                    select(Dossier).where(
                                        Dossier.patient_id == patient_obj.id,
                                        Dossier.admit_time == pv1.get("admit_time")
                                    )
                                ).first()
                            if not dossier_obj:
                                dseq = get_next_sequence(session, "dossier")
                                dossier_obj = Dossier(
                                    dossier_seq=dseq,
                                    patient_id=patient_obj.id,
                                    uf_responsabilite=pv1.get("hospital_service") or pv1.get("location") or "",
                                    admit_time=pv1.get("admit_time") or datetime.utcnow(),
                                    discharge_time=pv1.get("discharge_time"),
                                )
                                session.add(dossier_obj)
                                session.flush()
                                session.refresh(dossier_obj)
                                logger.info(f"Created Dossier id={dossier_obj.id} seq={dossier_obj.dossier_seq}")

                            # Venue
                            if dossier_obj:
                                if pv1.get("admit_time"):
                                    venue_obj = session.exec(
                                        select(Venue).where(
                                            Venue.dossier_id == dossier_obj.id,
                                            Venue.start_time == pv1.get("admit_time")
                                        )
                                    ).first()
                                if not venue_obj:
                                    vseq = get_next_sequence(session, "venue")
                                    venue_obj = Venue(
                                        venue_seq=vseq,
                                        dossier_id=dossier_obj.id,
                                        uf_responsabilite=dossier_obj.uf_responsabilite,
                                        start_time=pv1.get("admit_time") or dossier_obj.admit_time,
                                        code=(pv1.get("location") or "")[:64],
                                        label=(pv1.get("location") or ""),
                                    )
                                    session.add(venue_obj)
                                    session.flush()
                                    session.refresh(venue_obj)
                                    logger.info(f"Created Venue id={venue_obj.id} seq={venue_obj.venue_seq}")

                    # --- Movements (A01,A04,A06,A02,A21,A22,A54) ---
                    movement_triggers = ("A01", "A04", "A06", "A02", "A21", "A22", "A54")
                    if msg_family == "ADT" and trigger in movement_triggers:
                        # ensure we have a venue to attach to
                        if not venue_obj:
                            # try to find a venue for this patient and admit_time
                            if pid.get("external_id"):
                                patient_obj = session.exec(
                                    select(Patient).where(Patient.external_id == pid["external_id"])
                                ).first()
                                if patient_obj and pv1.get("admit_time"):
                                    d = session.exec(
                                        select(Dossier).where(Dossier.patient_id == patient_obj.id, Dossier.admit_time == pv1.get("admit_time"))
                                    ).first()
                                    if d:
                                        venue_obj = session.exec(
                                            select(Venue).where(Venue.dossier_id == d.id, Venue.start_time == pv1.get("admit_time"))
                                        ).first()
                        if not venue_obj:
                            # fallback: create minimal venue linked to dossier if any
                            dossier_for_venue = None
                            if pid.get("external_id"):
                                patient_obj = session.exec(
                                    select(Patient).where(Patient.external_id == pid["external_id"])
                                ).first()
                                if patient_obj:
                                    dossier_for_venue = session.exec(
                                        select(Dossier).where(Dossier.patient_id == patient_obj.id).order_by(Dossier.id.desc())
                                    ).first()
                            if dossier_for_venue:
                                vseq = get_next_sequence(session, "venue")
                                venue_obj = Venue(
                                    venue_seq=vseq,
                                    dossier_id=dossier_for_venue.id,
                                    uf_responsabilite=dossier_for_venue.uf_responsabilite,
                                    start_time=pv1.get("admit_time") or datetime.utcnow(),
                                )
                                session.add(venue_obj)
                                session.flush()
                                session.refresh(venue_obj)
                        if venue_obj:
                            mseq = get_next_sequence(session, "mouvement")
                            mv = Mouvement(
                                mouvement_seq=mseq,
                                venue_id=venue_obj.id,
                                type=trigger,
                                when=pv1.get("admit_time") or datetime.utcnow(),
                                location=pv1.get("location"),
                            )
                            session.add(mv)
                            session.flush()
                            session.refresh(mv)
                            logger.info(f"Created Mouvement id={mv.id} seq={mv.mouvement_seq} on venue={venue_obj.id}")

                    # --- Z99 handling (modifications) ---
                    _handle_z99_updates(msg, session)

                    # MessageLog is created inside the same transaction so the whole processing is atomic
                    log = MessageLog(
                        direction="in",
                        kind="MLLP",
                        endpoint_id=(getattr(endpoint, "id", None)),
                        correlation_id=ctrl_id or "",
                        status="ack_ok",
                        payload=msg,
                        ack_payload="",
                        created_at=datetime.utcnow(),
                    )
                    session.add(log)

                    # commit happens automatically on successful exit of session.begin()
                # After successful transaction, emit outbound messages for created/updated entities
                try:
                    # prefer using in-memory references when available, else re-query
                    if 'p' in locals() and p:
                        emit_to_senders(p, "patient", session)
                    else:
                        if pid.get("external_id"):
                            patient_obj = session.exec(select(Patient).where(Patient.external_id == pid["external_id"])) .first()
                            if patient_obj:
                                emit_to_senders(patient_obj, "patient", session)

                    if 'dossier_obj' in locals() and dossier_obj:
                        emit_to_senders(dossier_obj, "dossier", session)
                    if 'venue_obj' in locals() and venue_obj:
                        emit_to_senders(venue_obj, "venue", session)
                    if 'mv' in locals() and mv:
                        emit_to_senders(mv, "mouvement", session)
                except Exception:
                    logger.exception("emit_to_senders failed")
            except Exception as e:
                # rollback occurred; log error and return AE
                logger.exception(f"Persistence error during domain processing: {e}")
                # best-effort: write a MessageLog entry describing the error (outside transaction)
                try:
                    err_ack = build_ack(msg, ack_code="AE", text=str(e)[:80])
                    log = MessageLog(
                        direction="in",
                        kind="MLLP",
                        endpoint_id=(getattr(endpoint, "id", None)),
                        correlation_id=ctrl_id or "",
                        status="ack_error",
                        payload=msg,
                        ack_payload=err_ack,
                        created_at=datetime.utcnow(),
                    )
                    session.add(log)
                    session.commit()
                except Exception:
                    logger.exception("Failed to write error MessageLog after rollback")
                # change ack info
                ack_code, text = "AE", f"Persistence error: {str(e)[:80]}"

        # Validation des transitions d'état pour les dossiers
        if msg_family == "ADT" and dossier_obj:
            current_state = dossier_obj.current_state or "Pas de venue courante"
            if not is_valid_transition(current_state, trigger):
                logger.warning(f"Transition invalide: état actuel={current_state}, trigger={trigger}")
                ack_code, text = "AE", f"Transition invalide: état actuel={current_state}, trigger={trigger}"
            else:
                dossier_obj.current_state = trigger
                session.add(dossier_obj)

        ack = build_ack(msg, ack_code=ack_code, text=text)

        log = MessageLog(
            direction="in",
            kind="MLLP",
            endpoint_id=(getattr(endpoint, "id", None)),
            correlation_id=ctrl_id or "",
            status="ack_ok" if ack_code == "AA" else "ack_error",
            payload=msg,
            ack_payload=ack,
            created_at=datetime.utcnow(),
        )
        session.add(log)
        session.commit()
        return ack

    except Exception as e:
        # On failure, attempt a generic AE ACK and best-effort log
        logger.exception(f"Unhandled error in on_message_inbound: {e}")
        ack = build_ack("MSH|^~\\\&||||||||||P|2.5", ack_code="AE", text=str(e)[:80])
        try:
            log = MessageLog(
                direction="in", kind="MLLP", endpoint_id=(getattr(endpoint, "id", None)),
                correlation_id="", status="ack_error",
                payload=msg, ack_payload=ack, created_at=datetime.utcnow()
            )
            session.add(log)
            session.commit()
        except Exception:
            pass
        return ack
