"""Compatibility shim. Models moved to app/models/shared.py

This wrapper keeps the old imports working.
"""

from app.models.shared import *  # noqa: F401,F403
