# app/runners.py
from datetime import datetime, timezone

class RunnerRegistry:
    def __init__(self):
        self._runners: dict[int, object] = {}

    def running_ids(self) -> list[int]:
        return list(self._runners.keys())

    def is_running(self, endpoint_id: int) -> bool:
        return endpoint_id in self._runners

    def start(self, endpoint, session):
        # TODO: instancier ton vrai listener/sender (MLLP) ou client FHIR
        self._runners[endpoint.id] = object()
        endpoint.updated_at = datetime.now(timezone.utc)
        session.add(endpoint)

    def stop(self, endpoint, session):
        self._runners.pop(endpoint.id, None)
        endpoint.updated_at = datetime.now(timezone.utc)
        session.add(endpoint)

registry = RunnerRegistry()
