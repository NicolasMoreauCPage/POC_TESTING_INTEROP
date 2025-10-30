# app/db_session_factory.py
from contextlib import contextmanager
from app.db import get_session

@contextmanager
def session_factory():
    s = next(get_session())
    try:
        yield s
    finally:
        s.close()
