from enum import Enum
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

# Énumérations pour les types de listes prédéfinies
class VocabularySystemType(str, Enum):
    FHIR = "FHIR"
    HL7V2 = "HL7V2"
    LOCAL = "LOCAL"

class VocabularySystem(SQLModel, table=True):
    """Système de vocabulaire (ex: FHIR AdministrativeGender, HL7 Table 0001, etc)"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # Nom technique (ex: "administrative-gender")
    label: str  # Libellé utilisateur (ex: "Genre administratif")
    uri: Optional[str] = None  # URI du système (ex: "http://hl7.org/fhir/administrative-gender")
    oid: Optional[str] = None  # OID HL7v2 si applicable
    description: Optional[str] = None
    system_type: VocabularySystemType
    is_user_defined: bool = False  # Si True, les valeurs peuvent être modifiées par l'utilisateur
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    # Relations
    values: List["VocabularyValue"] = Relationship(back_populates="system")

class VocabularyValue(SQLModel, table=True):
    """Valeur d'un système de vocabulaire"""
    id: Optional[int] = Field(default=None, primary_key=True)
    system_id: int = Field(foreign_key="vocabularysystem.id")
    code: str  # Code technique (ex: "M", "F")
    display: str  # Libellé d'affichage (ex: "Masculin", "Féminin")
    definition: Optional[str] = None
    is_active: bool = True
    order: int = 0  # Pour trier les valeurs
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    # Relations
    system: VocabularySystem = Relationship(back_populates="values")
    mappings: List["VocabularyMapping"] = Relationship(back_populates="source_value")

class VocabularyMapping(SQLModel, table=True):
    """Correspondance entre valeurs de différents systèmes"""
    id: Optional[int] = Field(default=None, primary_key=True)
    source_value_id: int = Field(foreign_key="vocabularyvalue.id")
    target_system_id: int = Field(foreign_key="vocabularysystem.id")
    target_code: str
    map_type: str = "equivalent"  # equivalent, wider, narrower, inexact
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    # Relations
    source_value: VocabularyValue = Relationship(back_populates="mappings")
    target_system: VocabularySystem = Relationship()