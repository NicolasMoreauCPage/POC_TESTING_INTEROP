"""
Models package - Centralise tous les modèles de données SQLModel
"""

# Base models (Patient, Dossier, Venue, Mouvement, etc.)
from app.models.base import *  # noqa: F401,F403

# Context models (GHT Context)
from app.models.context import *  # noqa: F401,F403

# Endpoint models (SystemEndpoint, EndpointConfig, etc.)
from app.models.endpoints import *  # noqa: F401,F403

# Identifier models (PatientIdentifier, etc.)
from app.models.identifiers import *  # noqa: F401,F403

# Scenario models (Scenario, ScenarioStep, etc.)
from app.models.scenarios import *  # noqa: F401,F403

# Shared models (MessageLog, etc.)
from app.models.shared import *  # noqa: F401,F403

# Structure models (Pole, Service, UniteFonctionnelle, Chambre, Lit)
from app.models.structure import *  # noqa: F401,F403

# Structure FHIR models (EntiteJuridique, EntiteGeographique, etc.)
from app.models.structure_fhir import *  # noqa: F401,F403

# Transport models (SystemEndpoint variants)
from app.models.transport import *  # noqa: F401,F403

# Vocabulary models (VocabularySystem, VocabularyValue, etc.)
from app.models.vocabulary import *  # noqa: F401,F403

# Workflow models (WorkflowState, WorkflowTransition, etc.)
from app.models.workflows import *  # noqa: F401,F403
