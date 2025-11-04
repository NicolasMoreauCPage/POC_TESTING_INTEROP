import asyncio
import json
from typing import Literal, Sequence, Tuple

from sqlmodel import Session, select

from app.models import Patient, Dossier, Venue, Mouvement
from app.models_endpoints import SystemEndpoint, MessageLog, FHIRConfig
from app.models_identifiers import Identifier, IdentifierType
from app.services.fhir import generate_fhir_bundle_for_dossier
from app.services.fhir_transport import post_fhir_bundle as send_fhir
from app.services.mllp import send_mllp


def build_pid3_identifiers(patient: Patient, session: Session, forced_system: str = None) -> str:
    """
    Construit PID-3 avec TOUS les identifiants du patient (répétitions avec ~).
    
    Format HL7 v2.5 PID-3: ID1^^^SYSTEM1^TYPE~ID2^^^SYSTEM2^TYPE~...
    
    Ordre des identifiants:
    1. IPP (patient_seq) - identifiant interne principal
    2. External ID si présent
    3. NIR (Sécurité sociale) si présent
    4. Tous les autres identifiants actifs de la table Identifier
    
    Args:
        patient: Instance Patient
        session: Session DB pour requêter les Identifier
        forced_system: Système forcé pour IPP (si None, utilise "HOSP")
    
    Returns:
        String PID-3 avec répétitions ~ entre identifiants
    
    Exemple:
        "1001^^^HOSP^PI~EXT123^^^EXTERNAL_SYS^PI~1234567890123^^^INS-NIR^NH"
    """
    identifiers = []
    
    # 1. IPP (patient_seq) - TOUJOURS en premier si présent
    if patient.patient_seq:
        system = forced_system or "HOSP"
        identifiers.append(f"{patient.patient_seq}^^^{system}^PI")
    
    # 2. External ID si présent - chercher dans Identifier pour avoir system/oid
    if patient.external_id:
        # Chercher si cet external_id est dans la table Identifier
        ext_ident = session.exec(
            select(Identifier)
            .where(Identifier.patient_id == patient.id)
            .where(Identifier.value == patient.external_id)
            .where(Identifier.status == "active")
        ).first()
        
        if ext_ident:
            # Utiliser system/oid de l'Identifier
            identifiers.append(f"{ext_ident.value}^^^{ext_ident.system}^{ext_ident.type}")
        else:
            # Fallback: external_id sans système connu
            identifiers.append(f"{patient.external_id}^^^EXTERNAL^PI")
    
    # 3. NIR (Sécurité sociale) si présent
    if patient.nir:
        # NH = National Health ID (HL7 Table 0203)
        identifiers.append(f"{patient.nir}^^^INS-NIR^NH")
    
    # 4. Tous les autres identifiants actifs
    # Exclure ceux déjà ajoutés (patient_seq, external_id, nir)
    already_added_values = set()
    if patient.patient_seq:
        already_added_values.add(str(patient.patient_seq))
    if patient.external_id:
        already_added_values.add(patient.external_id)
    if patient.nir:
        already_added_values.add(patient.nir)
    
    # Charger explicitement les identifiers si pas encore chargés
    if not patient.identifiers:
        patient.identifiers = session.exec(
            select(Identifier).where(Identifier.patient_id == patient.id)
        ).all()
    
    for ident in patient.identifiers:
        if ident.status == "active" and ident.value not in already_added_values:
            # Format: value^^^system^type
            # Si OID présent, on pourrait l'ajouter: value^^^system&OID&ISO^type
            identifiers.append(f"{ident.value}^^^{ident.system}^{ident.type}")
            already_added_values.add(ident.value)
    
    # Joindre avec ~ (répétition HL7)
    return "~".join(identifiers) if identifiers else ""


