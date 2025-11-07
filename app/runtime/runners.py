# app/runtime/runners.py
from datetime import datetime, timezone
import asyncio
from app.services.mllp_manager import MLLPManager
from app.db_session_factory import session_factory
from app.services.transport_inbound import on_message_inbound

manager = MLLPManager(session_factory, on_message_inbound)

class RunnerRegistry:
    def __init__(self):
        self._runners: dict[int, object] = {}

    def running_ids(self) -> list[int]:
        return list(self._runners.keys())

    def is_running(self, endpoint_id: int) -> bool:
        return endpoint_id in self._runners

    def start(self, endpoint, session):
        if endpoint.kind == "MLLP" and endpoint.role in ("receiver","both"):
            asyncio.create_task(manager.start_endpoint(endpoint))
        self._runners[endpoint.id] = object()
        endpoint.updated_at = datetime.now(timezone.utc)
        session.add(endpoint)

    def stop(self, endpoint, session):
        self._runners.pop(endpoint.id, None)
        endpoint.updated_at = datetime.now(timezone.utc)
        session.add(endpoint)

registry = RunnerRegistry()
