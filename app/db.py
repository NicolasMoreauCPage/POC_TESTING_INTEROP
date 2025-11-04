"""
Accès base de données et aides de séquence

Contenu
- Création du moteur SQLModel/SQLite (fichier local `poc.db`).
- Utilitaires de session via dépendance `get_session` (FastAPI Depends).
- Gestion de séquences applicatives simples (table `Sequence`) avec `peek_next_sequence`
    et `get_next_sequence`.
- Hook `before_flush` pour normaliser certains champs date/heure (chaînes → datetime).

Notes
- En contexte transactionnel (session.in_transaction()), on privilégie `flush()`
    pour éviter des commits imbriqués.
"""

from sqlmodel import SQLModel, create_engine, Session, select
from typing import Optional

# Import ALL models to ensure tables are registered
from app.models import Sequence, Patient, Dossier, Venue, Mouvement
from app.models_endpoints import SystemEndpoint, MessageLog
from app.models_vocabulary import VocabularySystem, VocabularyValue, VocabularyMapping
from app.models_structure_fhir import GHTContext, IdentifierNamespace
from app.models_structure import EntiteGeographique, Pole, Service, UniteFonctionnelle, UniteHebergement, Chambre, Lit
from app.models_identifiers import Identifier
from app import models_scenarios  # ensure scenario models are registered
from app import models_workflows  # ensure workflow models are registered

# Moteur SQLite local. Par défaut, fichier `poc.db` au répertoire courant.
# Pool size increased to handle concurrent emissions
engine = create_engine(
    "sqlite:///./poc.db",
    echo=False,
    pool_size=20,  # Increased from default 5
    max_overflow=30,  # Increased from default 10
    pool_timeout=60,  # Increased from default 30
    pool_pre_ping=True  # Check connections before using
)

def init_db() -> None:
    """Crée les tables si elles n'existent pas (idempotent)."""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Dépendance FastAPI: fournit une session courte (context manager)."""
    with Session(engine) as session:
        yield session

def _get_seq(session: Session, name: str) -> Sequence:
    seq: Optional[Sequence] = session.get(Sequence, name)
    if not seq:
        seq = Sequence(name=name, value=0)
        session.add(seq)
        # If we're already inside a transaction (e.g. session.begin()), don't commit here.
        # Commit only when called from outside a transactional context; otherwise flush so the object gets an identity.
        if session.in_transaction():
            session.flush()
        else:
            session.commit()
        session.refresh(seq)
    return seq

def peek_next_sequence(session: Session, name: str) -> int:
    """Regarde la prochaine valeur (sans la consommer)."""
    return _get_seq(session, name).value + 1

def get_next_sequence(session: Session, name: str) -> int:
    """Incrémente et retourne la nouvelle valeur de la séquence `name`."""
    seq = _get_seq(session, name)
    seq.value += 1
    session.add(seq)
    if session.in_transaction():
        session.flush()
    else:
        session.commit()
    return seq.value


# Convert common ISO datetime strings to datetime objects before flush
from sqlalchemy import event
from datetime import datetime

def _coerce_datetime_value(v):
    if isinstance(v, str):
        # Try ISO formats
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(v, fmt)
            except Exception:
                continue
        # fallback: try to parse first 14 digits as YYYYMMDDHHMMSS
        s = ''.join([c for c in v if c.isdigit()])
        try:
            return datetime.strptime(s[:14], "%Y%m%d%H%M%S")
        except Exception:
            return v
    return v


def _before_flush(session, flush_context, instances):
    """Normalise quelques attributs date/heure si fournis comme chaînes.

    Ceci permet d'accepter des formats ISO usuels ou des timestamps HL7-like (YYYYMMDDHHMMSS)
    sans faire échouer la persistance. Les attributs visés: admit_time, discharge_time,
    start_time, when, created_at, updated_at.
    """
    from app.models import Dossier, Venue, Mouvement

    for obj in list(session.new) + list(session.dirty):
        # handle a few common datetime-like attributes
        for attr in ("admit_time", "discharge_time", "start_time", "when", "created_at", "updated_at"):
            if hasattr(obj, attr):
                v = getattr(obj, attr)
                new_v = _coerce_datetime_value(v)
                if new_v is not None and new_v is not v:
                    setattr(obj, attr, new_v)


event.listen(Session, "before_flush", _before_flush)
