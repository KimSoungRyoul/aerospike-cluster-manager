"""Aerospike async client pool manager.

Manages one AsyncClient per connection-id, with asyncio.Lock()
for safe concurrent access in the async event loop.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import aerospike_py
from aerospike_py.exception import AerospikeError

from aerospike_cluster_manager_api import config, db
from aerospike_cluster_manager_api.utils import parse_host_port


class ClientManager:
    def __init__(self) -> None:
        self._clients: dict[str, aerospike_py.AsyncClient] = {}
        self._lock = asyncio.Lock()

    async def get_client(self, conn_id: str) -> aerospike_py.AsyncClient:
        async with self._lock:
            client = self._clients.get(conn_id)
            if client is not None and client.is_connected():
                return client

        profile = await db.get_connection(conn_id)
        if profile is None:
            raise ValueError(f"Connection profile '{conn_id}' not found")

        hosts = [parse_host_port(h, profile.port) for h in profile.hosts]
        as_config: dict[str, Any] = {"hosts": hosts, "tend_interval": config.AS_TEND_INTERVAL}
        if profile.username and profile.password:
            as_config["user"] = profile.username
            as_config["password"] = profile.password

        client = aerospike_py.AsyncClient(as_config)
        await client.connect()

        async with self._lock:
            old = self._clients.get(conn_id)
            if old is not None:
                with contextlib.suppress(AerospikeError, OSError):
                    await old.close()
            self._clients[conn_id] = client

        return client

    async def close_client(self, conn_id: str) -> None:
        async with self._lock:
            client = self._clients.pop(conn_id, None)
        if client is not None:
            with contextlib.suppress(AerospikeError, OSError):
                await client.close()

    async def close_all(self) -> None:
        async with self._lock:
            clients = list(self._clients.values())
            self._clients.clear()
        for client in clients:
            with contextlib.suppress(AerospikeError, OSError):
                await client.close()


client_manager = ClientManager()
