"""Shared models module to avoid circular imports"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

# Forward-declare types for static analysis without creating import cycles
if TYPE_CHECKING:  # pragma: no cover - import only for type checkers
    from app.models_structure_fhir import GHTContext
    from app.models_endpoints import MLLPConfig, FHIRConfig

class MessageLog(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}  # Allow redefinition
    id: Optional[int] = Field(default=None, primary_key=True)
    direction: str                           # "in" / "out"
    kind: str                               # "MLLP" / "FHIR"
    message_type: Optional[str] = None       # Type de message (ex: "QBP^Q23", "ADT^A01")
    endpoint_id: Optional[int] = Field(default=None, foreign_key="systemendpoint.id")
    mllp_config_id: Optional[int] = Field(default=None, foreign_key="mllpconfig.id")
    fhir_config_id: Optional[int] = Field(default=None, foreign_key="fhirconfig.id")
    correlation_id: Optional[str] = None     # MSH-10 (HL7) / id FHIR / autre
    status: str = "received"                # received/sent/ack_ok/ack_error/error
    payload: str                            # Message brut
    ack_payload: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Enums pour modèles partagés
class EndpointRole(str):
    SENDER = "sender"
    RECEIVER = "receiver"
    BOTH = "both"

class EndpointKind(str):
    MLLP = "MLLP"
    FHIR = "FHIR"

class SystemEndpoint(SQLModel, table=True):
    """Représente un point d'intégration système (serveur FHIR, endpoint MLLP)"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    kind: str
    role: str = Field(default=EndpointRole.BOTH)
    is_enabled: bool = Field(default=True)

    # Configuration commune
    ght_context_id: Optional[int] = Field(foreign_key="ghtcontext.id", nullable=True)
    ght_context: Optional["GHTContext"] = Relationship(back_populates="endpoints")

    # Relations vers configurations
    mllp_configs: Optional[List["MLLPConfig"]] = Relationship(
        back_populates="endpoint", sa_relationship_kwargs={"lazy": "selectin"}
    )
    fhir_configs: Optional[List["FHIRConfig"]] = Relationship(
        back_populates="endpoint", sa_relationship_kwargs={"lazy": "selectin"}
    )

    # Pour MLLP
    host: Optional[str] = None  # Hostname/IP
    port: Optional[int] = None  # Port TCP
    sending_app: Optional[str] = None      # MSH-3
    sending_facility: Optional[str] = None  # MSH-4
    receiving_app: Optional[str] = None     # MSH-5
    receiving_facility: Optional[str] = None # MSH-6

    # Pour FHIR
    base_url: Optional[str] = None  # Ex: https://fhir.example.com/fhir
    auth_kind: Optional[str] = None  # none, basic, bearer
    auth_token: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Optional: force specific identifier system when emitting
    forced_identifier_system: Optional[str] = None
    forced_identifier_oid: Optional[str] = None