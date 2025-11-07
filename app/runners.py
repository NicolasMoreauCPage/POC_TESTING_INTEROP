"""
Compatibility shim: runners moved to app.runtime.runners.
Re-export the registry and types to keep existing imports working.
"""

from app.runtime.runners import *  # noqa: F401,F403
