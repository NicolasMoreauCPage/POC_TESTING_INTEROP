"""Conversion EntiteJuridique vers FHIR Organization.

Ce module convertit les entités juridiques en ressources FHIR Organization
conformes au profil fr-organization de l'ANS.

Références:
- http://interop-sante.fr/fhir/StructureDefinition/fr-organization
- https://www.hl7.org/fhir/organization.html
"""

from typing import Any, Dict, List, Optional
from sqlmodel import Session
from app.models_structure_fhir import EntiteJuridique


def _format_telecom(phone: Optional[str] = None, email: Optional[str] = None) -> List[Dict[str, str]]:
    """Formate les coordonnées télécom selon FHIR."""
    telecoms = []
    if phone:
        telecoms.append({
            "system": "phone",
            "value": phone,
            "use": "work"
        })
    if email:
        telecoms.append({
            "system": "email",
            "value": email,
            "use": "work"
        })
    return telecoms


def entity_to_fhir_organization(ej: EntiteJuridique, session: Session) -> Dict[str, Any]:
    """Convertit une EntiteJuridique en ressource FHIR Organization.
    
    Génère une Organization conforme au profil fr-organization avec :
    - Identifiant FINESS (obligatoire pour les établissements français)
    - Nom complet et nom court (alias)
    - Type d'organisation (établissement de santé)
    - Statut actif/inactif
    - Coordonnées (adresse, téléphone, email)
    - Référence au GHT parent (partOf)
    
    Args:
        ej: Instance d'EntiteJuridique
        session: Session SQLModel (pour charger les relations si besoin)
    
    Returns:
        Dictionnaire représentant une ressource FHIR Organization
    """
    
    # Base de la ressource Organization
    organization = {
        "resourceType": "Organization",
        "id": str(ej.id),
        "meta": {
            "profile": ["http://interop-sante.fr/fhir/StructureDefinition/fr-organization"]
        }
    }
    
    # Identifiants
    identifiers = []
    
    # FINESS EJ (obligatoire)
    if ej.finess_ej:
        identifiers.append({
            "use": "official",
            "system": "http://finess.sante.gouv.fr",
            "value": ej.finess_ej
        })
    
    # SIREN (si disponible)
    if hasattr(ej, 'siren') and ej.siren:
        identifiers.append({
            "system": "urn:oid:1.2.250.1.213.1.4.2",  # OID SIREN
            "value": ej.siren
        })
    
    # SIRET (si disponible)
    if hasattr(ej, 'siret') and ej.siret:
        identifiers.append({
            "system": "urn:oid:1.2.250.1.213.1.4.1",  # OID SIRET
            "value": ej.siret
        })
    
    if identifiers:
        organization["identifier"] = identifiers
    
    # Statut (actif par défaut)
    organization["active"] = getattr(ej, 'is_active', True)
    
    # Type d'organisation (établissement de santé)
    organization["type"] = [
        {
            "coding": [
                {
                    "system": "https://mos.esante.gouv.fr/NOS/TRE_R66-CategorieEtablissement/FHIR/TRE-R66-CategorieEtablissement",
                    "code": "EJ",
                    "display": "Entité Juridique"
                }
            ],
            "text": "Entité Juridique"
        }
    ]
    
    # Nom de l'organisation
    organization["name"] = ej.name
    
    # Alias (nom court)
    if ej.short_name:
        organization["alias"] = [ej.short_name]
    
    # Coordonnées télécom (si disponibles)
    telecoms = _format_telecom(
        phone=getattr(ej, 'phone', None),
        email=getattr(ej, 'email', None)
    )
    if telecoms:
        organization["telecom"] = telecoms
    
    # Adresse (si disponible)
    if hasattr(ej, 'address_line1') and ej.address_line1:
        address = {
            "use": "work",
            "type": "postal"
        }
        
        lines = []
        if ej.address_line1:
            lines.append(ej.address_line1)
        if hasattr(ej, 'address_line2') and ej.address_line2:
            lines.append(ej.address_line2)
        if hasattr(ej, 'address_line3') and ej.address_line3:
            lines.append(ej.address_line3)
        
        if lines:
            address["line"] = lines
        
        if hasattr(ej, 'address_city') and ej.address_city:
            address["city"] = ej.address_city
        if hasattr(ej, 'address_postalcode') and ej.address_postalcode:
            address["postalCode"] = ej.address_postalcode
        if hasattr(ej, 'address_country') and ej.address_country:
            address["country"] = ej.address_country
        else:
            address["country"] = "FR"
        
        organization["address"] = [address]
    
    # Référence au GHT parent (partOf)
    if ej.ght_context_id:
        from app.models_structure_fhir import GHTContext
        ght = session.get(GHTContext, ej.ght_context_id)
        if ght:
            organization["partOf"] = {
                "reference": f"Organization/{ght.id}",
                "display": ght.name
            }
    
    # Extensions spécifiques (dates, etc.)
    extensions = []
    
    # Date de début d'activité (si disponible)
    if ej.start_date:
        extensions.append({
            "url": "http://example.org/fhir/StructureDefinition/start-date",
            "valueDateTime": ej.start_date.isoformat()
        })
    
    # Date de fin d'activité (si disponible)
    if ej.end_date:
        extensions.append({
            "url": "http://example.org/fhir/StructureDefinition/end-date",
            "valueDateTime": ej.end_date.isoformat()
        })
    
    if extensions:
        organization["extension"] = extensions
    
    return organization


def organization_to_bundle(ej: EntiteJuridique, session: Session, method: str = "PUT") -> Dict[str, Any]:
    """Crée un Bundle FHIR transaction pour créer/modifier une Organization.
    
    Args:
        ej: EntiteJuridique à convertir
        session: Session SQLModel
        method: Méthode HTTP ("PUT" pour upsert, "DELETE" pour suppression)
    
    Returns:
        Bundle FHIR de type transaction
    """
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": []
    }
    
    if method == "DELETE":
        bundle["entry"].append({
            "request": {
                "method": "DELETE",
                "url": f"Organization/{ej.id}"
            }
        })
    else:
        resource = entity_to_fhir_organization(ej, session)
        bundle["entry"].append({
            "resource": resource,
            "request": {
                "method": method,
                "url": f"Organization/{ej.id}"
            }
        })
    
    return bundle
