from sqlmodel import SQLModel, create_engine, Session, select
from typing import Optional
from app.models import Sequence
from app.models_endpoints import SystemEndpoint, MessageLog

engine = create_engine("sqlite:///./poc.db", echo=False)

def init_db() -> None:
    SQLModel.metadata.create_all(engine)

def get_session():
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
    """Incrémente et retourne la nouvelle valeur."""
    seq = _get_seq(session, name)
    seq.value += 1
    session.add(seq)
    if session.in_transaction():
        session.flush()
    else:
        session.commit()
    return seq.value
