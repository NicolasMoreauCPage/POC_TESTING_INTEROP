"""Compatibility shim. Models moved to app/models/endpoints.py

This wrapper keeps the old imports working.
"""

from app.models.endpoints import *  # noqa: F401,F403
