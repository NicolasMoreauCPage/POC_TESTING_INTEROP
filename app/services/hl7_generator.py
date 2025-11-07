"""
Générateur de messages HL7 PAM dynamiques.

Ce module génère des messages HL7 v2.5 PAM (Patient Administration Management)
à partir des entités du modèle de données (Patient, Dossier, Venue, Mouvement).

Avantages:
- Dates toujours actuelles (plus besoin de update_hl7_message_dates)
- Cohérence Patient HL7 = Patient en base
- Support complet des namespaces et identifiants
- Génération dynamique avec ZBE segments
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from app.models import Patient, Dossier, Venue, Mouvement
from app.models_identifiers import Identifier, IdentifierNamespace
from sqlmodel import Session, select


def format_datetime(dt: Optional[datetime] = None) -> str:
    """Format datetime en HL7 timestamp (YYYYMMDDHHmmss)."""
    if dt is None:
        dt = datetime.utcnow()
    return dt.strftime("%Y%m%d%H%M%S")


def format_date(dt: Optional[datetime] = None) -> str:
    """Format datetime en HL7 date (YYYYMMDD)."""
    if dt is None:
        return ""
    return dt.strftime("%Y%m%d")


def build_msh_segment(
    *,
    message_type: str,
    trigger_event: str,
    control_id: str,
    timestamp: Optional[datetime] = None,
    sending_application: str = "MedBridge",
    sending_facility: str = "POC",
    receiving_application: str = "TARGET",
    receiving_facility: str = "TARGET"
) -> str:
    """
    Construit le segment MSH (Message Header).
    
    Args:
        message_type: Type de message (ex: "ADT")
        trigger_event: Événement déclencheur (ex: "A01", "A02")
        control_id: ID de contrôle du message
        timestamp: Date/heure du message
        sending_application: Application émettrice
        sending_facility: Établissement émetteur
        receiving_application: Application réceptrice
        receiving_facility: Établissement récepteur
    
    Returns:
        Segment MSH formaté
    """
    ts = format_datetime(timestamp)
    return (
        f"MSH|^~\\&|{sending_application}|{sending_facility}|"
        f"{receiving_application}|{receiving_facility}|"
        f"{ts}||{message_type}^{trigger_event}|{control_id}|P|2.5"
    )


def build_pid_segment(
    patient: Patient,
    identifiers: Optional[List[Identifier]] = None,
    session: Optional[Session] = None
) -> str:
    """
    Construit le segment PID (Patient Identification).
    
    Args:
        patient: Patient
        identifiers: Liste des identifiants (optionnel, sinon chargés depuis DB)
        session: Session DB pour charger les identifiants si besoin
    
    Returns:
        Segment PID formaté
    """
    # Charger les identifiants si pas fournis
    if identifiers is None and session:
        identifiers = session.exec(
            select(Identifier).where(Identifier.patient_id == patient.id)
        ).all()
    
    # PID-3: Identifiants patient (format: ID^^^AUTHORITY&OID&ISO^PI)
    pid_3_parts = []
    if identifiers:
        for ident in identifiers:
            # Charger le namespace si besoin
            if session and ident.namespace_id:
                namespace = session.get(IdentifierNamespace, ident.namespace_id)
                if namespace:
                    # Format: ID^^^AUTHORITY&OID&ISO^PI
                    pid_3_parts.append(
                        f"{ident.value}^^^{namespace.name}&{namespace.oid}&ISO^PI"
                    )
    
    # Si pas d'identifiants, utiliser l'external_id si présent
    if not pid_3_parts and patient.external_id:
        pid_3_parts.append(patient.external_id)
    
    pid_3 = "~".join(pid_3_parts) if pid_3_parts else ""
    
    # PID-5: Nom du patient (Family^Given)
    pid_5 = f"{patient.family or ''}^{patient.given or ''}"
    
    # PID-7: Date de naissance
    pid_7 = format_date(patient.birth_date)
    
    # PID-8: Genre
    pid_8 = patient.gender or ""
    
    return f"PID|||{pid_3}||{pid_5}||{pid_7}|{pid_8}"


def build_pv1_segment(
    dossier: Dossier,
    venue: Optional[Venue] = None,
    identifiers: Optional[List[Identifier]] = None,
    session: Optional[Session] = None
) -> str:
    """
    Construit le segment PV1 (Patient Visit).
    
    Args:
        dossier: Dossier patient
        venue: Venue/séjour (optionnel)
        identifiers: Identifiants du dossier
        session: Session DB
    
    Returns:
        Segment PV1 formaté
    """
    # PV1-2: Type de patient (I=Inpatient, O=Outpatient, E=Emergency)
    patient_class = dossier.dossier_type or "I"
    if patient_class == "URGENCE":
        patient_class = "E"
    elif patient_class == "EXTERNE":
        patient_class = "O"
    else:
        patient_class = "I"
    
    # PV1-3: Localisation (code venue si présent)
    location = ""
    if venue:
        location = venue.code or ""
    
    # PV1-19: Numéro de visite (NDA)
    visit_number = ""
    if identifiers is None and session:
        identifiers = session.exec(
            select(Identifier).where(Identifier.dossier_id == dossier.id)
        ).all()
    
    if identifiers:
        for ident in identifiers:
            if session and ident.namespace_id:
                namespace = session.get(IdentifierNamespace, ident.namespace_id)
                if namespace and namespace.name == "NDA":
                    visit_number = f"{ident.value}^^^{namespace.name}&{namespace.oid}&ISO^VN"
                    break
    
    # PV1-10: UF responsable (format: ^^^^^UF_CODE)
    uf = dossier.uf_medicale or ""
    
    # PV1-44: Date/heure admission
    admit_time = format_datetime(dossier.admit_time)
    
    return f"PV1||{patient_class}|{location}|||||||{uf}||||||||||||{visit_number}|||||||||||||||||||||||||{admit_time}"


def build_zbe_segment(
    movement: Mouvement,
    namespace: Optional[IdentifierNamespace] = None,
    uf_responsabilite: Optional[str] = None
) -> str:
    """
    Construit le segment ZBE (mouvement patient - spécifique France).
    
    Args:
        movement: Mouvement patient
        namespace: Namespace pour l'identifiant du mouvement
        uf_responsabilite: UF responsable
    
    Returns:
        Segment ZBE formaté
    """
    # ZBE-1: Identifiant du mouvement (format: ID^AUTHORITY^OID^ISO)
    movement_id = movement.mouvement_seq or movement.id
    if namespace:
        zbe_1 = f"{movement_id}^{namespace.name}^{namespace.oid}^ISO"
    else:
        zbe_1 = str(movement_id)
    
    # ZBE-2: Date/heure du mouvement
    zbe_2 = format_datetime(movement.when)
    
    # ZBE-3: Action (vide)
    zbe_3 = ""
    
    # ZBE-4: Type d'action (INSERT, UPDATE, CANCEL)
    zbe_4 = "INSERT"
    
    # ZBE-5: Indicateur annulation (N par défaut)
    zbe_5 = "N"
    
    # ZBE-6: Événement d'origine
    zbe_6 = ""
    
    # ZBE-7: UF responsable (format: ^^^^^^UF^^^CODE_UF)
    uf = uf_responsabilite or ""
    zbe_7 = f"^^^^^^UF^^^{uf}" if uf else ""
    
    # ZBE-8: Vide
    zbe_8 = ""
    
    # ZBE-9: Mode de traitement
    zbe_9 = "HMS"
    
    return f"ZBE|{zbe_1}|{zbe_2}|{zbe_3}|{zbe_4}|{zbe_5}|{zbe_6}|{zbe_7}|{zbe_8}|{zbe_9}"


def generate_adt_message(
    *,
    patient: Patient,
    dossier: Dossier,
    venue: Optional[Venue] = None,
    movement: Optional[Mouvement] = None,
    message_type: str = "ADT",
    trigger_event: str = "A01",
    session: Optional[Session] = None,
    namespaces: Optional[Dict[str, IdentifierNamespace]] = None,
    control_id: Optional[str] = None,
    timestamp: Optional[datetime] = None
) -> str:
    """
    Génère un message ADT complet.
    
    Args:
        patient: Patient
        dossier: Dossier patient
        venue: Venue/séjour (optionnel)
        movement: Mouvement patient (optionnel, ajoute segment ZBE)
        message_type: Type de message (défaut: "ADT")
        trigger_event: Événement (A01=Admission, A02=Transfert, A03=Sortie, etc.)
        session: Session DB pour charger les identifiants
        namespaces: Dictionnaire des namespaces disponibles
        control_id: ID de contrôle (généré si absent)
        timestamp: Date/heure du message (maintenant si absent)
    
    Returns:
        Message HL7 PAM complet
        
    Raises:
        ValueError: Si les segments obligatoires selon le profil IHE PAM FR ne peuvent pas être générés
    """
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    if control_id is None:
        control_id = f"MSG{timestamp.strftime('%Y%m%d%H%M%S')}"
    
    # Validation des segments obligatoires selon le profil IHE PAM FR
    movement_triggers = {"A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", 
                        "A11", "A12", "A13", "A21", "A22", "A23", "A38", 
                        "A52", "A53", "A54", "A55"}
    
    # Les messages de mouvement requièrent le segment ZBE (sauf A28, A31, A40, A47 qui sont des messages d'identité)
    if trigger_event in movement_triggers and movement is None:
        raise ValueError(
            f"Le segment ZBE est obligatoire pour le message ADT^{trigger_event} selon le profil IHE PAM France. "
            f"Un objet Mouvement doit être fourni pour générer le segment ZBE."
        )
    
    # Messages A40 (fusion) et A47 (changement identifiant) ne sont pas encore supportés
    # car ils nécessitent le segment MRG
    if trigger_event in {"A40", "A47"}:
        raise NotImplementedError(
            f"Le message ADT^{trigger_event} n'est pas encore supporté par le générateur. "
            f"Ce type de message requiert le segment MRG (Merge Patient Information) qui n'est pas encore implémenté."
        )
    
    # Segments obligatoires
    segments = [
        build_msh_segment(
            message_type=message_type,
            trigger_event=trigger_event,
            control_id=control_id,
            timestamp=timestamp
        ),
        build_pid_segment(patient, session=session),
        build_pv1_segment(dossier, venue=venue, session=session)
    ]
    
    # Segment ZBE si mouvement présent
    if movement:
        movement_namespace = None
        if namespaces and "MOUVEMENT" in namespaces:
            movement_namespace = namespaces["MOUVEMENT"]
        
        uf = dossier.uf_medicale or (venue.uf_medicale if venue else None)
        segments.append(
            build_zbe_segment(movement, namespace=movement_namespace, uf_medicale=uf)
        )
    
    return "\r".join(segments)


def generate_admission_message(
    patient: Patient,
    dossier: Dossier,
    venue: Venue,
    session: Optional[Session] = None,
    namespaces: Optional[Dict[str, IdentifierNamespace]] = None
) -> str:
    """Génère un message ADT^A01 (Admission)."""
    return generate_adt_message(
        patient=patient,
        dossier=dossier,
        venue=venue,
        trigger_event="A01",
        session=session,
        namespaces=namespaces
    )


def generate_transfer_message(
    patient: Patient,
    dossier: Dossier,
    venue: Venue,
    movement: Mouvement,
    session: Optional[Session] = None,
    namespaces: Optional[Dict[str, IdentifierNamespace]] = None
) -> str:
    """Génère un message ADT^A02 (Transfert)."""
    return generate_adt_message(
        patient=patient,
        dossier=dossier,
        venue=venue,
        movement=movement,
        trigger_event="A02",
        session=session,
        namespaces=namespaces
    )


def generate_discharge_message(
    patient: Patient,
    dossier: Dossier,
    venue: Venue,
    session: Optional[Session] = None,
    namespaces: Optional[Dict[str, IdentifierNamespace]] = None
) -> str:
    """Génère un message ADT^A03 (Sortie)."""
    return generate_adt_message(
        patient=patient,
        dossier=dossier,
        venue=venue,
        trigger_event="A03",
        session=session,
        namespaces=namespaces
    )


def generate_update_message(
    patient: Patient,
    dossier: Dossier,
    venue: Optional[Venue] = None,
    session: Optional[Session] = None,
    namespaces: Optional[Dict[str, IdentifierNamespace]] = None
) -> str:
    """Génère un message ADT^A08 (Mise à jour)."""
    return generate_adt_message(
        patient=patient,
        dossier=dossier,
        venue=venue,
        trigger_event="A08",
        session=session,
        namespaces=namespaces
    )


def generate_cancel_admission_message(
    patient: Patient,
    dossier: Dossier,
    venue: Venue,
    session: Optional[Session] = None,
    namespaces: Optional[Dict[str, IdentifierNamespace]] = None
) -> str:
    """Génère un message ADT^A11 (Annulation admission)."""
    return generate_adt_message(
        patient=patient,
        dossier=dossier,
        venue=venue,
        trigger_event="A11",
        session=session,
        namespaces=namespaces
    )
