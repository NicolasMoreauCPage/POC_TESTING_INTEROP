from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

class EndpointContext(SQLModel, table=True):
    """
    Contexte d'un endpoint/receiver - maintient une vue isolée des données
    pour chaque système émetteur/récepteur.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    endpoint_id: int = Field(foreign_key="systemendpoint.id")
    
    # Liens vers les entités de base avec leur ID externe dans ce contexte
    patient_mappings: List["PatientContextMapping"] = Relationship(back_populates="context")
    dossier_mappings: List["DossierContextMapping"] = Relationship(back_populates="context") 
    venue_mappings: List["VenueContextMapping"] = Relationship(back_populates="context")
    mouvement_mappings: List["MouvementContextMapping"] = Relationship(back_populates="context")
    
    # État du contexte
    last_sequence_value: int = 0  # Dernière valeur de séquence utilisée
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PatientContextMapping(SQLModel, table=True):
    """Mapping des identifiants patients par contexte"""
    id: Optional[int] = Field(default=None, primary_key=True)
    context_id: int = Field(foreign_key="endpointcontext.id")
    patient_id: int = Field(foreign_key="patient.id")
    external_id: str  # ID dans le système source
    context: EndpointContext = Relationship(back_populates="patient_mappings")
    patient: "Patient" = Relationship()

class DossierContextMapping(SQLModel, table=True):
    """Mapping des dossiers par contexte"""
    id: Optional[int] = Field(default=None, primary_key=True) 
    context_id: int = Field(foreign_key="endpointcontext.id")
    dossier_id: int = Field(foreign_key="dossier.id")
    external_id: str
    context: EndpointContext = Relationship(back_populates="dossier_mappings")
    dossier: "Dossier" = Relationship()

class VenueContextMapping(SQLModel, table=True):
    """Mapping des venues par contexte"""
    id: Optional[int] = Field(default=None, primary_key=True)
    context_id: int = Field(foreign_key="endpointcontext.id")
    venue_id: int = Field(foreign_key="venue.id") 
    external_id: str
    context: EndpointContext = Relationship(back_populates="venue_mappings")
    venue: "Venue" = Relationship()

class MouvementContextMapping(SQLModel, table=True):
    """Mapping des mouvements par contexte"""
    id: Optional[int] = Field(default=None, primary_key=True)
    context_id: int = Field(foreign_key="endpointcontext.id")
    mouvement_id: int = Field(foreign_key="mouvement.id")
    external_id: str  
    context: EndpointContext = Relationship(back_populates="mouvement_mappings")
    mouvement: "Mouvement" = Relationship()