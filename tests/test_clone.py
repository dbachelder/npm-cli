"""Tests for proxy host cloning functionality."""

import pytest
from unittest.mock import Mock, patch

from npm_cli.api.client import NPMClient
from npm_cli.api.models import ProxyHost, Certificate


@pytest.fixture
def mock_client():
    """Create NPMClient with mocked authentication."""
    with patch("npm_cli.api.client.NPMClient.authenticate"):
        client = NPMClient(base_url="http://localhost:81")
        client._get_token = Mock(return_value="mock-token")
        return client


@pytest.fixture
def source_proxy_without_cert():
    """Source proxy host without certificate."""
    return ProxyHost(
        id=1,
        domain_names=["source.example.com"],
        forward_scheme="http",
        forward_host="192.168.1.100",
        forward_port=8080,
        certificate_id=None,
        ssl_forced=False,
        hsts_enabled=False,
        hsts_subdomains=False,
        http2_support=True,
        block_exploits=True,
        caching_enabled=False,
        allow_websocket_upgrade=True,
        access_list_id=0,
        advanced_config="# Custom config\nlocation /api { deny all; }",
        enabled=True,
        meta={},
        locations=None,
        created_on="2026-01-05T10:00:00.000Z",
        modified_on="2026-01-05T10:00:00.000Z",
        owner_user_id=1,
    )


@pytest.fixture
def source_proxy_with_cert():
    """Source proxy host with certificate."""
    return ProxyHost(
        id=2,
        domain_names=["secure.example.com"],
        forward_scheme="https",
        forward_host="backend.local",
        forward_port=443,
        certificate_id=42,
        ssl_forced=True,
        hsts_enabled=True,
        hsts_subdomains=True,
        http2_support=True,
        block_exploits=True,
        caching_enabled=False,
        allow_websocket_upgrade=False,
        access_list_id=5,
        advanced_config="# Authentik config\nproxy_pass http://backend;",
        enabled=True,
        meta={"custom": "data"},
        locations=None,
        created_on="2026-01-05T09:00:00.000Z",
        modified_on="2026-01-05T09:30:00.000Z",
        owner_user_id=1,
    )


@pytest.fixture
def created_certificate():
    """Mock created certificate."""
    return Certificate(
        id=99,
        domain_names=["new.example.com"],
        nice_name="",
        provider="letsencrypt",
        meta={},
        created_on="2026-01-05T11:00:00.000Z",
        modified_on="2026-01-05T11:00:00.000Z",
        expires_on="2026-04-05T11:00:00.000Z",
        owner_user_id=1,
    )


@pytest.fixture
def cloned_proxy():
    """Mock cloned proxy host."""
    return ProxyHost(
        id=10,
        domain_names=["new.example.com"],
        forward_scheme="http",
        forward_host="192.168.1.100",
        forward_port=8080,
        certificate_id=None,
        ssl_forced=False,
        hsts_enabled=False,
        hsts_subdomains=False,
        http2_support=True,
        block_exploits=True,
        caching_enabled=False,
        allow_websocket_upgrade=True,
        access_list_id=0,
        advanced_config="# Custom config\nlocation /api { deny all; }",
        enabled=True,
        meta={},
        locations=None,
        created_on="2026-01-05T11:00:00.000Z",
        modified_on="2026-01-05T11:00:00.000Z",
        owner_user_id=1,
    )


