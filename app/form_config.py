"""
Compatibility shim: the form configuration has moved to app.forms.config.
Keep importing from app.form_config working by re-exporting all symbols.
"""

from app.forms.config import *  # noqa: F401,F403