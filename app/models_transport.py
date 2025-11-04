from dataclasses import dataclass
from typing import Dict, List, Literal, Optional

from sqlmodel import Field, Relationship, SQLModel

from .models_endpoints import SystemEndpoint

# Use MLLPConfig from models_endpoints to avoid duplicate class definition

# Use FHIRConfig from models_endpoints to avoid duplicate class definition