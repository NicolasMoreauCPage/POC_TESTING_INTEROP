from datetime import datetime
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel

from app.models_shared import SystemEndpoint

class GHTContext(SQLModel, table=True):
    """Contexte d'un Groupement Hospitalier de Territoire (GHT)"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # Nom du GHT
    code: str = Field(index=True, default="")  # Code unique du GHT
    description: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Configuration FHIR
    oid_racine: Optional[str] = None  # OID racine pour le GHT
    fhir_server_url: Optional[str] = None  # URL du serveur FHIR

    # Relations
    namespaces: List["IdentifierNamespace"] = Relationship(back_populates="ght_context")
    entites_juridiques: List["EntiteJuridique"] = Relationship(back_populates="ght_context")
    endpoints: List["SystemEndpoint"] = Relationship(back_populates="ght_context")

class IdentifierNamespace(SQLModel, table=True):
    """Espace de noms pour les identifiants au sein d'un GHT ou d'une EJ"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # Nom descriptif (ex: "IPP EJ Principal")
    system: str  # URI de l'espace de noms (ex: "urn:oid:1.2.250.1.71.1.2.2")
    oid: Optional[str] = None  # OID associé si différent de l'URI
    type: str  # Type d'identifiant (ex: "IPP", "NDA", "FINESS", etc.)
    description: Optional[str] = None
    is_active: bool = Field(default=True)

    # Relations
    ght_context_id: int = Field(foreign_key="ghtcontext.id")
    ght_context: GHTContext = Relationship(back_populates="namespaces")
    
    # Namespace peut être lié à une EJ spécifique (IPP, NDA, etc.) ou au niveau GHT (structure)
    entite_juridique_id: Optional[int] = Field(default=None, foreign_key="entitejuridique.id")
    entite_juridique: Optional["EntiteJuridique"] = Relationship(back_populates="namespaces")

class EntiteJuridique(SQLModel, table=True):
    """Structure juridique (ES_JURIDIQUE) - niveau 1"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    short_name: Optional[str] = None
    description: Optional[str] = None
    
    # Identifiants officiels
    finess_ej: str = Field(index=True)  # FINESS entité juridique
    siren: Optional[str] = None
    siret: Optional[str] = None
    
    # Adresse
    address_line: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: str = "FR"
    
    # État
    is_active: bool = Field(default=True)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relations
    ght_context_id: int = Field(foreign_key="ghtcontext.id")
    ght_context: GHTContext = Relationship(back_populates="entites_juridiques")
    entites_geographiques: List["EntiteGeographique"] = Relationship(back_populates="entite_juridique")
    endpoints: List["SystemEndpoint"] = Relationship(back_populates="entite_juridique")
    namespaces: List["IdentifierNamespace"] = Relationship(back_populates="entite_juridique")

class EntiteGeographique(SQLModel, table=True):
    """Structure géographique (ES_GEOGRAPHIQUE) - niveau 2"""
    id: Optional[int] = Field(default=None, primary_key=True)
    identifier: str = Field(index=True, unique=True)  # ID_GLBL
    name: str
    short_name: Optional[str] = None
    description: Optional[str] = None

    # Statut/location (aligné sur BaseLocation)
    status: str = Field(default="active")
    mode: str = Field(default="instance")
    physical_type: Optional[str] = Field(default="si")

    # Identifiants officiels
    finess: str = Field(index=True)  # FINESS entité géographique
    siren: Optional[str] = None
    siret: Optional[str] = None

    # Adresse
    address_text: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    address_line3: Optional[str] = None
    address_postalcode: Optional[str] = None
    address_city: Optional[str] = None
    address_country: Optional[str] = "FR"
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Catégorisation
    category_code: Optional[str] = None  # Code catégorie établissement
    category_name: Optional[str] = None
    category_sae: Optional[str] = None
    city_insee_code: Optional[str] = None
    type: Optional[str] = None  # Typologie (ex: MCO)

    # État
    is_active: bool = Field(default=True)

    # Dates (format HL7 YYYYMMDD pour compatibilité tests)
    opening_date: Optional[str] = None
    activation_date: Optional[str] = None
    closing_date: Optional[str] = None
    deactivation_date: Optional[str] = None

    # Responsable(s)
    responsible_id: Optional[str] = None
    responsible_name: Optional[str] = None
    responsible_firstname: Optional[str] = None
    responsible_rpps: Optional[str] = None
    responsible_adeli: Optional[str] = None
    responsible_specialty: Optional[str] = None

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relations
    # Make the foreign key optional for POC/tests: some imports create
    # geographical entities without a juridical entity present.
    entite_juridique_id: Optional[int] = Field(default=None, foreign_key="entitejuridique.id")
    entite_juridique: Optional[EntiteJuridique] = Relationship(back_populates="entites_geographiques")
    poles: List["Pole"] = Relationship(back_populates="entite_geo")

# Re-use canonical structural models from app.models_structure to avoid
# duplicate class definitions in multiple modules which breaks SQLAlchemy
# declarative registry. This file keeps FHIR-specific models (GHTContext,
# IdentifierNamespace, EntiteJuridique, EntiteGeographique) and imports
# structural classes from the central `models_structure` module.
from app.models_structure import Pole, Service, UniteHebergement, Chambre, Lit
