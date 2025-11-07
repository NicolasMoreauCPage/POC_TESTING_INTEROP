"""
Compatibility shim: state transitions moved to app.workflows.state_transitions.
Re-export to preserve existing imports from app.state_transitions.
"""

from app.workflows.state_transitions import *  # noqa: F401,F403
