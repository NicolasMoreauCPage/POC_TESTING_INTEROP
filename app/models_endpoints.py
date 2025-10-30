from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class SystemEndpoint(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str                                  # "HIS X", "Broker Y", "LIS Z"
    # "MLLP" ou "FHIR"
    kind: str
    # "sender", "receiver", "both"
    role: str = "both"

    # --- MLLP ---
    host: Optional[str] = None                 # ex. 0.0.0.0 (receiver) / serveur distant (sender)
    port: Optional[int] = None                 # port TCP MLLP
    sending_app: Optional[str] = None          # MSH-3
    sending_facility: Optional[str] = None     # MSH-4
    receiving_app: Optional[str] = None        # MSH-5
    receiving_facility: Optional[str] = None   # MSH-6

    # --- FHIR ---
    base_url: Optional[str] = None             # ex. https://fhir.example.com/fhir
    auth_kind: Optional[str] = None            # "none", "bearer"
    auth_token: Optional[str] = None           # si bearer: stocké en clair pour le POC

    is_enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class MessageLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    direction: str                              # "in" / "out"
    kind: str                                   # "MLLP" / "FHIR"
    endpoint_id: Optional[int] = Field(default=None, foreign_key="systemendpoint.id")
    correlation_id: Optional[str] = None        # MSH-10 (HL7) / id FHIR / autre
    status: str = "received"                    # received/sent/ack_ok/ack_error/error
    payload: str                                # message brut
    ack_payload: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
