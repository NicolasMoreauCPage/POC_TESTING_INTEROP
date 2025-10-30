from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

# --- Générateur de séquences générique ---
class Sequence(SQLModel, table=True):
    name: str = Field(primary_key=True)   # ex: "dossier", "venue", "mouvement"
    value: int = 0

# --- Patient ---
class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_seq: int = Field(index=True, unique=True)  # <-- identifiant métier séquentiel (unique)
    external_id: str                                   # si tu veux, tu peux le garder pour l'ID source
    family: str
    given: str
    middle: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    ssn: Optional[str] = None
    marital_status: Optional[str] = None
    mothers_maiden_name: Optional[str] = None
    race: Optional[str] = None
    religion: Optional[str] = None
    primary_care_provider: Optional[str] = None

    dossiers: List["Dossier"] = Relationship(back_populates="patient")


# --- Dossier ---
class Dossier(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    dossier_seq: int = Field(index=True, unique=True)       # identifiant métier unique
    patient_id: int = Field(foreign_key="patient.id")
    uf_responsabilite: str
    admit_time: datetime
    discharge_time: Optional[datetime] = None
    patient: Patient = Relationship(back_populates="dossiers")
    venues: List["Venue"] = Relationship(back_populates="dossier")

# --- Venue (appartient à un Dossier) ---
class Venue(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    venue_seq: int = Field(index=True, unique=True)         # identifiant métier unique
    dossier_id: int = Field(foreign_key="dossier.id")
    uf_responsabilite: str
    start_time: datetime
    code: Optional[str] = None
    label: Optional[str] = None
    dossier: Dossier = Relationship(back_populates="venues")
    mouvements: List["Mouvement"] = Relationship(back_populates="venue")

# --- Mouvement (appartient à une Venue) ---
class Mouvement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mouvement_seq: int = Field(index=True, unique=True)     # identifiant métier unique
    venue_id: int = Field(foreign_key="venue.id")
    type: str
    when: datetime
    location: Optional[str] = None
    venue: Venue = Relationship(back_populates="mouvements")
