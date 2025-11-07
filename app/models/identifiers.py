"""
Modèle de gestion des identifiants
"""
from enum import Enum
from typing import Optional, TYPE_CHECKING
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models import Patient, Dossier, Venue, Mouvement


class IdentifierType(str, Enum):
    IPP = "IPP"  # Identifiant Patient Permanent
    NDA = "NDA"  # Numéro de Dossier Administratif
    AN = "AN"   # Account Number (PID-18)
    VN = "VN"   # Visit Number
    PI = "PI"   # Patient Internal
    PG = "PG"   # Patient Global
    SNS = "SNS" # Social Security
    PN = "PN"   # Person to notify / Contact
    NDP = "NDP" # Numéro dossier patient (table 203 complément FR)
    MVT = "MVT" # Identifiant de mouvement (ZBE-1)
    FINESS = "FINESS"  # Numéro FINESS établissement


class Identifier(SQLModel, table=True):
    """Modèle pour stocker les identifiants avec leur domaine"""
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # L'identifiant lui-même
    value: str = Field(..., index=True)
    
    # Type d'identifiant
    type: IdentifierType
    
    # Domaine d'identification (authority)
    system: str  # URI pour FHIR, namespace pour HL7
    oid: Optional[str] = None  # OID HL7v2 si applicable
    
    # Statut de l'identifiant
    status: str = "active"  # active, inactive, old
    
    # Dates
    assigned_date: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    # Liens vers les entités
    patient_id: Optional[int] = Field(default=None, foreign_key="patient.id")
    dossier_id: Optional[int] = Field(default=None, foreign_key="dossier.id")
    venue_id: Optional[int] = Field(default=None, foreign_key="venue.id")
    mouvement_id: Optional[int] = Field(default=None, foreign_key="mouvement.id")
    
    # Relations
    patient: Optional["Patient"] = Relationship(back_populates="identifiers")
    dossier: Optional["Dossier"] = Relationship(back_populates="identifiers")
    venue: Optional["Venue"] = Relationship(back_populates="identifiers")
    mouvement: Optional["Mouvement"] = Relationship(back_populates="identifiers")
