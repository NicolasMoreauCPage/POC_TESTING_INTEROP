"""Compatibility shim. Models moved to app/models/workflows.py

This wrapper keeps the old imports working.
"""

from app.models.workflows import *  # noqa: F401,F403