class TestCloneProxyHost:
    """Test suite for clone_proxy_host method."""

    def test_clone_without_certificate_by_id(
        self, mock_client, source_proxy_without_cert, cloned_proxy
    ):
        """Test cloning proxy by ID without SSL certificate."""
        # Mock get_proxy_host to return source
        mock_client.get_proxy_host = Mock(return_value=source_proxy_without_cert)

        # Mock create_proxy_host to return cloned proxy
        mock_client.create_proxy_host = Mock(return_value=cloned_proxy)

        # Clone by ID
        result = mock_client.clone_proxy_host(
            source_identifier=1,
            new_domains=["new.example.com"],
            provision_ssl=True  # Should skip SSL since source has none
        )

        # Verify get_proxy_host was called with source ID
        mock_client.get_proxy_host.assert_called_once_with(1)

        # Verify create_proxy_host was called with correct data
        create_call = mock_client.create_proxy_host.call_args[0][0]
        assert create_call.domain_names == ["new.example.com"]
        assert create_call.forward_scheme == "http"
        assert create_call.forward_host == "192.168.1.100"
        assert create_call.forward_port == 8080
        assert create_call.certificate_id is None
        assert create_call.ssl_forced is False
        assert create_call.hsts_enabled is False
        assert create_call.hsts_subdomains is False
        assert create_call.http2_support is True
        assert create_call.block_exploits is True
        assert create_call.caching_enabled is False
        assert create_call.allow_websocket_upgrade is True
        assert create_call.access_list_id == 0
        assert create_call.advanced_config == "# Custom config\nlocation /api { deny all; }"
        assert create_call.enabled is True

        # Verify result
        assert result == cloned_proxy

    def test_clone_without_certificate_by_domain(
        self, mock_client, source_proxy_without_cert, cloned_proxy
    ):
        """Test cloning proxy by domain name without SSL certificate."""
        # Mock list_proxy_hosts to return source in list
        mock_client.list_proxy_hosts = Mock(return_value=[source_proxy_without_cert])

        # Mock create_proxy_host to return cloned proxy
        mock_client.create_proxy_host = Mock(return_value=cloned_proxy)

        # Clone by domain name
        result = mock_client.clone_proxy_host(
            source_identifier="source.example.com",
            new_domains=["new.example.com"],
            provision_ssl=False
        )

        # Verify list_proxy_hosts was called
        mock_client.list_proxy_hosts.assert_called_once()

        # Verify create_proxy_host was called
        assert mock_client.create_proxy_host.called

        # Verify result
        assert result == cloned_proxy

    def test_clone_with_certificate_provisioning(
        self, mock_client, source_proxy_with_cert, created_certificate
    ):
        """Test cloning proxy with automatic SSL certificate provisioning."""
        # Mock get_proxy_host to return source with cert
        mock_client.get_proxy_host = Mock(return_value=source_proxy_with_cert)

        # Mock certificate_create to return new certificate
        mock_client.certificate_create = Mock(return_value=created_certificate)

        # Mock create_proxy_host to return cloned proxy with new cert
        cloned_with_cert = ProxyHost(
            id=11,
            domain_names=["new.example.com"],
            forward_scheme="https",
            forward_host="backend.local",
            forward_port=443,
            certificate_id=99,  # New certificate ID
            ssl_forced=True,
            hsts_enabled=True,
            hsts_subdomains=True,
            http2_support=True,
            block_exploits=True,
            caching_enabled=False,
            allow_websocket_upgrade=False,
            access_list_id=5,
            advanced_config="# Authentik config\nproxy_pass http://backend;",
            enabled=True,
            meta={"custom": "data"},
            locations=None,
            created_on="2026-01-05T11:00:00.000Z",
            modified_on="2026-01-05T11:00:00.000Z",
            owner_user_id=1,
        )
        mock_client.create_proxy_host = Mock(return_value=cloned_with_cert)

        # Clone by ID with SSL provisioning
        result = mock_client.clone_proxy_host(
            source_identifier=2,
            new_domains=["new.example.com"],
            provision_ssl=True
        )

        # Verify certificate was created
        cert_create_call = mock_client.certificate_create.call_args[0][0]
        assert cert_create_call.provider == "letsencrypt"
        assert cert_create_call.domain_names == ["new.example.com"]
        assert cert_create_call.meta == {}

        # Verify proxy was created with new certificate
        create_call = mock_client.create_proxy_host.call_args[0][0]
        assert create_call.domain_names == ["new.example.com"]
        assert create_call.certificate_id == 99
        assert create_call.ssl_forced is True
        assert create_call.hsts_enabled is True
        assert create_call.hsts_subdomains is True
        assert create_call.access_list_id == 5
        assert create_call.advanced_config == "# Authentik config\nproxy_pass http://backend;"

        # Verify result
        assert result == cloned_with_cert

    def test_clone_with_certificate_skip_provisioning(
        self, mock_client, source_proxy_with_cert
    ):
        """Test cloning proxy with --no-ssl flag (skip certificate provisioning)."""
        # Mock get_proxy_host to return source with cert
        mock_client.get_proxy_host = Mock(return_value=source_proxy_with_cert)

        # Mock create_proxy_host
        cloned_no_cert = ProxyHost(
            id=12,
            domain_names=["test.example.com"],
            forward_scheme="https",
            forward_host="backend.local",
            forward_port=443,
            certificate_id=None,  # No certificate
            ssl_forced=False,  # Will be reset since no cert
            hsts_enabled=False,
            hsts_subdomains=False,
            http2_support=True,
            block_exploits=True,
            caching_enabled=False,
            allow_websocket_upgrade=False,
            access_list_id=5,
            advanced_config="# Authentik config\nproxy_pass http://backend;",
            enabled=True,
            meta={"custom": "data"},
            locations=None,
            created_on="2026-01-05T11:00:00.000Z",
            modified_on="2026-01-05T11:00:00.000Z",
            owner_user_id=1,
        )
        mock_client.create_proxy_host = Mock(return_value=cloned_no_cert)

        # Clone with provision_ssl=False
        result = mock_client.clone_proxy_host(
            source_identifier=2,
            new_domains=["test.example.com"],
            provision_ssl=False
        )

        # Verify certificate_create was NOT called
        assert not hasattr(mock_client, "certificate_create") or not mock_client.certificate_create.called

        # Verify proxy was created without certificate
        create_call = mock_client.create_proxy_host.call_args[0][0]
        assert create_call.certificate_id is None

        # Verify result
        assert result == cloned_no_cert

    def test_clone_domain_not_found(self, mock_client):
        """Test cloning with non-existent domain raises ValueError."""
        # Mock list_proxy_hosts to return empty list
        mock_client.list_proxy_hosts = Mock(return_value=[])

        # Should raise ValueError
        with pytest.raises(ValueError, match="not found"):
            mock_client.clone_proxy_host(
                source_identifier="nonexistent.example.com",
                new_domains=["new.example.com"],
                provision_ssl=False
            )

    def test_clone_domain_multiple_matches(
        self, mock_client, source_proxy_without_cert
    ):
        """Test cloning with multiple domain matches raises ValueError."""
        # Create two proxies with overlapping domains
        proxy1 = source_proxy_without_cert
        proxy2 = ProxyHost(
            id=3,
            domain_names=["source.example.com", "another.com"],
            forward_scheme="http",
            forward_host="10.0.0.1",
            forward_port=9000,
            certificate_id=None,
            ssl_forced=False,
            hsts_enabled=False,
            hsts_subdomains=False,
            http2_support=True,
            block_exploits=True,
            caching_enabled=False,
            allow_websocket_upgrade=False,
            access_list_id=0,
            advanced_config="",
            enabled=True,
            meta={},
            locations=None,
            created_on="2026-01-05T10:00:00.000Z",
            modified_on="2026-01-05T10:00:00.000Z",
            owner_user_id=1,
        )

        # Mock list_proxy_hosts to return both proxies
        mock_client.list_proxy_hosts = Mock(return_value=[proxy1, proxy2])

        # Should raise ValueError for multiple matches
        with pytest.raises(ValueError, match="Multiple proxy hosts found"):
            mock_client.clone_proxy_host(
                source_identifier="source.example.com",
                new_domains=["new.example.com"],
                provision_ssl=False
            )

    def test_clone_multiple_new_domains(
        self, mock_client, source_proxy_without_cert
    ):
        """Test cloning to multiple new domains."""
        # Mock get_proxy_host to return source
        mock_client.get_proxy_host = Mock(return_value=source_proxy_without_cert)

        # Mock create_proxy_host
        cloned_multi = ProxyHost(
            id=13,
            domain_names=["app1.local", "app2.local", "app3.local"],
            forward_scheme="http",
            forward_host="192.168.1.100",
            forward_port=8080,
            certificate_id=None,
            ssl_forced=False,
            hsts_enabled=False,
            hsts_subdomains=False,
            http2_support=True,
            block_exploits=True,
            caching_enabled=False,
            allow_websocket_upgrade=True,
            access_list_id=0,
            advanced_config="# Custom config\nlocation /api { deny all; }",
            enabled=True,
            meta={},
            locations=None,
            created_on="2026-01-05T11:00:00.000Z",
            modified_on="2026-01-05T11:00:00.000Z",
            owner_user_id=1,
        )
        mock_client.create_proxy_host = Mock(return_value=cloned_multi)

        # Clone to multiple domains
        result = mock_client.clone_proxy_host(
            source_identifier=1,
            new_domains=["app1.local", "app2.local", "app3.local"],
            provision_ssl=False
        )

        # Verify create was called with all domains
        create_call = mock_client.create_proxy_host.call_args[0][0]
        assert create_call.domain_names == ["app1.local", "app2.local", "app3.local"]

        # Verify result
        assert result == cloned_multi