def generate_pam_hl7(
    entity,
    entity_type: Literal["patient", "dossier", "venue", "mouvement"],
    session: Session,
    forced_identifier_system: str | None = None,
    forced_identifier_oid: str | None = None,
    operation: str = "insert",
) -> str:
    """Build a minimal HL7 PAM message for the given entity type."""
    if entity_type == "patient":
        # Determine event type based on operation
        if operation == "update":
            event_type = "A31"  # ADT^A31 (Update person information)
        else:
            event_type = "A04"  # ADT^A04 (Register patient) - new patient created
        
        # Build timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        control_id = str(getattr(entity, "patient_seq", getattr(entity, "id", "UNKNOWN")))
        
        # MSH segment
        msh = f"MSH|^~\\&|POC|HOSP|EXT|HOSP|{timestamp}||ADT^{event_type}|{control_id}|P|2.5"
        
        # EVN segment
        evn = f"EVN|{event_type}|{timestamp}"
        
        # PID segment - avec identifiants multiples et PID-32
        # PID-3: Identifiants patient (répétitions ~)
        pid3 = build_pid3_identifiers(entity, session, forced_identifier_oid or forced_identifier_system)
        
        # PID-5: Noms du patient (XPN, multi-valué)
        # Répétition 1 : nom usuel, Répétition 2 : nom de naissance (si différent)
        names = []
        family = entity.family or ""
        given = entity.given or ""
        middle = getattr(entity, "middle", "") or ""
        # Nom usuel (usage D)
        name_usuel = f"{family}^{given}^{middle}^^^^D" if middle else f"{family}^{given}^^^^D"
        names.append(name_usuel)
        # Nom de naissance (usage L) si présent et différent
        birth_family = getattr(entity, "birth_family", None)
        if birth_family and birth_family != family:
            name_naissance = f"{birth_family}^{given}^{middle}^^^^L" if middle else f"{birth_family}^{given}^^^^L"
            names.append(name_naissance)
        # TODO: Ajouter d'autres alias si besoin
        name = "~".join(names)
        
        # PID-7: Date de naissance
        birth_date = entity.birth_date or ""
        
        # PID-8: Sexe administratif
        gender = entity.gender or ""
        
        # PID-11: Adresses du patient (XAD, multi-valué)
        addresses = []
        # Adresse d'habitation
        addr1 = [
            getattr(entity, "address", "") or "",
            "",  # other designation
            getattr(entity, "city", "") or "",
            getattr(entity, "state", "") or "",
            getattr(entity, "postal_code", "") or "",
            getattr(entity, "country", "") or ""
        ]
        addresses.append("^".join(addr1))
        # Adresse de naissance (si présente)
        if getattr(entity, "birth_address", None) or getattr(entity, "birth_city", None):
            addr2 = [
                getattr(entity, "birth_address", "") or "",
                "",  # other designation
                getattr(entity, "birth_city", "") or "",
                getattr(entity, "birth_state", "") or "",
                getattr(entity, "birth_postal_code", "") or "",
                getattr(entity, "birth_country", "") or ""
            ]
            addresses.append("^".join(addr2))
        # TODO: Ajouter d'autres adresses si besoin
        patient_address = "~".join(addresses)
        
        # PID-13: Téléphones (XTN, multi-valué)
        phones = []
        phone = getattr(entity, "phone", "") or ""
        if phone:
            phones.append(phone)
        # Ajout d'autres téléphones si présents (mobile, pro...)
        if hasattr(entity, "mobile") and getattr(entity, "mobile"):
            phones.append(getattr(entity, "mobile"))
        if hasattr(entity, "work_phone") and getattr(entity, "work_phone"):
            phones.append(getattr(entity, "work_phone"))
        # TODO: Ajouter d'autres XTN si besoin
        phone_field = "~".join(phones)
        
        # PID-23: Lieu de naissance (ville)
        birth_place = getattr(entity, "birth_city", "") or ""
        
        # PID-32: Statut de l'identité (Identity Reliability Code) - HL7 Table 0445
        # VIDE/PROV/VALI/DOUTE/FICTI
        identity_code = getattr(entity, "identity_reliability_code", "") or ""
        
        # Construction du segment PID complet HL7 v2.5
        # Format: PID|SetID|PatientID|PatientIDList|AltPatientID|PatientName|MothersMaidenName|
        #            DateOfBirth|Sex|PatientAlias|Race|PatientAddress|CountryCode|PhoneNumber|
        #            BusinessPhone|PrimaryLanguage|MaritalStatus|Religion|AccountNumber|SSN|
        #            DriversLicense|MothersIdentifier|EthnicGroup|BirthPlace|MultipleBirth|
        #            BirthOrder|Citizenship|VeteranStatus|Nationality|PatientDeathDate|DeathIndicator|
        #            IdentityUnknownIndicator|IdentityReliabilityCode
        # PID-1 à PID-13 remplis, PID-14 à PID-22 vides (9 pipes), PID-23 birth_place, PID-24 à PID-31 vides (8 pipes), PID-32 identity_code
        # Note: chaque champ est séparé par |, donc: ...|{phone}||||||||||{birth_place}|||||||||{identity_code}
        pid = f"PID|1||{pid3}||{name}||{birth_date}|{gender}|||{patient_address}||{phone_field}||||||||||{birth_place}|||||||||{identity_code}"
        
        return "\r".join([msh, evn, pid])
        
    if entity_type == "dossier":
        # ADT^A01 (Admit patient) - new admission created
        assigning = forced_identifier_oid or forced_identifier_system or "HOSP"
        
        # Get patient info
        patient = entity.patient if hasattr(entity, 'patient') else None
        if patient:
            patient_id = patient.identifier or patient.external_id or str(patient.patient_seq)
            family = patient.family or ""
            given = patient.given or ""
            birth_date = patient.birth_date or ""
            gender = patient.gender or ""
        else:
            patient_id = str(entity.patient_id)
            family = ""
            given = ""
            birth_date = ""
            gender = ""
        
        pid3 = f"{patient_id}^^^{assigning}^PI"
        
        # Build timestamp
        admit_time = entity.admit_time.strftime("%Y%m%d%H%M%S") if entity.admit_time else ""
        control_id = str(entity.dossier_seq)
        
        # MSH segment
        msh = f"MSH|^~\\&|POC|HOSP|EXT|HOSP|{admit_time}||ADT^A01|{control_id}|P|2.5"
        
        # EVN segment
        evn = f"EVN|A01|{admit_time}"
        
        # PID segment
        pid = f"PID|1||{pid3}||{family}^{given}||{birth_date}|{gender}"
        
        # PV1 segment
        patient_class = "I"  # Inpatient
        location = entity.uf_responsabilite or ""
        pv1 = f"PV1|1|{patient_class}|{location}|||||||||||||{control_id}|||||||||||||||||||{location}||||||{admit_time}"
        
        return "\r".join([msh, evn, pid, pv1])
    if entity_type == "venue":
        return (
            f"MSH|^~\\&|POC|HOSP|EXT|HOSP|{entity.start_time or ''}||Z99^Z99|{entity.id}|P|2.5\n"
            f"Z99|VENUE|{entity.venue_seq}|{entity.code}|{entity.label}"
        )
    if entity_type == "mouvement":
        # Extract event type from mouvement.type (format: "ADT^A01" or "ADT^A01^ADT_A01")
        msg_type = entity.type if entity.type else "ADT^A99"
        
        # Get venue and patient info
        venue = entity.venue if hasattr(entity, 'venue') else None
        dossier = venue.dossier if venue and hasattr(venue, 'dossier') else None
        patient = dossier.patient if dossier and hasattr(dossier, 'patient') else None
        
        # Build timestamp
        timestamp = entity.when.strftime("%Y%m%d%H%M%S") if entity.when else ""
        
        # Build MSH segment
        control_id = str(entity.mouvement_seq)
        msh = f"MSH|^~\\&|POC|HOSP|EXT|HOSP|{timestamp}||{msg_type}|{control_id}|P|2.5"
        
        # Build EVN segment (extract event code from msg_type)
        event_code = msg_type.split("^")[1] if "^" in msg_type else "A99"
        evn = f"EVN|{event_code}|{timestamp}"
        
        # Build PID segment if we have patient info
        if patient:
            assigning = forced_identifier_oid or forced_identifier_system or "HOSP"
            patient_id = patient.identifier or patient.external_id or str(patient.id)
            pid3 = f"{patient_id}^^^{assigning}^PI"
            family = patient.family or ""
            given = patient.given or ""
            birth_date = patient.birth_date or ""
            gender = patient.gender or ""
            pid = f"PID|1||{pid3}||{family}^{given}||{birth_date}|{gender}"
        else:
            pid = f"PID|1||UNKNOWN^^^{forced_identifier_oid or 'HOSP'}^PI||UNKNOWN^UNKNOWN||||"
        
        # Build PV1 segment
        patient_class = "I"  # Inpatient by default
        location = entity.location or entity.to_location or ""
        if venue:
            uf_resp = venue.uf_responsabilite or ""
        elif dossier:
            uf_resp = dossier.uf_responsabilite or ""
        else:
            uf_resp = ""
        
        # PV1-19 (Visit Number) - use venue_seq if available
        visit_number = ""
        if venue:
            visit_number = str(venue.venue_seq)
        
        pv1 = f"PV1|1|{patient_class}|{location}|||||||||||||||{visit_number}||||||||||||||||||||{uf_resp}||||||{timestamp}"
        
        # Combine all segments with \r separator (HL7 standard)
        return "\r".join([msh, evn, pid, pv1])
    
    return ""


