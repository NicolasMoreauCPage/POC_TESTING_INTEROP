# app/services/mllp_manager.py
import asyncio
from typing import Dict, Tuple
from contextlib import suppress
from sqlmodel import select
from app.models_endpoints import SystemEndpoint
from app.services.mllp import start_mllp_server, stop_mllp_server

class MLLPManager:
    def __init__(self, session_factory, on_message):
        self.session_factory = session_factory
        self.on_message = on_message
        self.servers: Dict[int, asyncio.base_events.Server] = {}
        self._by_addr: Dict[Tuple[str,int], int] = {}
        self._lock = asyncio.Lock()

    def running_ids(self) -> list[int]:
        return list(self.servers.keys())

    async def start_endpoint(self, endpoint: SystemEndpoint):
        if endpoint.kind != "MLLP" or endpoint.role not in ("receiver","both"):
            return
        if not endpoint.host or not endpoint.port:
            return
        async with self._lock:
            if endpoint.id in self.servers:
                return
            key = (endpoint.host, endpoint.port)
            if key in self._by_addr:
                return
            server = await start_mllp_server(
                host=endpoint.host,
                port=endpoint.port,
                on_message=self.on_message,
                endpoint=endpoint,
                session_factory=self.session_factory,
            )
            self.servers[endpoint.id] = server
            self._by_addr[key] = endpoint.id

    async def stop_endpoint(self, endpoint_id: int):
        async with self._lock:
            server = self.servers.pop(endpoint_id, None)
            if server:
                await stop_mllp_server(server)
            with suppress(KeyError):
                for k, eid in list(self._by_addr.items()):
                    if eid == endpoint_id:
                        del self._by_addr[k]

    async def stop_all(self):
        async with self._lock:
            servers = list(self.servers.values())
            self.servers.clear()
            self._by_addr.clear()
        for s in servers:
            await stop_mllp_server(s)

    async def reload_all(self, session):
        await self.stop_all()
        eps = session.exec(
            select(SystemEndpoint).where(
                SystemEndpoint.is_enabled == True,
                SystemEndpoint.kind == "MLLP"
            )
        ).all()
        for e in eps:
            await self.start_endpoint(e)
