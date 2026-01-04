"""Tests for NPM API client certificate CRUD operations."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock

import pytest
import httpx
from pydantic import ValidationError

from npm_cli.api.client import NPMClient
from npm_cli.api.models import Certificate, CertificateCreate
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
