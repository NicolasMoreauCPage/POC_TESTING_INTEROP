"""Parser ADT messages HL7 v2.5 pour extraction entités Patient/Dossier/Mouvement.

Utilisé pour réimporter messages ADT dans un nouveau contexte GHT.
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from sqlmodel import Session, select
from app.models import Patient, Dossier, Venue, Mouvement, DossierType
from app.models_identifiers import Identifier, IdentifierType
from app.models_structure_fhir import IdentifierNamespace
from app.db import get_next_sequence

def parse_hl7_date(hl7_date: Optional[str]) -> Optional[str]:
    """Parse date HL7 (YYYYMMDD ou YYYYMMDDHHmmss) vers format ISO YYYY-MM-DD."""
    if not hl7_date or len(hl7_date) < 8:
        return None
    # Prendre les 8 premiers caractères (YYYYMMDD)
    date_part = hl7_date[:8]
    try:
        dt = datetime.strptime(date_part, "%Y%m%d")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None

def parse_hl7_datetime(hl7_datetime: Optional[str]) -> Optional[datetime]:
    """Parse datetime HL7 (YYYYMMDDHHmmss) vers datetime Python."""
    if not hl7_datetime or len(hl7_datetime) < 8:
        return None
    try:
        # Tenter avec secondes
        if len(hl7_datetime) >= 14:
            return datetime.strptime(hl7_datetime[:14], "%Y%m%d%H%M%S")
        # Sinon juste la date
        return datetime.strptime(hl7_datetime[:8], "%Y%m%d")
    except Exception:
        return None

def parse_cx_identifier(cx: str) -> Tuple[str, str, str]:
    """Parse composant CX (format: ID^^^AUTHORITY&OID&ISO^TYPE).
    
    Returns:
        (value, authority_name, oid)
    """
    parts = cx.split("^")
    value = parts[0] if len(parts) > 0 else ""
    authority = ""
    oid = ""
    if len(parts) > 3:
        auth_parts = parts[3].split("&")
        authority = auth_parts[0] if len(auth_parts) > 0 else ""
        oid = auth_parts[1] if len(auth_parts) > 1 else ""
    return (value, authority, oid)

def parse_adt_message(message: str) -> Dict[str, Any]:
    """Parse message ADT complet et extrait segments structurés.
    
    Returns:
        Dict avec clés: msh, pid, pv1, zbe (si présent)
    """
    segments = [s.strip() for s in message.split("\r") if s.strip()]
    result = {}
    
    for seg in segments:
        fields = seg.split("|")
        seg_type = fields[0]
        
        if seg_type == "MSH":
            result["msh"] = {
                "trigger_event": fields[8].split("^")[1] if len(fields) > 8 else "",
                "timestamp": parse_hl7_datetime(fields[6]) if len(fields) > 6 else None,
                "control_id": fields[9] if len(fields) > 9 else ""
            }
        
        elif seg_type == "PID":
            # PID-3: identifiants (multiple via ~)
            pid_3 = fields[3] if len(fields) > 3 else ""
            identifiers = []
            for cx in pid_3.split("~"):
                if cx:
                    value, authority, oid = parse_cx_identifier(cx)
                    identifiers.append({"value": value, "authority": authority, "oid": oid})
            
            # PID-5: nom (Family^Given)
            pid_5 = fields[5] if len(fields) > 5 else ""
            name_parts = pid_5.split("^")
            family = name_parts[0] if len(name_parts) > 0 else ""
            given = name_parts[1] if len(name_parts) > 1 else ""
            
            result["pid"] = {
                "identifiers": identifiers,
                "family": family,
                "given": given,
                "birth_date": parse_hl7_date(fields[7]) if len(fields) > 7 else None,
                "gender": fields[8] if len(fields) > 8 else ""
            }
        
        elif seg_type == "PV1":
            # PV1-2: patient class
            # PV1-19: visit number (NDA)
            pv1_19 = fields[19] if len(fields) > 19 else ""
            visit_id_parts = parse_cx_identifier(pv1_19) if pv1_19 else ("", "", "")
            
            # PV1-44: admit time
            admit_time = parse_hl7_datetime(fields[44]) if len(fields) > 44 else None
            
            result["pv1"] = {
                "patient_class": fields[2] if len(fields) > 2 else "I",
                "location": fields[3] if len(fields) > 3 else "",
                "visit_number": visit_id_parts[0],
                "admit_time": admit_time
            }
        
        elif seg_type == "ZBE":
            # ZBE-1: mouvement ID
            # ZBE-2: date/heure mouvement
            # ZBE-4: action (INSERT/UPDATE/CANCEL)
            result["zbe"] = {
                "movement_id": fields[1] if len(fields) > 1 else "",
                "when": parse_hl7_datetime(fields[2]) if len(fields) > 2 else None,
                "action": fields[4] if len(fields) > 4 else "INSERT"
            }
    
    return result

def import_adt_into_ght(
    message: str,
    session: Session,
    ght_id: int,
    ej_id: Optional[int] = None
) -> Dict[str, Any]:
    """Importe un message ADT dans un GHT cible.
    
    Crée Patient + Dossier + Venue + Mouvement selon le contenu du message.
    
    Returns:
        Dict avec clés: patient_id, dossier_id, mouvement_id, status
    """
    parsed = parse_adt_message(message)
    
    if "pid" not in parsed or "pv1" not in parsed:
        return {"status": "error", "error": "Segments PID ou PV1 manquants"}
    
    pid_data = parsed["pid"]
    pv1_data = parsed["pv1"]
    msh_data = parsed.get("msh", {})
    zbe_data = parsed.get("zbe")
    
    # Charger namespaces cible
    namespaces = session.exec(
        select(IdentifierNamespace).where(IdentifierNamespace.ght_context_id == ght_id)
    ).all()
    ns_by_type = {ns.type: ns for ns in namespaces}
    
    # Chercher patient existant par identifiant (premier identifiant)
    patient = None
    if pid_data["identifiers"]:
        first_id = pid_data["identifiers"][0]
        existing_ident = session.exec(
            select(Identifier).where(Identifier.value == first_id["value"])
        ).first()
        if existing_ident:
            patient = existing_ident.patient
    
    # Créer patient si absent
    if not patient:
        patient = Patient(
            family=pid_data["family"],
            given=pid_data["given"],
            birth_date=pid_data["birth_date"],
            gender=pid_data["gender"],
            identity_reliability_code="VALI",
            country="FR"
        )
        session.add(patient)
        session.commit()
        session.refresh(patient)
        
        # Créer identifiants patient (IPP)
        ipp_ns = ns_by_type.get("IPP") or ns_by_type.get("IPP-RT")
        if ipp_ns and pid_data["identifiers"]:
            for id_info in id_info["identifiers"]:
                ident = Identifier(
                    patient_id=patient.id,
                    type=IdentifierType.IPP,
                    value=id_info["value"],
                    system=ipp_ns.system,
                    oid=ipp_ns.system.split(":")[-1],
                    status="active"
                )
                session.add(ident)
        session.commit()
    
    # Chercher dossier existant par NDA
    dossier = None
    if pv1_data["visit_number"]:
        existing_dossier_id = session.exec(
            select(Identifier).where(
                Identifier.value == pv1_data["visit_number"],
                Identifier.dossier_id.isnot(None)
            )
        ).first()
        if existing_dossier_id:
            dossier = existing_dossier_id.dossier
    
    # Créer dossier si absent
    if not dossier:
        dossier = Dossier(
            dossier_seq=get_next_sequence(session, "dossier"),
            patient_id=patient.id,
            dossier_type=DossierType.HOSPITALISE,
            admit_time=pv1_data["admit_time"] or datetime.utcnow(),
            uf_responsabilite="UF-IMPORT"
        )
        session.add(dossier)
        session.commit()
        session.refresh(dossier)
        
        # Créer identifiant NDA
        nda_ns = ns_by_type.get("NDA") or ns_by_type.get("NDA-RT")
        if nda_ns and pv1_data["visit_number"]:
            ident = Identifier(
                dossier_id=dossier.id,
                namespace_id=nda_ns.id,
                value=pv1_data["visit_number"],
                system=nda_ns.system
            )
            session.add(ident)
        session.commit()
    
    # Créer venue (simplifiée)
    venue = Venue(
        venue_seq=get_next_sequence(session, "venue"),
        dossier_id=dossier.id,
        uf_responsabilite=dossier.uf_responsabilite,
        start_time=pv1_data["admit_time"] or datetime.utcnow(),
        code=pv1_data["location"] or "IMPORT",
        operational_status="active"
    )
    session.add(venue)
    session.commit()
    session.refresh(venue)
    
    # Créer mouvement si ZBE présent
    mouvement_id = None
    if zbe_data:
        mouvement = Mouvement(
            mouvement_seq=get_next_sequence(session, "mouvement"),
            venue_id=venue.id,
            when=zbe_data["when"] or datetime.utcnow(),
            location=pv1_data["location"] or "IMPORT",
            trigger_event=msh_data.get("trigger_event", "A01"),
            movement_type="Import"
        )
        session.add(mouvement)
        session.commit()
        session.refresh(mouvement)
        mouvement_id = mouvement.id
    
    return {
        "status": "success",
        "patient_id": patient.id,
        "dossier_id": dossier.id,
        "mouvement_id": mouvement_id
    }
