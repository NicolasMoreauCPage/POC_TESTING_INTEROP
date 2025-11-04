from __future__ import annotations

from datetime import datetime
from typing import Literal, TypedDict
from uuid import uuid4

from fastapi import Request


FlashLevel = Literal["info", "success", "warning", "error"]


class FlashPayload(TypedDict):
    id: str
    level: FlashLevel
    message: str
    timestamp: str


def flash(request: Request, message: str, level: FlashLevel = "info") -> None:
    """Store a one-shot notification in the client session.

    Messages are popped by the FlashMessageMiddleware and exposed on
    ``request.state.flash_messages`` for template rendering.
    """
    if not hasattr(request, "session"):
        return

    payload: FlashPayload = {
        "id": uuid4().hex,
        "level": level,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }

    messages = request.session.get("_messages")
    if not isinstance(messages, list):
        messages = []
    messages.append(payload)
    request.session["_messages"] = messages
