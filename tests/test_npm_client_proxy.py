"""Tests for NPM API client proxy host CRUD operations."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock

import pytest
import httpx
from pydantic import ValidationError

from npm_cli.api.client import NPMClient
from npm_cli.api.models import ProxyHost, ProxyHostCreate, ProxyHostUpdate
from npm_cli.api.exceptions import NPMAPIError, NPMConnectionError, NPMValidationError


class TestNPMClientListProxyHosts:
    """Tests for list_proxy_hosts method."""

    def test_list_proxy_hosts_success(self, mocker, tmp_path):
        """Should list all proxy hosts and return list of ProxyHost objects."""
        # Create valid token file
        token_dir = tmp_path / ".npm-cli"
        token_dir.mkdir()
        token_path = token_dir / "token.json"
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        token_data = {
            "token": "test-token",
            "expires": expires.isoformat().replace("+00:00", "Z")
        }
        token_path.write_text(json.dumps(token_data))
        mocker.patch("npm_cli.api.client.Path.home", return_value=tmp_path)

        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": 1,
                "domain_names": ["example.com"],
                "forward_scheme": "http",
                "forward_host": "192.168.1.100",
                "forward_port": 8080,
                "certificate_id": 0,
                "ssl_forced": False,
                "hsts_enabled": False,
                "hsts_subdomains": False,
                "http2_support": True,
                "block_exploits": True,
                "caching_enabled": False,
                "allow_websocket_upgrade": False,
                "access_list_id": 0,
                "advanced_config": "",
                "enabled": True,
                "meta": {},
                "locations": [],
                "created_on": "2026-01-04T10:00:00.000Z",
                "modified_on": "2026-01-04T10:00:00.000Z",
                "owner_user_id": 1
            }
        ]
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        client = NPMClient(base_url="http://localhost:81")
        result = client.list_proxy_hosts()

        # Verify request was made correctly
        mock_http_client.request.assert_called_once()
        call_args = mock_http_client.request.call_args
        assert call_args[0] == ("GET", "/api/nginx/proxy-hosts")
        assert "Authorization" in call_args[1]["headers"]

        # Verify result is list of ProxyHost objects
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], ProxyHost)
        assert result[0].id == 1
        assert result[0].domain_names == ["example.com"]

    def test_list_proxy_hosts_empty_list(self, mocker, tmp_path):
        """Should return empty list when no proxy hosts exist."""
        # Create valid token file
        token_dir = tmp_path / ".npm-cli"
        token_dir.mkdir()
        token_path = token_dir / "token.json"
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        token_data = {
            "token": "test-token",
            "expires": expires.isoformat().replace("+00:00", "Z")
        }
        token_path.write_text(json.dumps(token_data))
        mocker.patch("npm_cli.api.client.Path.home", return_value=tmp_path)

        # Mock empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        client = NPMClient(base_url="http://localhost:81")
        result = client.list_proxy_hosts()

        assert isinstance(result, list)
        assert len(result) == 0

    def test_list_proxy_hosts_connection_error(self, mocker, tmp_path):
        """Should raise NPMConnectionError on connection failure."""
        # Create valid token file
        token_dir = tmp_path / ".npm-cli"
        token_dir.mkdir()
        token_path = token_dir / "token.json"
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        token_data = {
            "token": "test-token",
            "expires": expires.isoformat().replace("+00:00", "Z")
        }
        token_path.write_text(json.dumps(token_data))
        mocker.patch("npm_cli.api.client.Path.home", return_value=tmp_path)

        # Mock connection error
        mock_http_client = MagicMock()
        mock_http_client.request.side_effect = httpx.ConnectError("Connection refused")
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        client = NPMClient(base_url="http://localhost:81")

        with pytest.raises(NPMConnectionError, match="Cannot connect to NPM"):
            client.list_proxy_hosts()

    def test_list_proxy_hosts_http_error(self, mocker, tmp_path):
        """Should raise NPMAPIError on HTTP errors."""
        # Create valid token file
        token_dir = tmp_path / ".npm-cli"
        token_dir.mkdir()
        token_path = token_dir / "token.json"
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        token_data = {
            "token": "test-token",
            "expires": expires.isoformat().replace("+00:00", "Z")
        }
        token_path.write_text(json.dumps(token_data))
        mocker.patch("npm_cli.api.client.Path.home", return_value=tmp_path)

        # Mock HTTP 500 error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=Mock(),
            response=mock_response
        )

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        client = NPMClient(base_url="http://localhost:81")

        with pytest.raises(NPMAPIError, match="Failed to list proxy hosts"):
            client.list_proxy_hosts()

    def test_list_proxy_hosts_validation_error(self, mocker, tmp_path):
        """Should raise NPMValidationError on schema mismatch."""
        # Create valid token file
        token_dir = tmp_path / ".npm-cli"
        token_dir.mkdir()
        token_path = token_dir / "token.json"
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        token_data = {
            "token": "test-token",
            "expires": expires.isoformat().replace("+00:00", "Z")
        }
        token_path.write_text(json.dumps(token_data))
        mocker.patch("npm_cli.api.client.Path.home", return_value=tmp_path)

        # Mock response with invalid schema (missing required fields)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": 1,
                # Missing required fields like domain_names, forward_scheme, etc.
            }
        ]
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        client = NPMClient(base_url="http://localhost:81")

        with pytest.raises(NPMValidationError, match="NPM API response schema changed"):
            client.list_proxy_hosts()


class TestNPMClientGetProxyHost:
    """Tests for get_proxy_host method."""

    def test_get_proxy_host_success(self, mocker, tmp_path):
        """Should get single proxy host by ID and return ProxyHost object."""
        # Create valid token file
        token_dir = tmp_path / ".npm-cli"
        token_dir.mkdir()
        token_path = token_dir / "token.json"
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        token_data = {
            "token": "test-token",
            "expires": expires.isoformat().replace("+00:00", "Z")
        }
        token_path.write_text(json.dumps(token_data))
        mocker.patch("npm_cli.api.client.Path.home", return_value=tmp_path)

        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 42,
            "domain_names": ["test.example.com"],
            "forward_scheme": "https",
            "forward_host": "backend.local",
            "forward_port": 3000,
            "certificate_id": 1,
            "ssl_forced": True,
            "hsts_enabled": True,
            "hsts_subdomains": False,
            "http2_support": True,
            "block_exploits": True,
            "caching_enabled": False,
            "allow_websocket_upgrade": True,
            "access_list_id": 0,
            "advanced_config": "",
            "enabled": True,
            "meta": {},
            "locations": [],
            "created_on": "2026-01-04T10:00:00.000Z",
            "modified_on": "2026-01-04T11:00:00.000Z",
            "owner_user_id": 1
        }
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        client = NPMClient(base_url="http://localhost:81")
        result = client.get_proxy_host(42)

        # Verify request was made correctly
        mock_http_client.request.assert_called_once()
        call_args = mock_http_client.request.call_args
        assert call_args[0] == ("GET", "/api/nginx/proxy-hosts/42")
        assert "Authorization" in call_args[1]["headers"]

        # Verify result is ProxyHost object
        assert isinstance(result, ProxyHost)
        assert result.id == 42
        assert result.domain_names == ["test.example.com"]
        assert result.forward_scheme == "https"
        assert result.allow_websocket_upgrade is True

    def test_get_proxy_host_not_found(self, mocker, tmp_path):
        """Should raise NPMAPIError with specific message for 404."""
        # Create valid token file
        token_dir = tmp_path / ".npm-cli"
        token_dir.mkdir()
        token_path = token_dir / "token.json"
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        token_data = {
            "token": "test-token",
            "expires": expires.isoformat().replace("+00:00", "Z")
        }
        token_path.write_text(json.dumps(token_data))
        mocker.patch("npm_cli.api.client.Path.home", return_value=tmp_path)

        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=Mock(),
            response=mock_response
        )

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        client = NPMClient(base_url="http://localhost:81")

        with pytest.raises(NPMAPIError, match="Proxy host 999 not found"):
            client.get_proxy_host(999)

    def test_get_proxy_host_connection_error(self, mocker, tmp_path):
        """Should raise NPMConnectionError on connection failure."""
        # Create valid token file
        token_dir = tmp_path / ".npm-cli"
        token_dir.mkdir()
        token_path = token_dir / "token.json"
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        token_data = {
            "token": "test-token",
            "expires": expires.isoformat().replace("+00:00", "Z")
        }
        token_path.write_text(json.dumps(token_data))
        mocker.patch("npm_cli.api.client.Path.home", return_value=tmp_path)

        # Mock connection error
        mock_http_client = MagicMock()
        mock_http_client.request.side_effect = httpx.ConnectError("Connection refused")
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        client = NPMClient(base_url="http://localhost:81")

        with pytest.raises(NPMConnectionError, match="Cannot connect to NPM"):
            client.get_proxy_host(1)

    def test_get_proxy_host_validation_error(self, mocker, tmp_path):
        """Should raise NPMValidationError on schema mismatch."""
        # Create valid token file
        token_dir = tmp_path / ".npm-cli"
        token_dir.mkdir()
        token_path = token_dir / "token.json"
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        token_data = {
            "token": "test-token",
            "expires": expires.isoformat().replace("+00:00", "Z")
        }
        token_path.write_text(json.dumps(token_data))
        mocker.patch("npm_cli.api.client.Path.home", return_value=tmp_path)

        # Mock response with invalid schema
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 1,
            # Missing required fields
        }
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        client = NPMClient(base_url="http://localhost:81")

        with pytest.raises(NPMValidationError, match="NPM API response schema changed"):
            client.get_proxy_host(1)

    def test_get_proxy_host_http_error(self, mocker, tmp_path):
        """Should raise NPMAPIError on other HTTP errors."""
        # Create valid token file
        token_dir = tmp_path / ".npm-cli"
        token_dir.mkdir()
        token_path = token_dir / "token.json"
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        token_data = {
            "token": "test-token",
            "expires": expires.isoformat().replace("+00:00", "Z")
        }
        token_path.write_text(json.dumps(token_data))
        mocker.patch("npm_cli.api.client.Path.home", return_value=tmp_path)

        # Mock 500 error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=Mock(),
            response=mock_response
        )

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        client = NPMClient(base_url="http://localhost:81")

        with pytest.raises(NPMAPIError, match="Failed to get proxy host"):
            client.get_proxy_host(1)
