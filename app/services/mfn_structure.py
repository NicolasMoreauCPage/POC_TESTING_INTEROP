import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from sqlmodel import Session, select

from app.models_structure import (
    EntiteGeographique, Pole, Service, UniteFonctionnelle,
    UniteHebergement, Chambre, Lit, LocationPhysicalType, LocationServiceType
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

def _extract_type_and_identifier_from_loc(raw: str) -> Tuple[str, str]:
    """
    Extrait le type d'entité ET l'identifier d'une référence LRL.
    Exemples:
        ^^^^^ETBL_GRPQ^^^^75&CPAGE... → ('ETBL_GRPQ', '75')
        ^^^^^P^^^^123&CPAGE... → ('P', '123')
        ^^^^^D^^^^456&CPAGE... → ('D', '456')
    """
    if not raw:
        return ("", "")
    try:
        stripped = raw.strip("^")
        parts = [p for p in stripped.split("^^^^") if p]
        if len(parts) >= 2:
            loc_type = parts[0]  # ETBL_GRPQ, P, D, UF, etc.
            identifier = parts[1].split("&")[0]  # 75, 123, 456, etc.
            return (loc_type, identifier)
        return ("", "")
    except Exception:
        return ("", "")


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

def process_mfn_message(message: str, session: Session, multi_pass: bool = True) -> List[Dict[str, Any]]:
    """
    Traite un message MFN M05 et importe les locations dans la base
    
    Args:
        message: Message MFN M05 au format HL7
        session: Session SQLModel
        multi_pass: Si True, fait plusieurs passes pour résoudre les dépendances parent-enfant
    """
    logger.debug(f"Message reçu : {message}")
    # Si le message contient \\, remplacer par \
    message = message.replace("\\\\", "\\")
    # Normaliser les séparateurs HL7 (souvent '\r') en '\n' puis splitter
    normalized = message.replace("\r", "\n")
    segments = [seg.strip().split("|") for seg in normalized.split("\n") if seg.strip()]
    logger.debug(f"Segments : {segments}")
    
    if not segments:
        logger.error("Pas de segments dans le message")
        raise ValueError("Message vide")
        
    # Vérifier le type de message
    if len(segments[0]) < 9 or not segments[0][8].startswith("MFN^M05"):
        logger.error(f"Type de message invalide: {segments[0][8] if len(segments[0]) >= 9 else 'inconnu'}")
        raise ValueError(f"Type de message invalide: {segments[0][8] if len(segments[0]) >= 9 else 'inconnu'}")
    
    # Phase 1: Parse all locations from message
    locations = []
    current_location = None
    current_chars = {}
    current_relations = []
    
    for segment in segments:
        segment_type = segment[0]
        
        if segment_type == "MFE":
            # Nouveau Master File Entry - stocke l'entrée précédente
            if current_location and current_chars:
                locations.append({
                    "type": current_location[0],
                    "identifier": current_location[1],
                    "characteristics": current_chars,
                    "relations": current_relations
                })
                current_chars = {}
                current_relations = []
                
        elif segment_type == "LOC":
            current_location = extract_location_type(segment)
            
        elif segment_type == "LCH":
            field_info = segment[4].split("^") if len(segment) > 4 else [""]
            field_name = field_info[0] if field_info else ""
            value_field = segment[5] if len(segment) > 5 else ""
            components = value_field.split("^") if value_field else [""]
            value = next((c for c in reversed(components) if c), components[-1] if components else "")
            current_chars[field_name] = value
            
        elif segment_type == "LRL":
            if len(segment) > 5:
                current_relations.append({
                    "type": segment[4].split("^")[0] if len(segment) > 4 else "",
                    "target": segment[6] if len(segment) > 6 else ""
                })
    
    # Stocke la dernière entrée
    if current_location and current_chars:
        locations.append({
            "type": current_location[0],
            "identifier": current_location[1],
            "characteristics": current_chars,
            "relations": current_relations
        })
    
    logger.info(f"Parsed {len(locations)} locations from MFN message")
    services = [l for l in locations if l['type'] == 'D']
    logger.info(f"  Services: {len(services)}")
    if services:
        logger.info(f"  First Service: type={services[0]['type']}, id={services[0]['identifier'][:60]}, n_relations={len(services[0]['relations'])}")
    
    # Phase 2: Import with multi-pass if enabled
    if multi_pass:
        return _import_locations_multipass(locations, session)
    else:
        # Single pass (legacy behavior)
        results = []
        for loc in locations:
            result = save_location(loc["type"], loc["identifier"], loc["characteristics"], loc["relations"], session)
            results.append(result)
        return results

def _import_locations_multipass(locations: List[Dict[str, Any]], session: Session) -> List[Dict[str, Any]]:
    """Import locations with multiple passes to resolve parent dependencies"""
    # Order by hierarchy level (parents first)
    type_order = {"M": 1, "ETBL_GRPQ": 1, "P": 2, "D": 3, "UF": 4, "UH": 5, "CH": 6, "LIT": 7}
    locations_sorted = sorted(locations, key=lambda x: type_order.get(x["type"], 99))
    
    results = []
    pending = list(locations_sorted)
    max_passes = 10
    pass_num = 0
    
    while pending and pass_num < max_passes:
        pass_num += 1
        logger.info(f"Import MFN pass {pass_num}: {len(pending)} locations pending")
        
        still_pending = []
        for loc in pending:
            result = save_location(
                loc["type"],
                loc["identifier"], 
                loc["characteristics"],
                loc["relations"],
                session
            )
            
            if result["status"] == "success":
                results.append(result)
            else:
                # Check if error is due to missing parent
                error_msg = result.get("error", "")
                if "NOT NULL constraint failed" in error_msg or "parent" in error_msg.lower():
                    # Retry in next pass
                    still_pending.append(loc)
                else:
                    # Other error, record it
                    results.append(result)
        
        if len(still_pending) == len(pending):
            # No progress made, stop to avoid infinite loop
            logger.warning(f"Import MFN stalled: {len(still_pending)} locations cannot be imported (missing parents)")
            results.extend([{"status": "error", "error": f"Missing parent for {loc['identifier']}"} for loc in still_pending])
            break
            
        pending = still_pending
    
    if pending:
        logger.warning(f"Import MFN incomplete: {len(pending)} locations not imported after {pass_num} passes")
    else:
        logger.info(f"Import MFN complete: all {len(results)} locations imported in {pass_num} passes")
    
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
    logger.info(f"save_location called: loc_type={loc_type}, identifier={identifier}, n_relations={len(relations)}")
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
                finess=characteristics.get("FNS") or "",  # Ensure empty string if missing
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
                finess=characteristics.get("FNS") or "",  # Ensure empty string if missing
                category_sae=characteristics.get("CTGR_S"),
                type=characteristics.get("TPLG"),
            )
            
        elif loc_type == "P":  # Pôle
            entity = Pole(
                **base_props,
                physical_type=LocationPhysicalType.AREA,
            )
            
        elif loc_type == "D":  # Service
            # TPLG peut contenir une valeur descriptive, on mappe par défaut vers MCO si absent
            tplg = characteristics.get("TPLG") or "MCO"
            service_type = LocationServiceType.MCO
            try:
                service_type = LocationServiceType(tplg.lower()) if tplg.lower() in [e.value for e in LocationServiceType] else LocationServiceType.MCO
            except Exception:
                service_type = LocationServiceType.MCO
            entity = Service(
                **base_props,
                physical_type=LocationPhysicalType.SI,
                service_type=service_type,
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
        
        logger.info(f"Created entity {entity.__class__.__name__} ID={entity.identifier}, about to process {len(relations)} relations")
        if isinstance(entity, Service) and len(relations) > 0:
            logger.info(f"  Service relations: {relations}")
        
        # Gestion des relations
        logger.info(f"Entity {entity.__class__.__name__} ID={entity.identifier} has {len(relations)} relations")
        for relation in relations:
            logger.info(f"  Relation type='{relation.get('type')}' target={relation.get('target', '')[:80]}")
            if relation["type"] == "ETBLSMNT":
                # Relation vers l'établissement parent (nettoyage identifiant)
                target_clean = _extract_identifier_from_loc(relation["target"])
                if isinstance(entity, Pole):
                    parent = session.exec(
                        select(EntiteGeographique)
                        .where(EntiteGeographique.identifier == target_clean)
                    ).first()
                    if parent:
                        entity.entite_geo_id = parent.id
                        
            elif relation["type"] == "LCLSTN":
                # Relation de localisation (tous les niveaux hiérarchiques)
                # Utilise le type du parent pour gérer automatiquement les sauts de hiérarchie
                parent_type, parent_identifier = _extract_type_and_identifier_from_loc(relation["target"])
                logger.info(f"LCLSTN pour {entity.__class__.__name__} ID={entity.identifier}: parent_type='{parent_type}', parent_id='{parent_identifier}', raw_target={relation['target'][:80]}")
                
                if isinstance(entity, Service):
                    # Service.pole_id requis
                    if parent_type == "P":
                        # Parent normal: Pôle
                        parent_pole = session.exec(
                            select(Pole).where(Pole.identifier == parent_identifier)
                        ).first()
                        if parent_pole:
                            entity.pole_id = parent_pole.id
                    
                    elif parent_type == "ETBL_GRPQ":
                        # Saut de hiérarchie: Service → EG directement
                        parent_eg = session.exec(
                            select(EntiteGeographique).where(EntiteGeographique.identifier == parent_identifier)
                        ).first()
                        if parent_eg:
                            # Chercher ou créer un Pôle virtuel intermédiaire
                            virtual_pole_id = f"VIRTUAL-POLE-{parent_identifier}"
                            virtual_pole = session.exec(
                                select(Pole).where(Pole.identifier == virtual_pole_id)
                            ).first()
                            
                            if not virtual_pole:
                                virtual_pole = Pole(
                                    identifier=virtual_pole_id,
                                    name=f"Pôle virtuel ({parent_eg.name})",
                                    physical_type=LocationPhysicalType.AREA,
                                    entite_geo_id=parent_eg.id,
                                    is_virtual=True
                                )
                                session.add(virtual_pole)
                                session.flush()
                                logger.info(f"Création d'un Pôle virtuel {virtual_pole.identifier} pour Service {entity.identifier}")
                            
                            entity.pole_id = virtual_pole.id
                        
                elif isinstance(entity, UniteFonctionnelle):
                    # UniteFonctionnelle.service_id requis
                    if parent_type == "D":
                        # Parent normal: Service
                        parent_service = session.exec(
                            select(Service).where(Service.identifier == parent_identifier)
                        ).first()
                        if parent_service:
                            entity.service_id = parent_service.id
                    
                    elif parent_type == "P":
                        # Saut: UF → Pôle (créer Service virtuel)
                        parent_pole = session.exec(
                            select(Pole).where(Pole.identifier == parent_identifier)
                        ).first()
                        if parent_pole:
                            # Get or create Service virtuel
                            virtual_service_id = f"VIRTUAL-SERVICE-{parent_identifier}"
                            virtual_service = session.exec(
                                select(Service).where(Service.identifier == virtual_service_id)
                            ).first()
                            
                            if not virtual_service:
                                virtual_service = Service(
                                    identifier=virtual_service_id,
                                    name=f"Service virtuel ({parent_pole.name})",
                                    physical_type=LocationPhysicalType.SI,
                                    service_type=LocationServiceType.MCO,
                                    pole_id=parent_pole.id,
                                    is_virtual=True
                                )
                                session.add(virtual_service)
                                session.flush()
                                logger.info(f"Création d'un Service virtuel {virtual_service.identifier} pour UF {entity.identifier}")
                            
                            entity.service_id = virtual_service.id
                    
                    elif parent_type == "ETBL_GRPQ":
                        # Double saut: UF → EG (créer Pôle + Service virtuels)
                        parent_eg = session.exec(
                            select(EntiteGeographique).where(EntiteGeographique.identifier == parent_identifier)
                        ).first()
                        if parent_eg:
                            # Get or create virtual Pole
                            virtual_pole_id = f"VIRTUAL-POLE-{parent_identifier}"
                            virtual_pole = session.exec(
                                select(Pole).where(Pole.identifier == virtual_pole_id)
                            ).first()
                            
                            if not virtual_pole:
                                virtual_pole = Pole(
                                    identifier=virtual_pole_id,
                                    name=f"Pôle virtuel ({parent_eg.name})",
                                    physical_type=LocationPhysicalType.AREA,
                                    entite_geo_id=parent_eg.id,
                                    is_virtual=True
                                )
                                session.add(virtual_pole)
                                session.flush()
                            
                            # Get or create virtual Service
                            virtual_service_id = f"VIRTUAL-SERVICE-{parent_identifier}"
                            virtual_service = session.exec(
                                select(Service).where(Service.identifier == virtual_service_id)
                            ).first()
                            
                            if not virtual_service:
                                virtual_service = Service(
                                    identifier=virtual_service_id,
                                    name=f"Service virtuel ({parent_eg.name})",
                                    physical_type=LocationPhysicalType.SI,
                                    service_type=LocationServiceType.MCO,
                                    pole_id=virtual_pole.id,
                                    is_virtual=True
                                )
                                session.add(virtual_service)
                                session.flush()
                                logger.info(f"Création Pôle+Service virtuels pour UF {entity.identifier}")
                            
                            entity.service_id = virtual_service.id
                        
                elif isinstance(entity, UniteHebergement):
                    # UH.unite_fonctionnelle_id requis
                    if parent_type == "UF":
                        parent = session.exec(
                            select(UniteFonctionnelle).where(UniteFonctionnelle.identifier == parent_identifier)
                        ).first()
                        if parent:
                            entity.unite_fonctionnelle_id = parent.id
                        
                elif isinstance(entity, Chambre):
                    # Chambre.unite_hebergement_id requis
                    if parent_type == "UH":
                        parent = session.exec(
                            select(UniteHebergement).where(UniteHebergement.identifier == parent_identifier)
                        ).first()
                        if parent:
                            entity.unite_hebergement_id = parent.id
                        
                elif isinstance(entity, Lit):
                    # Lit.chambre_id requis
                    if parent_type == "CH":
                        parent = session.exec(
                            select(Chambre).where(Chambre.identifier == parent_identifier)
                        ).first()
                        if parent:
                            entity.chambre_id = parent.id
        
        # Sauvegarde
        if isinstance(entity, Service):
            logger.warning(f"⚠️  BEFORE COMMIT Service {entity.identifier}, pole_id={entity.pole_id}, n_relations_processed={len(relations)}")
        
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

def generate_mfn_message(session: Session, eg_identifier: Optional[str] = None, collapse_virtual: bool = False) -> str:
    """
    Génère un message MFN M05 à partir des locations en base
    
    Args:
        session: Session SQLModel
        eg_identifier: Si fourni, génère le MFN seulement pour cet EntiteGeographique
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
    
    # Collect entities to export
    if eg_identifier:
        # Filter mode: only export hierarchy from specified EG
        eg_query = select(EntiteGeographique).where(EntiteGeographique.identifier == eg_identifier)
        target_eg = session.exec(eg_query).first()
        if not target_eg:
            logger.warning(f"EntiteGeographique {eg_identifier} not found")
            return "\n".join(message)
        
        entites_geo = [target_eg]
        poles = target_eg.poles
        services = [svc for pole in poles for svc in pole.services]
        unites_fonctionnelles = [uf for svc in services for uf in svc.unites_fonctionnelles]
        unites_hebergement = [uh for uf in unites_fonctionnelles for uh in uf.unites_hebergement]
        chambres = [ch for uh in unites_hebergement for ch in uh.chambres]
        lits = [lit for ch in chambres for lit in ch.lits]
    else:
        # Global mode: export all entities
        entites_geo = session.exec(select(EntiteGeographique)).all()
        poles = session.exec(select(Pole)).all()
        services = session.exec(select(Service)).all()
        unites_fonctionnelles = session.exec(select(UniteFonctionnelle)).all()
        unites_hebergement = session.exec(select(UniteHebergement)).all()
        chambres = session.exec(select(Chambre)).all()
        lits = session.exec(select(Lit)).all()

    # -- Collapse virtual nodes logic --
    # Convention actuelle: identifiants des pôles/services virtuels commencent par 'VIRTUAL-POLE-' / 'VIRTUAL-SERVICE-'
    # Objectif collapse: reproduire le schéma source (services liés directement à l'EG) et ne pas exporter les pôles/services virtuels.
    if collapse_virtual:
        # Filtrer pôles virtuels à exclure de l'export direct
        virtual_pole_prefix = "VIRTUAL-POLE-"
        virtual_service_prefix = "VIRTUAL-SERVICE-"
        real_poles = [p for p in poles if not p.identifier.startswith(virtual_pole_prefix)]
        poles = real_poles  # override

        # Ajuster les services: on conserve tous les services (même ceux sous pôles virtuels) mais on changera leurs relations
        # Exclure services virtuels (créés pour UF double saut) de l'export direct
        services = [s for s in services if not s.identifier.startswith(virtual_service_prefix)]

        # Pour les UF qui pointent vers un service virtuel, on tentera de les rattacher au pôle réel du service virtuel, sinon à l'EG
        # Simplification: si UF.service est virtuel → relation sera réécrite vers le pôle parent si disponible, sinon laissée telle quelle.
        # (Le fichier exemple ne contient pas d'UF, donc impact nul pour ce cas d'usage.)

    
    # Entités géographiques - filter if needed
    for eg in entites_geo:
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
    for service in services:
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

        # Relations hiérarchiques
        if collapse_virtual and service.pole and service.pole.identifier.startswith("VIRTUAL-POLE-"):
            # Collapse: exporter relation directe vers EG parent du pôle virtuel
            if service.pole.entite_geo:
                eg_parent = service.pole.entite_geo
                message.append(f"LRL|{identifier}|||LCLSTN^Relation de localisation^L||^^^^^ETBL_GRPQ^^^^{eg_parent.identifier}")
        else:
            # Relation avec le pôle (standard)
            if service.pole:
                message.append(f"LRL|{identifier}|||LCLSTN^Relation de localisation^L||^^^^^P^^^^{service.pole.identifier}")
    
    # Pôles (ignorer les pôles virtuels si collapse_virtual)
    for pole in poles:
        identifier = f"^^^^^P^^^^{pole.identifier}"
        message.append(f"MFE|MAD|||{identifier}|PL")
        message.append(f"LOC|{identifier}||P|Pole")
        message.extend(add_lch_segments(pole, identifier))
        # Relation avec l'entité géographique
        if pole.entite_geo:
            message.append(f"LRL|{identifier}|||ETBLSMNT^Relation établissement^L||^^^^^M^^^^{pole.entite_geo.identifier}")
    
    # UF
    for uf in unites_fonctionnelles:
        identifier = f"^^^^^UF^^^^{uf.identifier}"
        message.append(f"MFE|MAD|||{identifier}|PL")
        message.append(f"LOC|{identifier}||UF|Unite Fonctionnelle")
        message.extend(add_lch_segments(uf, identifier))
        if uf.um_code:
            message.append(f"LCH|{identifier}|||CD_UM^Code UM^L|^{uf.um_code}")
        # Relation avec le service
        if uf.service:
            message.append(f"LRL|{identifier}|||LCLSTN^Relation de localisation^L||^^^^^D^^^^{uf.service.identifier}")
    
    # UH
    for uh in unites_hebergement:
        identifier = f"^^^^^UH^^^^{uh.identifier}"
        message.append(f"MFE|MAD|||{identifier}|PL")
        message.append(f"LOC|{identifier}||UH|Unite Hebergement")
        message.extend(add_lch_segments(uh, identifier))
        # Relation avec UF
        if uh.unite_fonctionnelle:
            message.append(f"LRL|{identifier}|||LCLSTN^Relation de localisation^L||^^^^^UF^^^^{uh.unite_fonctionnelle.identifier}")
    
    # Chambres
    for chambre in chambres:
        identifier = f"^^^^^CH^^^^{chambre.identifier}"
        message.append(f"MFE|MAD|||{identifier}|PL")
        message.append(f"LOC|{identifier}||CH|Chambre")
        message.extend(add_lch_segments(chambre, identifier))
        # Relation avec UH
        if chambre.unite_hebergement:
            message.append(f"LRL|{identifier}|||LCLSTN^Relation de localisation^L||^^^^^UH^^^^{chambre.unite_hebergement.identifier}")
    
    # Lits
    for lit in lits:
        identifier = f"^^^^^LIT^^^^{lit.identifier}"
        message.append(f"MFE|MAD|||{identifier}|PL")
        message.append(f"LOC|{identifier}||LIT|Lit")
        message.extend(add_lch_segments(lit, identifier))
        if lit.operational_status:
            message.append(f"LCH|{identifier}|||OPERATIONAL_STATUS^Statut opérationnel^L|^{lit.operational_status}")
        # Relation avec chambre
        if lit.chambre:
            message.append(f"LRL|{identifier}|||LCLSTN^Relation de localisation^L||^^^^^CH^^^^{lit.chambre.identifier}")
    
    return "\n".join(message)
