"""Tests for NPM API client with authentication."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open

import pytest
import httpx

from npm_cli.api.client import NPMClient


class TestNPMClientAuthentication:
    """Tests for NPM API client authentication."""

    def test_authenticate_success(self, mocker, tmp_path):
        """Should authenticate and cache token to file."""
        # Mock httpx client
        mock_response = Mock()
        mock_response.json.return_value = {
            "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test",
            "expires": "2026-01-05T10:32:00.000Z"
        }
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.post.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        # Mock token file path to use tmp_path
        token_path = tmp_path / ".npm-cli" / "token.json"
        mocker.patch("npm_cli.api.client.Path.home", return_value=tmp_path)

        client = NPMClient(base_url="http://localhost:81")
        client.authenticate(username="admin@example.com", password="secret")

        # Verify API call
        mock_http_client.post.assert_called_once_with(
            "/api/tokens",
            json={"identity": "admin@example.com", "secret": "secret"}
        )

        # Verify token saved to file
        assert token_path.exists()
        saved_data = json.loads(token_path.read_text())
        assert saved_data["token"] == "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test"
        assert saved_data["expires"] == "2026-01-05T10:32:00.000Z"

    def test_authenticate_creates_directory(self, mocker, tmp_path):
        """Should create .npm-cli directory if it doesn't exist."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "token": "test-token",
            "expires": "2026-01-05T10:32:00.000Z"
        }
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.post.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        # Use tmp_path but don't create .npm-cli directory
        mocker.patch("npm_cli.api.client.Path.home", return_value=tmp_path)

        client = NPMClient(base_url="http://localhost:81")
        client.authenticate(username="admin@example.com", password="secret")

        # Verify directory was created
        token_dir = tmp_path / ".npm-cli"
        assert token_dir.exists()
        assert token_dir.is_dir()

    def test_authenticate_handles_auth_failure(self, mocker):
        """Should raise error on authentication failure."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=Mock(),
            response=Mock(status_code=401)
        )

        mock_http_client = MagicMock()
        mock_http_client.post.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        client = NPMClient(base_url="http://localhost:81")

        with pytest.raises(httpx.HTTPStatusError):
            client.authenticate(username="admin@example.com", password="wrong")


class TestNPMClientTokenManagement:
    """Tests for token caching and expiry checking."""

    def test_get_token_returns_valid_token(self, mocker, tmp_path):
        """Should return cached token if still valid."""
        # Create valid token file
        token_dir = tmp_path / ".npm-cli"
        token_dir.mkdir()
        token_path = token_dir / "token.json"

        # Token expires in 1 hour
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        token_data = {
            "token": "valid-token",
            "expires": expires.isoformat().replace("+00:00", "Z")
        }
        token_path.write_text(json.dumps(token_data))

        mocker.patch("npm_cli.api.client.Path.home", return_value=tmp_path)
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=MagicMock())

        client = NPMClient(base_url="http://localhost:81")
        token = client._get_token()

        assert token == "valid-token"

    def test_get_token_returns_none_for_expired_token(self, mocker, tmp_path):
        """Should return None if cached token is expired."""
        # Create expired token file
        token_dir = tmp_path / ".npm-cli"
        token_dir.mkdir()
        token_path = token_dir / "token.json"

        # Token expired 1 hour ago
        expires = datetime.now(timezone.utc) - timedelta(hours=1)
        token_data = {
            "token": "expired-token",
            "expires": expires.isoformat().replace("+00:00", "Z")
        }
        token_path.write_text(json.dumps(token_data))

        mocker.patch("npm_cli.api.client.Path.home", return_value=tmp_path)
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=MagicMock())

        client = NPMClient(base_url="http://localhost:81")
        token = client._get_token()

        assert token is None

    def test_get_token_returns_none_if_file_missing(self, mocker, tmp_path):
        """Should return None if token file doesn't exist."""
        mocker.patch("npm_cli.api.client.Path.home", return_value=tmp_path)
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=MagicMock())

        client = NPMClient(base_url="http://localhost:81")
        token = client._get_token()

        assert token is None


class TestNPMClientRequests:
    """Tests for authenticated API requests."""

    def test_request_includes_bearer_token(self, mocker, tmp_path):
        """Should include Bearer token in Authorization header."""
        # Create valid token file
        token_dir = tmp_path / ".npm-cli"
        token_dir.mkdir()
        token_path = token_dir / "token.json"

        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        token_data = {
            "token": "test-bearer-token",
            "expires": expires.isoformat().replace("+00:00", "Z")
        }
        token_path.write_text(json.dumps(token_data))

        mocker.patch("npm_cli.api.client.Path.home", return_value=tmp_path)

        # Mock httpx client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        client = NPMClient(base_url="http://localhost:81")
        response = client.request("GET", "/api/proxy-hosts")

        # Verify Authorization header was set
        mock_http_client.request.assert_called_once()
        call_args = mock_http_client.request.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-bearer-token"

    def test_request_raises_error_if_token_missing(self, mocker, tmp_path):
        """Should raise error if token is missing or expired."""
        mocker.patch("npm_cli.api.client.Path.home", return_value=tmp_path)
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=MagicMock())

        client = NPMClient(base_url="http://localhost:81")

        with pytest.raises(RuntimeError, match="Token expired or missing"):
            client.request("GET", "/api/proxy-hosts")

    def test_request_passes_kwargs_to_httpx(self, mocker, tmp_path):
        """Should pass additional kwargs to httpx request."""
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

        # Mock httpx client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        client = NPMClient(base_url="http://localhost:81")
        client.request("POST", "/api/proxy-hosts", json={"domain": "example.com"})

        # Verify json kwarg was passed through
        call_args = mock_http_client.request.call_args
        assert call_args[1]["json"] == {"domain": "example.com"}


class TestNPMClientConfiguration:
    """Tests for NPM client configuration."""

    def test_client_initializes_with_base_url(self, mocker):
        """Should initialize httpx client with base_url and timeout."""
        mock_http_client = MagicMock()
        mock_client_class = mocker.patch("npm_cli.api.client.httpx.Client")
        mock_client_class.return_value = mock_http_client

        client = NPMClient(base_url="http://192.168.1.100:81")

        # Verify httpx.Client was created with correct params
        mock_client_class.assert_called_once_with(
            base_url="http://192.168.1.100:81",
            timeout=30.0,
            headers={"Content-Type": "application/json; charset=UTF-8"}
        )
