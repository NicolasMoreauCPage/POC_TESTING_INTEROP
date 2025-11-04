import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from sqlmodel import Session, select

from app.models_structure import (
    EntiteGeographique, Pole, Service, UniteFonctionnelle,
    UniteHebergement, Chambre, Lit, LocationPhysicalType
)

logger = logging.getLogger(__name__)

def clean_hl7_date(hl7_date: Optional[str]) -> Optional[str]:
    """Normalise une date HL7 en chaîne YYYYMMDD[HHMMSS]."""
    if not hl7_date:
        return None
    value = hl7_date.strip()
    return value or None

def format_datetime(value: Optional[str]) -> str:
    """Retourne la chaîne HL7 prête à être insérée dans un segment."""
    return value or ""

def _extract_identifier_from_loc(raw: str) -> str:
    if not raw:
        return ""
    try:
        stripped = raw.strip("^")
        # après avoir retiré les segments vides, prendre la dernière section avant les métadonnées (&…)
        parts = [p for p in stripped.split("^^^^") if p]
        candidate = parts[-1] if parts else stripped
        candidate = candidate.split("&")[0]
        return candidate
    except Exception:
        return raw


def extract_location_type(loc_segment: List[str]) -> Tuple[str, str]:
    """Extrait le type et le code de location du segment LOC"""
    # LOC|^^^^^D^^^^0192&CPAGE&700004591&FINEJ||D|Service
    raw_identifier = loc_segment[1] if len(loc_segment) > 1 else ""
    location_identifier = _extract_identifier_from_loc(raw_identifier)
    location_type = loc_segment[3] if len(loc_segment) > 3 else ""
    return location_type, location_identifier

def parse_location_characteristics(lch_segments: List[List[str]]) -> Dict[str, str]:
    """Parse les segments LCH pour extraire les caractéristiques"""
    characteristics = {}
    for segment in lch_segments:
        field_info = segment[4].split("^") if len(segment) > 4 else [""]
        field_name = field_info[0]  # ex: "ID_GLBL"
        value_field = segment[5] if len(segment) > 5 else ""
        components = value_field.split("^") if value_field else [""]
        value = components[-1] if components else ""
        characteristics[field_name] = value
    return characteristics

def process_mfn_message(message: str, session: Session) -> List[Dict[str, Any]]:
    """
    Traite un message MFN M05 et importe les locations dans la base
    """
    results = []
    logger.debug(f"Message reçu : {message}")
    # Si le message contient \\, remplacer par \
    message = message.replace("\\\\", "\\")
    segments = [seg.strip().split("|") for seg in message.split("\n") if seg.strip()]
    logger.debug(f"Segments : {segments}")
    
    if not segments:
        logger.error("Pas de segments dans le message")
        raise ValueError("Message vide")
        
    # Vérifier le type de message
    if len(segments[0]) < 9 or not segments[0][8].startswith("MFN^M05"):
        logger.error(f"Type de message invalide: {segments[0][8] if len(segments[0]) >= 9 else 'inconnu'}")
        raise ValueError(f"Type de message invalide: {segments[0][8] if len(segments[0]) >= 9 else 'inconnu'}")
    
    current_location = None
    current_chars = {}
    current_relations = []
    
    for segment in segments:
        segment_type = segment[0]
        
        if segment_type == "MFE":
            # Nouveau Master File Entry - traite l'entrée précédente si elle existe
            if current_location and current_chars:
                result = save_location(
                    current_location[0], 
                    current_location[1],
                    current_chars,
                    current_relations,
                    session
                )
                results.append(result)
                current_chars = {}
                current_relations = []
                
        elif segment_type == "LOC":
            current_location = extract_location_type(segment)
            
        elif segment_type == "LCH":
            # Ajoute la caractéristique au dictionnaire courant
            # Format attendu: LCH|<identifier>|||<field_code>^...|^<value>
            # Certains messages peuvent décaler les champs, donc on protège les indices.
            field_info = segment[4].split("^") if len(segment) > 4 else [""]
            field_name = field_info[0] if field_info else ""
            value_field = segment[5] if len(segment) > 5 else ""
            components = value_field.split("^") if value_field else [""]
            # Prend le dernier composant non vide (valeur utile après les séparateurs)
            value = next((c for c in reversed(components) if c), components[-1] if components else "")
            current_chars[field_name] = value
            
        elif segment_type == "LRL":
            # Stocke la relation pour traitement ultérieur
            current_relations.append({
                "type": segment[2].split("^")[0],
                "target": segment[4]
            })
    
    # Traite la dernière entrée si elle existe
    if current_location and current_chars:
        result = save_location(
            current_location[0],
            current_location[1],
            current_chars,
            current_relations,
            session
        )
        results.append(result)
    
    return results