def generate_fhir(
    entity,
    entity_type: Literal["patient", "dossier", "venue", "mouvement"],
    session: Session,
    forced_identifier_system: str | None = None,
    forced_identifier_oid: str | None = None,
):
    """Build a minimal FHIR payload for the entity."""
    if entity_type == "dossier":
        return generate_fhir_bundle_for_dossier(entity)

    if entity_type == "patient":
        identifiers = [{"value": str(entity.patient_seq)}]
        if getattr(entity, "ssn", None):
            identifiers.append({"system": "urn:ssn", "value": entity.ssn})
        if forced_identifier_system:
            new_ids = []
            for iid in identifiers:
                new = iid if iid.get("system") else {**iid, "system": forced_identifier_system}
                if forced_identifier_oid:
                    new = {**new, "assigner": {"identifier": {"value": forced_identifier_oid}}}
                new_ids.append(new)
            identifiers = new_ids

        name = {"family": entity.family, "given": [entity.given]}
        if getattr(entity, "middle", None):
            name["given"].append(entity.middle)
        if getattr(entity, "prefix", None):
            name["prefix"] = [entity.prefix]
        if getattr(entity, "suffix", None):
            name["suffix"] = [entity.suffix]

        patient_res = {
            "resourceType": "Patient",
            "id": str(entity.id),
            "identifier": identifiers,
            "name": [name],
            "gender": entity.gender,
            "birthDate": entity.birth_date,
        }
        if getattr(entity, "phone", None):
            patient_res.setdefault("telecom", []).append({"system": "phone", "value": entity.phone})
        if getattr(entity, "address", None) or getattr(entity, "city", None):
            patient_res.setdefault("address", []).append(
                {
                    "line": [getattr(entity, "address", None)] if getattr(entity, "address", None) else [],
                    "city": getattr(entity, "city", None),
                    "state": getattr(entity, "state", None),
                    "postalCode": getattr(entity, "postal_code", None),
                }
            )
        if getattr(entity, "primary_care_provider", None):
            patient_res.setdefault("extension", []).append(
                {
                    "url": "http://example.org/fhir/StructureDefinition/primary-care-provider",
                    "valueString": entity.primary_care_provider,
                }
            )
        return patient_res

    # POC fallback for venue/mouvement
    return {
        "resourceType": "Observation",
        "id": str(entity.id),
        "status": "final",
        "code": {"text": entity_type},
        "valueString": str(entity),
    }


