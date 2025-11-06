"""Génération de messages HL7 MFN pour Organization (EntiteJuridique).

Ce module génère des messages MFN^M02 (Master File - Staff Practitioner)
adaptés pour les Organizations / Entités Juridiques.

Note: Bien que MFN^M02 soit conçu pour les praticiens, nous l'adaptons
pour les organizations car il n'existe pas de message MFN standard pour
les organizations dans HL7 v2.5.

Alternative: Utiliser MFN^M05 avec un type différent (ORG au lieu de LOC).
"""

import logging
from datetime import datetime
from typing import Optional
from sqlmodel import Session, select

from app.models_structure_fhir import EntiteJuridique, GHTContext

logger = logging.getLogger(__name__)


def _format_hl7_datetime(dt: Optional[datetime] = None) -> str:
    """Formate une datetime en format HL7 (YYYYMMDDHHMMSS)."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y%m%d%H%M%S")


def _escape_hl7(text: Optional[str]) -> str:
    """Échappe les caractères spéciaux HL7."""
    if not text:
        return ""
    # Échapper les caractères de séparation HL7
    text = text.replace("\\", "\\E\\")
    text = text.replace("|", "\\F\\")
    text = text.replace("^", "\\S\\")
    text = text.replace("&", "\\T\\")
    text = text.replace("~", "\\R\\")
    return text


def generate_mfn_organization_message(session: Session, ej: Optional[EntiteJuridique] = None) -> str:
    """Génère un message MFN^M05 pour Organization (snapshot ou single).
    
    Format adapté pour les Entités Juridiques :
    - MSH : En-tête du message
    - MFI : Master File Identification (type=ORG)
    - Pour chaque EJ :
      - MFE : Master File Entry (action=MAD - Add/Update)
      - ORG : Organization segment (custom segment)
      - STF : Staff segment adapté pour organization
    
    Args:
        session: Session SQLModel
        ej: EntiteJuridique spécifique (si None, envoie toutes les EJ)
    
    Returns:
        Message HL7 MFN^M05 formaté
    """
    now = _format_hl7_datetime()
    
    # En-tête MSH
    segments = [
        f"MSH|^~\\&|MedBridge|MedBridge|RECEIVER|RECEIVER|{now}||MFN^M05^MFN_M05|{now}|P|2.5|||||FRA|8859/1"
    ]
    
    # MFI - Master File Identification
    # MFI-1: Master File Identifier (ORG pour Organization)
    # MFI-2: Master File Application Identifier
    # MFI-3: File-Level Event Code (REP=Replace, UPD=Update, NE=No Event)
    # MFI-4: Entered Date/Time
    # MFI-5: Effective Date/Time
    # MFI-6: Response Level Code (AL=Always)
    segments.append(f"MFI|ORG|MEDBRIDGE_ORG|REP||{now}|AL")
    
    # Récupérer les EJ à émettre
    if ej:
        ejs = [ej]
    else:
        ejs = session.exec(select(EntiteJuridique)).all()
    
    # Générer les segments pour chaque EJ
    for entity in ejs:
        # Identifiant de l'organisation (format CX)
        # Format: ID^^^Authority&OID&ISO^Type
        org_identifier = f"{entity.id}^^^MEDBRIDGE&1.2.250.1.213.1.1.1&ISO^FINEJ"
        if entity.finess_ej:
            org_identifier = f"{entity.finess_ej}^^^FINESS&1.2.250.1.71.4.2.2&ISO^FINEJ"
        
        # MFE - Master File Entry
        # MFE-1: Record-Level Event Code (MAD=Add/Update, MDL=Delete, MUP=Update)
        # MFE-2: MFN Control ID (vide)
        # MFE-3: Effective Date/Time (vide)
        # MFE-4: Primary Key Value - Organization ID
        # MFE-5: Primary Key Value Type (ORG)
        segments.append(f"MFE|MAD|||{org_identifier}|ORG")
        
        # STF - Staff Identification (adapté pour Organization)
        # STF-1: Primary Key Value (Organization ID)
        # STF-2: Staff Identifier List (FINESS)
        # STF-3: Staff Name (Organization Name) - format XPN
        name_field = f"{_escape_hl7(entity.name)}^^^^"
        if entity.short_name:
            name_field += f"^{_escape_hl7(entity.short_name)}"
        
        staff_id = org_identifier
        segments.append(f"STF|{staff_id}|{org_identifier}|{name_field}||||||||||||||")
        
        # PRA - Practitioner Detail (adapté pour Organization)
        # PRA-1: Primary Key Value (même que STF-1)
        # PRA-2: Practitioner Group (vide)
        # PRA-3: Practitioner Category (ORG=Organization)
        segments.append(f"PRA|{staff_id}||ORG")
        
        # AFF - Professional Affiliation (liens avec GHT)
        if entity.ght_context_id:
            ght = session.get(GHTContext, entity.ght_context_id)
            if ght:
                ght_name = _escape_hl7(ght.name)
                segments.append(f"AFF|1||{ght_name}||||||")
        
        # ORG - Organization segment (custom - non standard HL7)
        # Format personnalisé pour transporter les données spécifiques EJ
        org_fields = [
            "ORG",
            org_identifier,  # ORG-1: Organization ID
            _escape_hl7(entity.name),  # ORG-2: Organization Name
            _escape_hl7(entity.short_name) if entity.short_name else "",  # ORG-3: Short Name
            "EJ",  # ORG-4: Organization Type
            "A" if getattr(entity, 'is_active', True) else "I",  # ORG-5: Status (A=Active, I=Inactive)
        ]
        
        # Ajouter les champs optionnels s'ils existent
        if hasattr(entity, 'siren') and entity.siren:
            org_fields.append(entity.siren)  # ORG-6: SIREN
        else:
            org_fields.append("")
        
        if hasattr(entity, 'siret') and entity.siret:
            org_fields.append(entity.siret)  # ORG-7: SIRET
        else:
            org_fields.append("")
        
        segments.append("|".join(org_fields))
        
        # LOC - Location (pour compatibilité avec les systèmes existants)
        # Certains systèmes s'attendent à un segment LOC même pour les organizations
        loc_identifier = f"^^^^^ORG^^^^{entity.finess_ej or entity.id}"
        segments.append(f"LOC|{loc_identifier}||ORG|Entite Juridique")
        
        # LCH - Location Characteristic (détails additionnels)
        segments.append(f"LCH|{loc_identifier}|||ID_GLBL^Identifiant unique global^L|^{entity.finess_ej or entity.id}")
        segments.append(f"LCH|{loc_identifier}|||LBL^Libelle^L|^{_escape_hl7(entity.name)}")
        if entity.short_name:
            segments.append(f"LCH|{loc_identifier}|||LBL_CRT^Libelle court^L|^{_escape_hl7(entity.short_name)}")
        
        # Adresse si disponible
        if hasattr(entity, 'address_line1') and entity.address_line1:
            segments.append(f"LCH|{loc_identifier}|||ADRS_1^Adresse 1^L|^{_escape_hl7(entity.address_line1)}")
        if hasattr(entity, 'address_line2') and entity.address_line2:
            segments.append(f"LCH|{loc_identifier}|||ADRS_2^Adresse 2^L|^{_escape_hl7(entity.address_line2)}")
        if hasattr(entity, 'address_city') and entity.address_city:
            segments.append(f"LCH|{loc_identifier}|||VL^Ville^L|^{_escape_hl7(entity.address_city)}")
        if hasattr(entity, 'address_postalcode') and entity.address_postalcode:
            segments.append(f"LCH|{loc_identifier}|||CD_PSTL^Code postal^L|^{entity.address_postalcode}")
    
    # Joindre tous les segments avec \r
    return "\r".join(segments)


def generate_mfn_organization_delete(ej_id: int, finess_ej: str) -> str:
    """Génère un message MFN^M05 pour supprimer une Organization.
    
    Args:
        ej_id: ID de l'EntiteJuridique supprimée
        finess_ej: Numéro FINESS de l'EJ
    
    Returns:
        Message HL7 MFN^M05 avec action MDL (Delete)
    """
    now = _format_hl7_datetime()
    
    org_identifier = f"{finess_ej}^^^FINESS&1.2.250.1.71.4.2.2&ISO^FINEJ"
    
    segments = [
        f"MSH|^~\\&|MedBridge|MedBridge|RECEIVER|RECEIVER|{now}||MFN^M05^MFN_M05|{now}|P|2.5|||||FRA|8859/1",
        f"MFI|ORG|MEDBRIDGE_ORG|REP||{now}|AL",
        f"MFE|MDL|||{org_identifier}|ORG"
    ]
    
    return "\r".join(segments)
