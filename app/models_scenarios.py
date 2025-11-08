from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy.orm import Mapped

if TYPE_CHECKING:  # pragma: no cover
    from app.models import Dossier


class InteropScenario(SQLModel, table=True):
    """Scénario d'interop (suite de messages HL7/FHIR à rejouer)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)  # identifiant stable (ex: path fichier)
    name: str
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, index=True)
    protocol: str = Field(default="HL7")  # HL7 | FHIR | MIXED
    source_path: Optional[str] = None  # emplacement d'origine (documentation/debug)
    tags: Optional[str] = None  # liste séparée par virgules
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    ght_context_id: Optional[int] = Field(default=None, foreign_key="ghtcontext.id")

    steps: Mapped[List["InteropScenarioStep"]] = Relationship(
        back_populates="scenario",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "InteropScenarioStep.order_index"},
    )
    bindings: Mapped[List["ScenarioBinding"]] = Relationship(
        back_populates="scenario",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class InteropScenarioStep(SQLModel, table=True):
    """Étape unique d'un scénario (un message à envoyer)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="interopscenario.id", index=True)
    order_index: int = Field(index=True)
    name: Optional[str] = None
    description: Optional[str] = None
    message_format: str = Field(default="hl7")  # hl7 | fhir | json | xml
    message_type: Optional[str] = None  # ex: ADT^A28, Bundle
    payload: str = Field(default="", sa_column_kwargs={"nullable": False})
    delay_seconds: Optional[int] = None  # délai suggéré avant envoi suivant
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    scenario: Mapped["InteropScenario"] = Relationship(back_populates="steps")


class ScenarioBinding(SQLModel, table=True):
    """Associe un scénario à un dossier de démonstration."""

    id: Optional[int] = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="interopscenario.id", index=True)
    dossier_id: int = Field(foreign_key="dossier.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    scenario: Mapped["InteropScenario"] = Relationship(back_populates="bindings")
