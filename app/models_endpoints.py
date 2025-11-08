from typing import Literal, Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

from app.models_structure_fhir import GHTContext
from app.models_shared import SystemEndpoint, MessageLog

class MLLPConfig(SQLModel, table=True):
    """Configuration MLLP spécifique à un endpoint"""
    __table_args__ = {'extend_existing': True}  # Allow redefinition

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    port: int = Field(...)
    is_enabled: bool = Field(default=True)
    
    # Connection settings
    host: str = Field(default="0.0.0.0")    # Default: listen on all interfaces
    sending_app: str                         # MSH-3
    sending_facility: str                    # MSH-4
    receiving_app: Optional[str] = None      # MSH-5
    receiving_facility: Optional[str] = None # MSH-6
    
    # Advanced settings
    buffer_size: int = Field(default=4096)  # Read buffer size
    send_ack: bool = Field(default=True)    # Whether to send ACKs
    timeout: float = Field(default=30.0)    # Socket timeout in seconds
    
    # Timing fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Owner relationship
    endpoint_id: int = Field(foreign_key="systemendpoint.id")
    endpoint: SystemEndpoint = Relationship(back_populates="mllp_configs")

class FHIRConfig(SQLModel, table=True):
    """Configuration FHIR spécifique à un endpoint"""
    __table_args__ = {'extend_existing': True}  # Allow redefinition
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)            # Name (e.g., "Patients", "Encounters")
    base_url: str = Field(...)               # Base URL for this FHIR endpoint
    path_prefix: str = ""                    # Optional path prefix (e.g., "/adt")
    version: str = "R4"                      # FHIR version

    # Auth settings
    auth_kind: str = Field(default="none")  # "none" or "bearer"
    auth_token: Optional[str] = None         # Bearer token if needed
    
    # Resource settings
    supported_resources: str = "*"           # Resource list ("*" = all)
    is_enabled: bool = Field(default=True)
    
    # Connection settings
    verify_ssl: bool = Field(default=True)   # Whether to verify SSL certs
    timeout: float = Field(default=30.0)     # Request timeout in seconds
    
    # Timing fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Owner relationship
    endpoint_id: int = Field(foreign_key="systemendpoint.id")
    endpoint: SystemEndpoint = Relationship(back_populates="fhir_configs")

# MessageLog moved to models_shared.py
