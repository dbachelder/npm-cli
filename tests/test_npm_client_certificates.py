"""Tests for NPM API client certificate CRUD operations."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock

import pytest
import httpx
from pydantic import ValidationError

from npm_cli.api.client import NPMClient
from npm_cli.api.models import Certificate, CertificateCreate, ProxyHost, ProxyHostUpdate
from npm_cli.api.exceptions import NPMAPIError, NPMConnectionError, NPMValidationError


class TestNPMClientCertificateCreate:
    """Tests for certificate_create method."""

    def test_certificate_create_success(self, mocker, tmp_path):
        """Should create certificate and return Certificate object."""
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
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 5,
            "domain_names": ["example.com", "www.example.com"],
            "nice_name": "Example Certificate",
            "provider": "letsencrypt",
            "meta": {
                "letsencrypt_email": "admin@example.com"
            },
            "created_on": "2026-01-04T10:00:00.000Z",
            "modified_on": "2026-01-04T10:00:00.000Z",
            "expires_on": "2026-04-04T10:00:00.000Z",
            "owner_user_id": 1
        }
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        # Create request data
        cert_create = CertificateCreate(
            domain_names=["example.com", "www.example.com"],
            meta={"letsencrypt_email": "admin@example.com"},
            nice_name="Example Certificate"
        )

        client = NPMClient(base_url="http://localhost:81")
        result = client.certificate_create(cert_create)

        # Verify request was made correctly
        mock_http_client.request.assert_called_once()
        call_args = mock_http_client.request.call_args
        assert call_args[0] == ("POST", "/api/nginx/certificates")
        assert "Authorization" in call_args[1]["headers"]

        # Verify payload used exclude_none=True
        json_payload = call_args[1]["json"]
        assert json_payload["domain_names"] == ["example.com", "www.example.com"]
        assert json_payload["meta"] == {"letsencrypt_email": "admin@example.com"}
        assert json_payload["nice_name"] == "Example Certificate"

        # Verify result is Certificate object
        assert isinstance(result, Certificate)
        assert result.id == 5
        assert result.domain_names == ["example.com", "www.example.com"]
        assert result.nice_name == "Example Certificate"
        assert result.expires_on == "2026-04-04T10:00:00.000Z"

    def test_certificate_create_connection_error(self, mocker, tmp_path):
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

        cert_create = CertificateCreate(
            domain_names=["test.com"],
            meta={"letsencrypt_email": "admin@test.com"}
        )

        client = NPMClient(base_url="http://localhost:81")

        with pytest.raises(NPMConnectionError, match="Cannot connect to NPM"):
            client.certificate_create(cert_create)

    def test_certificate_create_api_error(self, mocker, tmp_path):
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

        # Mock 400 error (bad request)
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request",
            request=Mock(),
            response=mock_response
        )

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        cert_create = CertificateCreate(
            domain_names=["test.com"],
            meta={"letsencrypt_email": "admin@test.com"}
        )

        client = NPMClient(base_url="http://localhost:81")

        with pytest.raises(NPMAPIError, match="Failed to create certificate"):
            client.certificate_create(cert_create)

    def test_certificate_create_validation_error(self, mocker, tmp_path):
        """Should raise NPMValidationError on invalid response schema."""
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
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 1,
            # Missing required fields like domain_names, meta, etc.
        }
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        cert_create = CertificateCreate(
            domain_names=["test.com"],
            meta={"letsencrypt_email": "admin@test.com"}
        )

        client = NPMClient(base_url="http://localhost:81")

        with pytest.raises(NPMValidationError, match="NPM API response schema changed"):
            client.certificate_create(cert_create)


class TestNPMClientCertificateList:
    """Tests for certificate_list method."""

    def test_certificate_list_success(self, mocker, tmp_path):
        """Should list all certificates and return list of Certificate objects."""
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
                "nice_name": "Example Cert",
                "provider": "letsencrypt",
                "meta": {"letsencrypt_email": "admin@example.com"},
                "created_on": "2026-01-01T10:00:00.000Z",
                "modified_on": "2026-01-01T10:00:00.000Z",
                "expires_on": "2026-04-01T10:00:00.000Z",
                "owner_user_id": 1
            },
            {
                "id": 2,
                "domain_names": ["test.com", "www.test.com"],
                "nice_name": "Test Cert",
                "provider": "letsencrypt",
                "meta": {"letsencrypt_email": "admin@test.com"},
                "created_on": "2026-01-02T10:00:00.000Z",
                "modified_on": "2026-01-02T10:00:00.000Z",
                "expires_on": "2026-04-02T10:00:00.000Z",
                "owner_user_id": 1
            }
        ]
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        client = NPMClient(base_url="http://localhost:81")
        result = client.certificate_list()

        # Verify request was made correctly
        mock_http_client.request.assert_called_once()
        call_args = mock_http_client.request.call_args
        assert call_args[0] == ("GET", "/api/nginx/certificates")
        assert "Authorization" in call_args[1]["headers"]

        # Verify result is list of Certificate objects
        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], Certificate)
        assert isinstance(result[1], Certificate)
        assert result[0].id == 1
        assert result[0].domain_names == ["example.com"]
        assert result[1].id == 2
        assert result[1].domain_names == ["test.com", "www.test.com"]

    def test_certificate_list_empty(self, mocker, tmp_path):
        """Should return empty list when no certificates exist."""
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
        result = client.certificate_list()

        assert isinstance(result, list)
        assert len(result) == 0

    def test_certificate_list_connection_error(self, mocker, tmp_path):
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
            client.certificate_list()

    def test_certificate_list_api_error(self, mocker, tmp_path):
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

        with pytest.raises(NPMAPIError, match="Failed to list certificates"):
            client.certificate_list()

    def test_certificate_list_validation_error(self, mocker, tmp_path):
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
        mock_response.json.return_value = [
            {
                "id": 1,
                # Missing required fields
            }
        ]
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        client = NPMClient(base_url="http://localhost:81")

        with pytest.raises(NPMValidationError, match="NPM API response schema changed"):
            client.certificate_list()


class TestNPMClientCertificateGet:
    """Tests for certificate_get method."""

    def test_certificate_get_success(self, mocker, tmp_path):
        """Should get single certificate by ID and return Certificate object."""
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
            "id": 10,
            "domain_names": ["*.example.com", "example.com"],
            "nice_name": "Wildcard Certificate",
            "provider": "letsencrypt",
            "meta": {
                "letsencrypt_email": "admin@example.com",
                "dns_provider": "cloudflare"
            },
            "created_on": "2026-01-01T10:00:00.000Z",
            "modified_on": "2026-01-01T10:00:00.000Z",
            "expires_on": "2026-04-01T10:00:00.000Z",
            "owner_user_id": 1
        }
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        client = NPMClient(base_url="http://localhost:81")
        result = client.certificate_get(10)

        # Verify request was made correctly
        mock_http_client.request.assert_called_once()
        call_args = mock_http_client.request.call_args
        assert call_args[0] == ("GET", "/api/nginx/certificates/10")
        assert "Authorization" in call_args[1]["headers"]

        # Verify result is Certificate object
        assert isinstance(result, Certificate)
        assert result.id == 10
        assert result.domain_names == ["*.example.com", "example.com"]
        assert result.nice_name == "Wildcard Certificate"

    def test_certificate_get_not_found(self, mocker, tmp_path):
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

        with pytest.raises(NPMAPIError, match="Certificate 999 not found"):
            client.certificate_get(999)

    def test_certificate_get_connection_error(self, mocker, tmp_path):
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
            client.certificate_get(1)

    def test_certificate_get_validation_error(self, mocker, tmp_path):
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
            client.certificate_get(1)


class TestNPMClientCertificateDelete:
    """Tests for certificate_delete method."""

    def test_certificate_delete_success(self, mocker, tmp_path):
        """Should delete certificate and return None."""
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

        # Mock successful API response (DELETE returns empty body)
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        client = NPMClient(base_url="http://localhost:81")
        result = client.certificate_delete(5)

        # Verify request was made correctly
        mock_http_client.request.assert_called_once()
        call_args = mock_http_client.request.call_args
        assert call_args[0] == ("DELETE", "/api/nginx/certificates/5")
        assert "Authorization" in call_args[1]["headers"]

        # Verify result is None
        assert result is None

    def test_certificate_delete_not_found(self, mocker, tmp_path):
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

        with pytest.raises(NPMAPIError, match="Certificate 999 not found"):
            client.certificate_delete(999)

    def test_certificate_delete_connection_error(self, mocker, tmp_path):
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
            client.certificate_delete(1)

    def test_certificate_delete_http_error(self, mocker, tmp_path):
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

        with pytest.raises(NPMAPIError, match="Failed to delete certificate"):
            client.certificate_delete(1)


class TestNPMClientAttachCertificateToProxy:
    """Tests for attach_certificate_to_proxy workflow helper."""

    def test_attach_certificate_to_proxy_success(self, mocker, tmp_path):
        """Should create certificate and attach to proxy host in one operation."""
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

        # Create mock responses
        # 1. Certificate creation response
        mock_cert_response = Mock()
        mock_cert_response.status_code = 201
        mock_cert_response.json.return_value = {
            "id": 5,
            "domain_names": ["app.example.com"],
            "nice_name": "App Certificate",
            "provider": "letsencrypt",
            "meta": {"letsencrypt_email": "admin@example.com"},
            "created_on": "2026-01-04T10:00:00.000Z",
            "modified_on": "2026-01-04T10:00:00.000Z",
            "expires_on": "2026-04-04T10:00:00.000Z",
            "owner_user_id": 1
        }
        mock_cert_response.raise_for_status = Mock()

        # 2. Proxy host list response
        mock_list_response = Mock()
        mock_list_response.status_code = 200
        mock_list_response.json.return_value = [
            {
                "id": 10,
                "domain_names": ["app.example.com"],
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
                "created_on": "2026-01-03T10:00:00.000Z",
                "modified_on": "2026-01-03T10:00:00.000Z",
                "owner_user_id": 1
            }
        ]
        mock_list_response.raise_for_status = Mock()

        # 3. GET proxy host for update
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = mock_list_response.json.return_value[0]
        mock_get_response.raise_for_status = Mock()

        # 4. PUT proxy host with certificate
        mock_update_response = Mock()
        mock_update_response.status_code = 200
        mock_update_response.json.return_value = {
            **mock_list_response.json.return_value[0],
            "certificate_id": 5,
            "ssl_forced": True,
            "hsts_enabled": True,
            "http2_support": True,
            "modified_on": "2026-01-04T11:00:00.000Z"
        }
        mock_update_response.raise_for_status = Mock()

        # Mock HTTP client to return different responses based on call order
        mock_http_client = MagicMock()
        mock_http_client.request.side_effect = [
            mock_cert_response,      # POST /api/nginx/certificates
            mock_list_response,      # GET /api/nginx/proxy-hosts
            mock_get_response,       # GET /api/nginx/proxy-hosts/10
            mock_update_response     # PUT /api/nginx/proxy-hosts/10
        ]
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        # Create request data
        cert_create = CertificateCreate(
            domain_names=["app.example.com"],
            meta={"letsencrypt_email": "admin@example.com"},
            nice_name="App Certificate"
        )

        client = NPMClient(base_url="http://localhost:81")
        cert, proxy = client.attach_certificate_to_proxy(
            domain="app.example.com",
            cert=cert_create,
            ssl_forced=True,
            hsts_enabled=True
        )

        # Verify certificate created
        assert isinstance(cert, Certificate)
        assert cert.id == 5
        assert cert.domain_names == ["app.example.com"]

        # Verify proxy host updated
        assert isinstance(proxy, ProxyHost)
        assert proxy.id == 10
        assert proxy.certificate_id == 5
        assert proxy.ssl_forced is True
        assert proxy.hsts_enabled is True
        assert proxy.http2_support is True

        # Verify API calls were made in correct order
        assert mock_http_client.request.call_count == 4
        call_list = mock_http_client.request.call_args_list

        # 1. Certificate creation
        assert call_list[0][0] == ("POST", "/api/nginx/certificates")

        # 2. List proxy hosts
        assert call_list[1][0] == ("GET", "/api/nginx/proxy-hosts")

        # 3. Get specific proxy host for update
        assert call_list[2][0] == ("GET", "/api/nginx/proxy-hosts/10")

        # 4. Update proxy host with certificate
        assert call_list[3][0] == ("PUT", "/api/nginx/proxy-hosts/10")
        update_payload = call_list[3][1]["json"]
        assert update_payload["certificate_id"] == 5
        assert update_payload["ssl_forced"] is True
        assert update_payload["hsts_enabled"] is True
        assert update_payload["http2_support"] is True

    def test_attach_certificate_to_proxy_not_found(self, mocker, tmp_path):
        """Should raise ValueError if proxy host not found for domain."""
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

        # Mock certificate creation response
        mock_cert_response = Mock()
        mock_cert_response.status_code = 201
        mock_cert_response.json.return_value = {
            "id": 5,
            "domain_names": ["nonexistent.example.com"],
            "nice_name": "Test Certificate",
            "provider": "letsencrypt",
            "meta": {"letsencrypt_email": "admin@example.com"},
            "created_on": "2026-01-04T10:00:00.000Z",
            "modified_on": "2026-01-04T10:00:00.000Z",
            "expires_on": "2026-04-04T10:00:00.000Z",
            "owner_user_id": 1
        }
        mock_cert_response.raise_for_status = Mock()

        # Mock proxy host list response (empty)
        mock_list_response = Mock()
        mock_list_response.status_code = 200
        mock_list_response.json.return_value = []
        mock_list_response.raise_for_status = Mock()

        mock_http_client = MagicMock()
        mock_http_client.request.side_effect = [
            mock_cert_response,      # POST /api/nginx/certificates
            mock_list_response       # GET /api/nginx/proxy-hosts (empty)
        ]
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        cert_create = CertificateCreate(
            domain_names=["nonexistent.example.com"],
            meta={"letsencrypt_email": "admin@example.com"}
        )

        client = NPMClient(base_url="http://localhost:81")

        with pytest.raises(ValueError, match="Proxy host not found for domain: nonexistent.example.com"):
            client.attach_certificate_to_proxy(
                domain="nonexistent.example.com",
                cert=cert_create
            )

    def test_attach_certificate_to_proxy_cert_creation_failure(self, mocker, tmp_path):
        """Should propagate NPMAPIError if certificate creation fails."""
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

        # Mock certificate creation failure
        mock_cert_response = Mock()
        mock_cert_response.status_code = 400
        mock_cert_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request",
            request=Mock(),
            response=mock_cert_response
        )

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_cert_response
        mocker.patch("npm_cli.api.client.httpx.Client", return_value=mock_http_client)

        cert_create = CertificateCreate(
            domain_names=["test.com"],
            meta={"letsencrypt_email": "admin@test.com"}
        )

        client = NPMClient(base_url="http://localhost:81")

        with pytest.raises(NPMAPIError, match="Failed to create certificate"):
            client.attach_certificate_to_proxy(
                domain="test.com",
                cert=cert_create
            )