def _build_fhir_targets(endpoint: SystemEndpoint) -> Sequence[Tuple[str, str, str | None]]:
    """Return (base_url, auth_kind, auth_token) tuples for an endpoint."""
    targets: list[Tuple[str, str, str | None]] = []

    # Prioritise explicit FHIR configs
    for cfg in getattr(endpoint, "fhir_configs", []) or []:
        if not isinstance(cfg, FHIRConfig):
            continue
        if not cfg.is_enabled or not cfg.base_url:
            continue
        targets.append((cfg.base_url, cfg.auth_kind or "none", cfg.auth_token))

    if targets:
        return targets

    host = (endpoint.host or "").strip()
    if not host:
        return targets

    if host.startswith(("http://", "https://")):
        base_url = host
        if endpoint.port and ":" not in host.split("//", 1)[1]:
            base_url = f"{host}:{endpoint.port}"
    else:
        scheme = "https" if str(endpoint.port) in {"443", "8443"} else "http"
        base_url = f"{scheme}://{host}"
        if endpoint.port:
            base_url = f"{base_url}:{endpoint.port}"

    targets.append((base_url, "none", None))
    return targets


async def emit_to_senders_async(
    entity,
    entity_type: Literal["patient", "dossier", "venue", "mouvement"],
    session: Session,
    operation: str = "insert",
) -> None:
    """Emit HL7/FHIR notifications for newly created or updated entities."""

    endpoints = session.exec(select(SystemEndpoint).where(SystemEndpoint.role == "sender")).all()
    sent_logs: list[MessageLog] = []

    for endpoint in endpoints:
        hl7_message = generate_pam_hl7(
            entity,
            entity_type,
            session,
            forced_identifier_system=getattr(endpoint, "forced_identifier_system", None),
            forced_identifier_oid=getattr(endpoint, "forced_identifier_oid", None),
            operation=operation,
        )
        
        # TEMPORARILY DISABLED: FHIR generation fails with detached entities
        # TODO: Fix FHIR generation to work with expunged entities or use different strategy
        # fhir_payload = generate_fhir(
        #     entity,
        #     entity_type,
        #     session,
        #     forced_identifier_system=getattr(endpoint, "forced_identifier_system", None),
        #     forced_identifier_oid=getattr(endpoint, "forced_identifier_oid", None),
        # )
        fhir_payload = None

        if endpoint.kind == "MLLP":
            status = "generated"
            ack_payload = ""
            try:
                if not endpoint.host or not endpoint.port:
                    raise ValueError("Endpoint MLLP host/port non configuré")
                ack_payload = await send_mllp(endpoint.host, endpoint.port, hl7_message)
                status = "sent"
            except Exception as exc:  # noqa: BLE001 - we want to log the failure
                status = "error"
                ack_payload = str(exc)
            sent_logs.append(
                MessageLog(
                    direction="out",
                    kind="MLLP",
                    endpoint_id=endpoint.id,
                    payload=hl7_message,
                    ack_payload=ack_payload or "",
                    status=status,
                )
            )
            continue

        if endpoint.kind == "FHIR":
            targets = _build_fhir_targets(endpoint)
            if not targets:
                payload_str = json.dumps(fhir_payload, default=str)
                sent_logs.append(
                    MessageLog(
                        direction="out",
                        kind="FHIR",
                        endpoint_id=endpoint.id,
                        payload=payload_str,
                        ack_payload="Endpoint FHIR non configuré",
                        status="error",
                    )
                )
                continue

            for base_url, auth_kind, auth_token in targets:
                status = "generated"
                ack_payload = ""
                payload_str = json.dumps(fhir_payload, default=str)
                try:
                    status_code, response_body = await send_fhir(
                        base_url, fhir_payload, auth_kind=auth_kind, auth_token=auth_token
                    )
                    status = "sent" if 200 <= status_code < 300 else "error"
                    ack_payload = json.dumps(response_body or {}, default=str)
                except Exception as exc:  # noqa: BLE001
                    status = "error"
                    ack_payload = str(exc)
                sent_logs.append(
                    MessageLog(
                        direction="out",
                        kind="FHIR",
                        endpoint_id=endpoint.id,
                        payload=payload_str,
                        ack_payload=ack_payload,
                        status=status,
                    )
                )
            continue

    if not endpoints:
        # No sender configured: store generated payloads for audit trail.
        hl7_message = generate_pam_hl7(entity, entity_type, session)
        fhir_payload = generate_fhir(entity, entity_type, session)
        sent_logs.append(
            MessageLog(
                direction="out",
                kind="MLLP",
                endpoint_id=None,
                payload=hl7_message,
                ack_payload="",
                status="generated",
            )
        )
        sent_logs.append(
            MessageLog(
                direction="out",
                kind="FHIR",
                endpoint_id=None,
                payload=json.dumps(fhir_payload, default=str),
                ack_payload="",
                status="generated",
            )
        )

    for log in sent_logs:
        session.add(log)

    if sent_logs:
        session.commit()


class _EmitToSendersWrapper:
    """Allow emit_to_senders to be used in sync and async contexts."""

    def __init__(self, async_callable):
        self._async = async_callable

    def __call__(self, entity, entity_type, session: Session):
        coro = self._async(entity, entity_type, session)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        else:
            return coro


emit_to_senders = _EmitToSendersWrapper(emit_to_senders_async)

__all__ = ["emit_to_senders", "emit_to_senders_async"]
