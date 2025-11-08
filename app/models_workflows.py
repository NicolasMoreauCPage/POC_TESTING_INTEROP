"""
Modèles pour les workflows de scénarios cliniques.

Ces modèles permettent de définir des scénarios métier (admission, transfert, sortie)
et de les exécuter en générant dynamiquement les messages HL7 PAM et les ressources FHIR
à partir des entités réelles (Patient, Dossier, Venue, Mouvement).
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, TYPE_CHECKING

from sqlmodel import Field, SQLModel, Relationship, JSON, Column
from sqlalchemy import Text

# Import only for type checking to avoid circular imports
if TYPE_CHECKING:
    from app.models import Patient, Dossier
    from app.models_structure_fhir import GHTContext
    from app.models_endpoints import SystemEndpoint
    from app.models_scenarios import InteropScenario


class ScenarioType(str, Enum):
    """Types de scénarios cliniques."""
    ADMISSION = "ADMISSION"
    TRANSFER = "TRANSFER"
    DISCHARGE = "DISCHARGE"
    UPDATE = "UPDATE"
    ADMISSION_WITH_TRANSFER = "ADMISSION_WITH_TRANSFER"
    ADMISSION_WITH_DISCHARGE = "ADMISSION_WITH_DISCHARGE"
    MERGE_PATIENTS = "MERGE_PATIENTS"
    CANCEL_ADMISSION = "CANCEL_ADMISSION"
    OTHER = "OTHER"


class ActionType(str, Enum):
    """Types d'actions dans un workflow."""
    CREATE_PATIENT = "CREATE_PATIENT"
    UPDATE_PATIENT = "UPDATE_PATIENT"
    MERGE_PATIENTS = "MERGE_PATIENTS"
    CREATE_DOSSIER = "CREATE_DOSSIER"
    UPDATE_DOSSIER = "UPDATE_DOSSIER"
    CLOSE_DOSSIER = "CLOSE_DOSSIER"
    CANCEL_DOSSIER = "CANCEL_DOSSIER"
    CREATE_VENUE = "CREATE_VENUE"
    UPDATE_VENUE = "UPDATE_VENUE"
    END_VENUE = "END_VENUE"
    CREATE_MOVEMENT = "CREATE_MOVEMENT"
    CANCEL_MOVEMENT = "CANCEL_MOVEMENT"
    EMIT_HL7 = "EMIT_HL7"
    EMIT_FHIR = "EMIT_FHIR"


class ExecutionStatus(str, Enum):
    """Statut d'exécution d'un scénario ou d'une étape."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class EntityType(str, Enum):
    """Types d'entités créées/modifiées."""
    PATIENT = "PATIENT"
    DOSSIER = "DOSSIER"
    VENUE = "VENUE"
    MOUVEMENT = "MOUVEMENT"
    HL7_MESSAGE = "HL7_MESSAGE"
    FHIR_RESOURCE = "FHIR_RESOURCE"


class WorkflowScenario(SQLModel, table=True):
    """
    Définition d'un scénario workflow.
    
    Un scénario décrit une séquence d'actions métier (créer patient, admission, transfert)
    qui peut être exécutée pour générer dynamiquement des messages HL7 et FHIR.
    """
    __tablename__ = "workflow_scenarios"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=200, index=True)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    scenario_type: ScenarioType = Field(index=True)
    
    # Contexte GHT
    ght_context_id: Optional[int] = Field(default=None, foreign_key="ghtcontext.id")
    
    # Métadonnées
    is_active: bool = Field(default=True, index=True)
    category: Optional[str] = Field(default=None, max_length=100, index=True)
    tags: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    
    # Traçabilité migration (FK ajoutée après création de la table pour éviter dépendance circulaire)
    source_scenario_id: Optional[int] = Field(
        default=None,
        description="ID du scénario IHE d'origine si migré"
    )
    
    # Dates
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class WorkflowScenarioStep(SQLModel, table=True):
    """
    Étape d'un scénario workflow.
    
    Chaque étape décrit une action métier avec ses paramètres.
    """
    __tablename__ = "workflow_scenario_steps"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="workflow_scenarios.id", index=True)
    
    # Ordre d'exécution
    order_index: int = Field(ge=0)
    
    # Action
    action_type: ActionType
    name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Paramètres de l'action (JSON flexible)
    parameters: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Délai avant prochaine étape (en secondes)
    delay_seconds: int = Field(default=0, ge=0)
    
    # Configuration émission
    emit_hl7: bool = Field(default=True)
    emit_fhir: bool = Field(default=False)


class WorkflowScenarioExecution(SQLModel, table=True):
    """
    Instance d'exécution d'un scénario.
    
    Trace l'exécution complète d'un scénario avec liens vers toutes les entités créées.
    """
    __tablename__ = "workflow_scenario_executions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="workflow_scenarios.id", index=True)
    
    # Contexte d'exécution
    ght_context_id: Optional[int] = Field(default=None, foreign_key="ghtcontext.id")
    
    # Entités principales créées
    patient_id: Optional[int] = Field(default=None, foreign_key="patient.id")
    dossier_id: Optional[int] = Field(default=None, foreign_key="dossier.id")
    
    # Statut
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, index=True)
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Dates
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    
    # Configuration
    emit_hl7: bool = Field(default=True)
    emit_fhir: bool = Field(default=False)
    hl7_endpoint_id: Optional[int] = Field(default=None, foreign_key="systemendpoint.id")
    fhir_endpoint_id: Optional[int] = Field(default=None, foreign_key="systemendpoint.id")
    
    # Métadonnées
    execution_context: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))


class WorkflowExecutionStep(SQLModel, table=True):
    """
    Trace de l'exécution d'une étape de workflow.
    
    Enregistre l'entité créée/modifiée et les messages émis.
    """
    __tablename__ = "workflow_execution_steps"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    execution_id: int = Field(foreign_key="workflow_scenario_executions.id", index=True)
    step_id: int = Field(foreign_key="workflow_scenario_steps.id", index=True)
    
    # Ordre d'exécution réel
    execution_order: int = Field(ge=0)
    
    # Entité créée/modifiée
    entity_type: Optional[EntityType] = Field(default=None)
    entity_id: Optional[int] = Field(default=None)
    
    # Messages émis
    hl7_message_id: Optional[int] = Field(
        default=None,
        foreign_key="messagelog.id",
        description="Message HL7 émis pour cette étape"
    )
    fhir_message_id: Optional[int] = Field(
        default=None,
        foreign_key="messagelog.id",
        description="Ressource FHIR émise pour cette étape"
    )
    
    # Statut
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, index=True)
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Dates
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    
    # Données de l'étape
    step_data: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Données générées par l'étape (pour traçabilité)"
    )
