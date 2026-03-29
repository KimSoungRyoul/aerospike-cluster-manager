"""Unit tests for ClientManager — verifies tend_interval is passed to AsyncClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from aerospike_cluster_manager_api.client_manager import ClientManager


@pytest.fixture()
def mock_db_profile(sample_connection):
    """Patch db.get_connection to return the sample profile."""
    with patch("aerospike_cluster_manager_api.client_manager.db") as mock_db:
        mock_db.get_connection = AsyncMock(return_value=sample_connection)
        yield mock_db


class TestClientManagerTendInterval:
    async def test_tend_interval_in_config(self, mock_db_profile):
        """AsyncClient should receive tend_interval from config."""
        mock_client = AsyncMock()
        mock_client.is_connected.return_value = True

        with (
            patch("aerospike_cluster_manager_api.client_manager.config.AS_TEND_INTERVAL", 2000),
            patch(
                "aerospike_cluster_manager_api.client_manager.aerospike_py.AsyncClient",
                return_value=mock_client,
            ) as mock_cls,
        ):
            mgr = ClientManager()
            await mgr.get_client("conn-test-1")

            call_args = mock_cls.call_args[0][0]
            assert call_args["tend_interval"] == 2000

    async def test_tend_interval_default(self, mock_db_profile):
        """AsyncClient should use default tend_interval of 1000."""
        mock_client = AsyncMock()
        mock_client.is_connected.return_value = True

        with patch(
            "aerospike_cluster_manager_api.client_manager.aerospike_py.AsyncClient",
            return_value=mock_client,
        ) as mock_cls:
            mgr = ClientManager()
            await mgr.get_client("conn-test-1")

            call_args = mock_cls.call_args[0][0]
            assert call_args["tend_interval"] == 1000