def save_location(
    loc_type: str,
    identifier: str,
    characteristics: Dict[str, str],
    relations: List[Dict[str, str]],
    session: Session
) -> Dict[str, Any]:
    """
    Sauvegarde une location en base selon son type
    """
    try:
        # Propriétés communes
        base_props = {
            "identifier": characteristics.get("ID_GLBL", ""),
            "name": characteristics.get("LBL", ""),
            "short_name": characteristics.get("LBL_CRT") or None,
            "address_line1": characteristics.get("ADRS_1") or None,
            "address_line2": characteristics.get("ADRS_2") or None,
            "address_line3": characteristics.get("ADRS_3") or None,
            "address_city": characteristics.get("VL") or None,
            "address_postalcode": characteristics.get("CD_PSTL") or None,
            "opening_date": clean_hl7_date(characteristics.get("DT_OVRTR")),
            "activation_date": clean_hl7_date(characteristics.get("DT_ACTVTN")),
            "closing_date": clean_hl7_date(characteristics.get("DT_FRMTR")),
            "deactivation_date": clean_hl7_date(characteristics.get("DT_FN_ACTVTN")),
        }

        if not base_props["identifier"]:
            base_props["identifier"] = identifier
        if not base_props["identifier"]:
            base_props["identifier"] = (
                characteristics.get("ID_GLBL")
                or characteristics.get("ID")
                or characteristics.get("FNS")
                or characteristics.get("INS")
                or characteristics.get("CD")
                or ""
            )
        if not base_props["identifier"]:
            logger.error(
                "Impossible de déterminer l'identifiant",
                extra={
                    "loc_type": loc_type,
                    "characteristics": characteristics,
                    "raw_identifier": identifier,
                },
            )
            raise ValueError("Identifiant manquant pour la localisation importée")
        else:
            logger.debug(
                "Import MFN identifier resolved",
                extra={
                    "loc_type": loc_type,
                    "identifier": base_props["identifier"],
                    "raw_identifier": identifier,
                },
            )
        
        # Sélection et création selon le type
        if loc_type == "M":  # Entité juridique
            entity = EntiteGeographique(
                **base_props,
                finess=characteristics.get("FNS", ""),
                category_sae=characteristics.get("CTGR_S"),
                city_insee_code=characteristics.get("INS"),
                type=characteristics.get("TPLG"),
                responsible_id=characteristics.get("ID_GLBL_RSPNSBL"),
                responsible_name=characteristics.get("NM_USL_RSPNSBL"),
                responsible_firstname=characteristics.get("PRNM_RSPNSBL"),
                responsible_rpps=characteristics.get("RPPS_RSPNSBL"),
                responsible_adeli=characteristics.get("ADL_RSPNSBL"),
                responsible_specialty=characteristics.get("CD_SPCLT_RSPNSBL"),
            )
            
        elif loc_type == "ETBL_GRPQ":  # Établissement géographique
            entity = EntiteGeographique(
                **base_props,
                finess=characteristics.get("FNS", ""),
                category_sae=characteristics.get("CTGR_S"),
                type=characteristics.get("TPLG"),
            )
            
        elif loc_type == "P":  # Pôle
            entity = Pole(
                **base_props,
                physical_type=LocationPhysicalType.AREA,
            )
            
        elif loc_type == "D":  # Service
            entity = Service(
                **base_props,
                physical_type=LocationPhysicalType.SI,
                typology=characteristics.get("TPLG"),
                responsible_id=characteristics.get("ID_GLBL_RSPNSBL"),
                responsible_name=characteristics.get("NM_USL_RSPNSBL"),
                responsible_firstname=characteristics.get("PRNM_RSPNSBL"),
                responsible_rpps=characteristics.get("RPPS_RSPNSBL"),
                responsible_adeli=characteristics.get("ADL_RSPNSBL"),
                responsible_specialty=characteristics.get("CD_SPCLT_RSPNSBL")
            )
            
        elif loc_type == "UF":  # Unité Fonctionnelle
            entity = UniteFonctionnelle(
                **base_props,
                physical_type=LocationPhysicalType.SI,
                um_code=characteristics.get("CD_UM")
            )
            
        elif loc_type == "UH":  # Unité d'Hébergement
            entity = UniteHebergement(
                **base_props,
                physical_type=LocationPhysicalType.WI,
            )
            
        elif loc_type == "CH":  # Chambre
            entity = Chambre(
                **base_props,
                physical_type=LocationPhysicalType.RO,
            )
            
        elif loc_type == "LIT":  # Lit
            entity = Lit(
                **base_props,
                physical_type=LocationPhysicalType.BD,
                operational_status=characteristics.get("OPERATIONAL_STATUS")
            )
            
        else:
            logger.warning(f"Type de location non supporté: {loc_type}")
            return {
                "status": "error",
                "error": f"Type de location non supporté: {loc_type}"
            }
        
        # Gestion des relations
        for relation in relations:
            if relation["type"] == "ETBLSMNT":
                # Relation vers l'établissement parent
                if isinstance(entity, Pole):
                    parent = session.exec(
                        select(EntiteGeographique)
                        .where(EntiteGeographique.identifier == relation["target"])
                    ).first()
                    if parent:
                        entity.entite_geo_id = parent.id
                        
            elif relation["type"] == "LCLSTN":
                # Relation de localisation
                if isinstance(entity, Service):
                    parent = session.exec(
                        select(Pole)
                        .where(Pole.identifier == relation["target"])
                    ).first()
                    if parent:
                        entity.pole_id = parent.id
                        
                elif isinstance(entity, UniteFonctionnelle):
                    parent = session.exec(
                        select(Service)
                        .where(Service.identifier == relation["target"])
                    ).first()
                    if parent:
                        entity.service_id = parent.id
        
        # Sauvegarde
        session.add(entity)
        session.commit()
        session.refresh(entity)
        
        return {
            "status": "success",
            "type": entity.__class__.__name__,
            "id": entity.id
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de la location: {e}")
        session.rollback()
        return {
            "status": "error",
            "error": str(e)
        }

def generate_mfn_message(session: Session) -> str:
    """
    Génère un message MFN M05 à partir des locations en base
    """
    # En-tête du message
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    message = [
        f"MSH|^~\\&|STR|STR|RECEPTEUR|RECEPTEUR|{now}||MFN^M05^MFN_M05|{now}|P|2.5|||||FRA|8859/15",
        f"MFI|LOC|CPAGE_LOC_FRA|REP||{now}|AL"
    ]
    
    # Fonction helper pour générer les segments LCH
    def add_lch_segments(entity: Any, identifier: str) -> List[str]:
        segments = []
        
        # Caractéristiques communes
        segments.extend([
            f"LCH|{identifier}|||ID_GLBL^Identifiant unique global^L|^{entity.identifier}",
            f"LCH|{identifier}|||LBL^Libelle^L|^{entity.name}",
            f"LCH|{identifier}|||LBL_CRT^Libelle court^L|^{entity.short_name or ''}",
        ])
        
        # Adresse si présente
        if entity.address_line1:
            segments.append(f"LCH|{identifier}|||ADRS_1^Adresse 1^L|^{entity.address_line1}")
        if entity.address_line2:
            segments.append(f"LCH|{identifier}|||ADRS_2^Adresse 2^L|^{entity.address_line2}")
        if entity.address_line3:
            segments.append(f"LCH|{identifier}|||ADRS_3^Adresse 3^L|^{entity.address_line3}")
        if entity.address_postalcode:
            segments.append(f"LCH|{identifier}|||CD_PSTL^Code postal^L|^{entity.address_postalcode}")
        if entity.address_city:
            segments.append(f"LCH|{identifier}|||VL^Ville^L|^{entity.address_city}")
            
        # Dates
        if entity.opening_date:
            segments.append(f"LCH|{identifier}|||DT_OVRTR^Date d'ouverture^L|^{format_datetime(entity.opening_date)}")
        if entity.activation_date:
            segments.append(f"LCH|{identifier}|||DT_ACTVTN^Date d'activation^L|^{format_datetime(entity.activation_date)}")
        if entity.closing_date:
            segments.append(f"LCH|{identifier}|||DT_FRMTR^Date de fermeture^L|^{format_datetime(entity.closing_date)}")
        if entity.deactivation_date:
            segments.append(f"LCH|{identifier}|||DT_FN_ACTVTN^Date de fin d'activation^L|^{format_datetime(entity.deactivation_date)}")
            
        return segments
    
    # Entités géographiques
    for eg in session.exec(select(EntiteGeographique)).all():
        identifier = f"^^^^^M^^^^{eg.identifier}"
        message.append(f"MFE|MAD|||{identifier}|PL")
        message.append(f"LOC|{identifier}||M|Etablissement juridique")
        message.extend(add_lch_segments(eg, identifier))
        if eg.finess:
            message.append(f"LCH|{identifier}|||FNS^Code FINESS^L|^{eg.finess}")
        if eg.category_sae:
            message.append(f"LCH|{identifier}|||CTGR_S^Catégorie SAE^L|^{eg.category_sae}")
        if eg.city_insee_code:
            message.append(f"LCH|{identifier}|||INS^Code INSEE commune^L|^{eg.city_insee_code}")
        if eg.type:
            message.append(f"LCH|{identifier}|||TPLG^Typologie^L|^{eg.type}")
        if eg.responsible_id:
            message.append(f"LCH|{identifier}|||ID_GLBL_RSPNSBL^Identifiant responsable^L|^{eg.responsible_id}")
        if eg.responsible_name:
            message.append(f"LCH|{identifier}|||NM_USL_RSPNSBL^Nom responsable^L|^{eg.responsible_name}")
        if eg.responsible_firstname:
            message.append(f"LCH|{identifier}|||PRNM_RSPNSBL^Prénom responsable^L|^{eg.responsible_firstname}")
        if eg.responsible_rpps:
            message.append(f"LCH|{identifier}|||RPPS_RSPNSBL^RPPS responsable^L|^{eg.responsible_rpps}")
        if eg.responsible_adeli:
            message.append(f"LCH|{identifier}|||ADL_RSPNSBL^ADELI responsable^L|^{eg.responsible_adeli}")
        if eg.responsible_specialty:
            message.append(f"LCH|{identifier}|||CD_SPCLT_RSPNSBL^Spécialité responsable^L|^{eg.responsible_specialty}")
    
    # Services (avec leurs responsables)
    for service in session.exec(select(Service)).all():
        identifier = f"^^^^^D^^^^{service.identifier}"
        message.append(f"MFE|MAD|||{identifier}|PL")
        message.append(f"LOC|{identifier}||D|Service")
        message.extend(add_lch_segments(service, identifier))
        
        if service.typology:
            message.append(f"LCH|{identifier}|||TPLG^Typologie^L|^{service.typology}")
        if service.responsible_id:
            message.append(f"LCH|{identifier}|||ID_GLBL_RSPNSBL^Identifiant unique global du responsable^L|^{service.responsible_id}")
        if service.responsible_name:
            message.append(f"LCH|{identifier}|||NM_USL_RSPNSBL^Nom usuel du responsable^L|^{service.responsible_name}")
        if service.responsible_firstname:
            message.append(f"LCH|{identifier}|||PRNM_RSPNSBL^Prénom du responsable^L|^{service.responsible_firstname}")
        if service.responsible_rpps:
            message.append(f"LCH|{identifier}|||RPPS_RSPNSBL^Code RPPS du responsable^L|^{service.responsible_rpps}")
        if service.responsible_adeli:
            message.append(f"LCH|{identifier}|||ADL_RSPNSBL^Code ADELI du responsable^L|^{service.responsible_adeli}")
        if service.responsible_specialty:
            message.append(f"LCH|{identifier}|||CD_SPCLT_RSPNSBL^Code spécialité B2 du responsable^L|^{service.responsible_specialty}")
            
        # Relation avec le pôle
        if service.pole:
            message.append(f"LRL|{identifier}|||LCLSTN^Relation de localisation^L||^^^^^P^^^^{service.pole.identifier}")
    
    # Et ainsi de suite pour les autres types...
    
    return "\n".join(message)
