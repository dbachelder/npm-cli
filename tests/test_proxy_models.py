"""Tests for proxy host Pydantic models."""

import pytest
from pydantic import ValidationError

from npm_cli.api.models import ProxyHost, ProxyHostCreate, ProxyHostUpdate


class TestProxyHostCreate:
    """Tests for ProxyHostCreate model (request model for POST)."""

    def test_minimal_valid_proxy_host(self):
        """ProxyHostCreate validates with only required fields."""
        data = {
            "domain_names": ["example.com"],
            "forward_scheme": "http",
            "forward_host": "backend.local",
            "forward_port": 8080,
        }
        host = ProxyHostCreate(**data)

        assert host.domain_names == ["example.com"]
        assert host.forward_scheme == "http"
        assert host.forward_host == "backend.local"
        assert host.forward_port == 8080
        # Check defaults
        assert host.certificate_id is None
        assert host.ssl_forced is False
        assert host.http2_support is True
        assert host.block_exploits is True
        assert host.enabled is True

    def test_all_fields_populated(self):
        """ProxyHostCreate accepts all valid fields."""
        data = {
            "domain_names": ["app.example.com", "www.example.com"],
            "forward_scheme": "https",
            "forward_host": "10.0.1.100",
            "forward_port": 443,
            "certificate_id": 5,
            "ssl_forced": True,
            "hsts_enabled": True,
            "hsts_subdomains": True,
            "http2_support": False,
            "block_exploits": False,
            "caching_enabled": True,
            "allow_websocket_upgrade": True,
            "access_list_id": 3,
            "advanced_config": "proxy_set_header X-Custom-Header value;",
            "enabled": False,
            "meta": {"custom": "value"},
            "locations": [{"path": "/api", "forward_host": "api.local"}],
        }
        host = ProxyHostCreate(**data)

        assert host.domain_names == ["app.example.com", "www.example.com"]
        assert host.forward_scheme == "https"
        assert host.certificate_id == 5
        assert host.ssl_forced is True
        assert host.hsts_enabled is True
        assert host.allow_websocket_upgrade is True
        assert host.meta == {"custom": "value"}
        assert host.locations == [{"path": "/api", "forward_host": "api.local"}]

    def test_ignores_extra_fields(self):
        """ProxyHostCreate ignores unknown fields (extra='ignore')."""
        data = {
            "domain_names": ["example.com"],
            "forward_scheme": "http",
            "forward_host": "backend.local",
            "forward_port": 8080,
            "unknown_field": "should be ignored",
            "extra_field": 123,
        }
        # Should not raise ValidationError
        host = ProxyHostCreate(**data)

        assert host.domain_names == ["example.com"]
        # Extra fields should be silently ignored
        assert not hasattr(host, "unknown_field")
        assert not hasattr(host, "extra_field")

    def test_requires_domain_names(self):
        """ProxyHostCreate requires domain_names field."""
        data = {
            "forward_scheme": "http",
            "forward_host": "backend.local",
            "forward_port": 8080,
        }

        with pytest.raises(ValidationError) as exc_info:
            ProxyHostCreate(**data)

        assert "domain_names" in str(exc_info.value).lower()

    def test_domain_names_min_length_one(self):
        """ProxyHostCreate requires at least one domain name."""
        data = {
            "domain_names": [],  # Empty list
            "forward_scheme": "http",
            "forward_host": "backend.local",
            "forward_port": 8080,
        }

        with pytest.raises(ValidationError) as exc_info:
            ProxyHostCreate(**data)

        assert "domain_names" in str(exc_info.value).lower()

    def test_domain_names_max_fifteen(self):
        """ProxyHostCreate enforces max 15 domain names."""
        data = {
            "domain_names": [f"domain{i}.com" for i in range(16)],  # 16 domains
            "forward_scheme": "http",
            "forward_host": "backend.local",
            "forward_port": 8080,
        }

        with pytest.raises(ValidationError) as exc_info:
            ProxyHostCreate(**data)

        assert "domain_names" in str(exc_info.value).lower()

    def test_forward_scheme_literal(self):
        """ProxyHostCreate only accepts 'http' or 'https' for forward_scheme."""
        data = {
            "domain_names": ["example.com"],
            "forward_scheme": "ftp",  # Invalid
            "forward_host": "backend.local",
            "forward_port": 8080,
        }

        with pytest.raises(ValidationError) as exc_info:
            ProxyHostCreate(**data)

        assert "forward_scheme" in str(exc_info.value).lower()

    def test_forward_host_required(self):
        """ProxyHostCreate requires forward_host field."""
        data = {
            "domain_names": ["example.com"],
            "forward_scheme": "http",
            "forward_port": 8080,
        }

        with pytest.raises(ValidationError) as exc_info:
            ProxyHostCreate(**data)

        assert "forward_host" in str(exc_info.value).lower()

    def test_forward_host_min_length(self):
        """ProxyHostCreate requires non-empty forward_host."""
        data = {
            "domain_names": ["example.com"],
            "forward_scheme": "http",
            "forward_host": "",  # Empty string
            "forward_port": 8080,
        }

        with pytest.raises(ValidationError) as exc_info:
            ProxyHostCreate(**data)

        assert "forward_host" in str(exc_info.value).lower()

    def test_forward_host_max_length(self):
        """ProxyHostCreate enforces max 255 chars for forward_host."""
        data = {
            "domain_names": ["example.com"],
            "forward_scheme": "http",
            "forward_host": "a" * 256,  # 256 chars
            "forward_port": 8080,
        }

        with pytest.raises(ValidationError) as exc_info:
            ProxyHostCreate(**data)

        assert "forward_host" in str(exc_info.value).lower()

    def test_forward_port_required(self):
        """ProxyHostCreate requires forward_port field."""
        data = {
            "domain_names": ["example.com"],
            "forward_scheme": "http",
            "forward_host": "backend.local",
        }

        with pytest.raises(ValidationError) as exc_info:
            ProxyHostCreate(**data)

        assert "forward_port" in str(exc_info.value).lower()

    def test_forward_port_range_min(self):
        """ProxyHostCreate enforces min port 1."""
        data = {
            "domain_names": ["example.com"],
            "forward_scheme": "http",
            "forward_host": "backend.local",
            "forward_port": 0,  # Invalid
        }

        with pytest.raises(ValidationError) as exc_info:
            ProxyHostCreate(**data)

        assert "forward_port" in str(exc_info.value).lower()

    def test_forward_port_range_max(self):
        """ProxyHostCreate enforces max port 65535."""
        data = {
            "domain_names": ["example.com"],
            "forward_scheme": "http",
            "forward_host": "backend.local",
            "forward_port": 65536,  # Invalid
        }

        with pytest.raises(ValidationError) as exc_info:
            ProxyHostCreate(**data)

        assert "forward_port" in str(exc_info.value).lower()

    def test_certificate_id_accepts_int(self):
        """ProxyHostCreate accepts integer for certificate_id."""
        data = {
            "domain_names": ["example.com"],
            "forward_scheme": "http",
            "forward_host": "backend.local",
            "forward_port": 8080,
            "certificate_id": 123,
        }
        host = ProxyHostCreate(**data)

        assert host.certificate_id == 123

    def test_certificate_id_accepts_new_literal(self):
        """ProxyHostCreate accepts 'new' literal for certificate_id."""
        data = {
            "domain_names": ["example.com"],
            "forward_scheme": "http",
            "forward_host": "backend.local",
            "forward_port": 8080,
            "certificate_id": "new",
        }
        host = ProxyHostCreate(**data)

        assert host.certificate_id == "new"

    def test_access_list_id_non_negative(self):
        """ProxyHostCreate enforces access_list_id >= 0."""
        data = {
            "domain_names": ["example.com"],
            "forward_scheme": "http",
            "forward_host": "backend.local",
            "forward_port": 8080,
            "access_list_id": -1,  # Invalid
        }

        with pytest.raises(ValidationError) as exc_info:
            ProxyHostCreate(**data)

        assert "access_list_id" in str(exc_info.value).lower()


class TestProxyHost:
    """Tests for ProxyHost model (response model with read-only fields)."""

    def test_inherits_from_proxy_host_create(self):
        """ProxyHost inherits all fields from ProxyHostCreate."""
        data = {
            "id": 1,
            "domain_names": ["example.com"],
            "forward_scheme": "http",
            "forward_host": "backend.local",
            "forward_port": 8080,
            "created_on": "2026-01-04T10:00:00.000Z",
            "modified_on": "2026-01-04T10:00:00.000Z",
            "owner_user_id": 1,
        }
        host = ProxyHost(**data)

        # Check inherited fields
        assert host.domain_names == ["example.com"]
        assert host.forward_scheme == "http"
        assert host.ssl_forced is False  # Inherited default

        # Check read-only fields
        assert host.id == 1
        assert host.created_on == "2026-01-04T10:00:00.000Z"
        assert host.modified_on == "2026-01-04T10:00:00.000Z"
        assert host.owner_user_id == 1

    def test_requires_id_field(self):
        """ProxyHost requires id field."""
        data = {
            "domain_names": ["example.com"],
            "forward_scheme": "http",
            "forward_host": "backend.local",
            "forward_port": 8080,
            "created_on": "2026-01-04T10:00:00.000Z",
            "modified_on": "2026-01-04T10:00:00.000Z",
            "owner_user_id": 1,
        }

        with pytest.raises(ValidationError) as exc_info:
            ProxyHost(**data)

        assert "id" in str(exc_info.value).lower()

    def test_id_must_be_positive(self):
        """ProxyHost enforces id >= 1."""
        data = {
            "id": 0,  # Invalid
            "domain_names": ["example.com"],
            "forward_scheme": "http",
            "forward_host": "backend.local",
            "forward_port": 8080,
            "created_on": "2026-01-04T10:00:00.000Z",
            "modified_on": "2026-01-04T10:00:00.000Z",
            "owner_user_id": 1,
        }

        with pytest.raises(ValidationError) as exc_info:
            ProxyHost(**data)

        assert "id" in str(exc_info.value).lower()

    def test_requires_created_on(self):
        """ProxyHost requires created_on field."""
        data = {
            "id": 1,
            "domain_names": ["example.com"],
            "forward_scheme": "http",
            "forward_host": "backend.local",
            "forward_port": 8080,
            "modified_on": "2026-01-04T10:00:00.000Z",
            "owner_user_id": 1,
        }

        with pytest.raises(ValidationError) as exc_info:
            ProxyHost(**data)

        assert "created_on" in str(exc_info.value).lower()

    def test_requires_modified_on(self):
        """ProxyHost requires modified_on field."""
        data = {
            "id": 1,
            "domain_names": ["example.com"],
            "forward_scheme": "http",
            "forward_host": "backend.local",
            "forward_port": 8080,
            "created_on": "2026-01-04T10:00:00.000Z",
            "owner_user_id": 1,
        }

        with pytest.raises(ValidationError) as exc_info:
            ProxyHost(**data)

        assert "modified_on" in str(exc_info.value).lower()

    def test_requires_owner_user_id(self):
        """ProxyHost requires owner_user_id field."""
        data = {
            "id": 1,
            "domain_names": ["example.com"],
            "forward_scheme": "http",
            "forward_host": "backend.local",
            "forward_port": 8080,
            "created_on": "2026-01-04T10:00:00.000Z",
            "modified_on": "2026-01-04T10:00:00.000Z",
        }

        with pytest.raises(ValidationError) as exc_info:
            ProxyHost(**data)

        assert "owner_user_id" in str(exc_info.value).lower()

    def test_owner_user_id_must_be_positive(self):
        """ProxyHost enforces owner_user_id >= 1."""
        data = {
            "id": 1,
            "domain_names": ["example.com"],
            "forward_scheme": "http",
            "forward_host": "backend.local",
            "forward_port": 8080,
            "created_on": "2026-01-04T10:00:00.000Z",
            "modified_on": "2026-01-04T10:00:00.000Z",
            "owner_user_id": 0,  # Invalid
        }

        with pytest.raises(ValidationError) as exc_info:
            ProxyHost(**data)

        assert "owner_user_id" in str(exc_info.value).lower()


class TestProxyHostUpdate:
    """Tests for ProxyHostUpdate model (request model for PUT)."""

    def test_all_fields_optional(self):
        """ProxyHostUpdate allows empty update (all fields optional)."""
        host = ProxyHostUpdate()

        assert host.domain_names is None
        assert host.forward_scheme is None
        assert host.forward_host is None
        assert host.forward_port is None

    def test_partial_update_domain_names_only(self):
        """ProxyHostUpdate accepts only domain_names."""
        data = {"domain_names": ["newdomain.com"]}
        host = ProxyHostUpdate(**data)

        assert host.domain_names == ["newdomain.com"]
        assert host.forward_scheme is None

    def test_partial_update_multiple_fields(self):
        """ProxyHostUpdate accepts any subset of fields."""
        data = {
            "forward_port": 9090,
            "ssl_forced": True,
            "enabled": False,
        }
        host = ProxyHostUpdate(**data)

        assert host.forward_port == 9090
        assert host.ssl_forced is True
        assert host.enabled is False
        assert host.domain_names is None

    def test_ignores_extra_fields(self):
        """ProxyHostUpdate ignores unknown fields (extra='ignore')."""
        data = {
            "domain_names": ["example.com"],
            "invalid_field": "should be ignored",
            "extra_field": 999,
        }
        # Should not raise ValidationError
        host = ProxyHostUpdate(**data)

        assert host.domain_names == ["example.com"]
        # Extra fields should be silently ignored
        assert not hasattr(host, "invalid_field")
        assert not hasattr(host, "extra_field")

    def test_validates_domain_names_when_provided(self):
        """ProxyHostUpdate validates domain_names constraints when provided."""
        # Max 15 domains
        data = {"domain_names": [f"domain{i}.com" for i in range(16)]}

        with pytest.raises(ValidationError) as exc_info:
            ProxyHostUpdate(**data)

        assert "domain_names" in str(exc_info.value).lower()

    def test_validates_forward_scheme_when_provided(self):
        """ProxyHostUpdate validates forward_scheme literal when provided."""
        data = {"forward_scheme": "ftp"}  # Invalid

        with pytest.raises(ValidationError) as exc_info:
            ProxyHostUpdate(**data)

        assert "forward_scheme" in str(exc_info.value).lower()

    def test_validates_forward_port_range_when_provided(self):
        """ProxyHostUpdate validates port range when provided."""
        data = {"forward_port": 70000}  # Out of range

        with pytest.raises(ValidationError) as exc_info:
            ProxyHostUpdate(**data)

        assert "forward_port" in str(exc_info.value).lower()

    def test_certificate_id_optional_types(self):
        """ProxyHostUpdate accepts int, 'new', or None for certificate_id."""
        # Test with int
        host1 = ProxyHostUpdate(certificate_id=5)
        assert host1.certificate_id == 5

        # Test with 'new'
        host2 = ProxyHostUpdate(certificate_id="new")
        assert host2.certificate_id == "new"

        # Test with None (default)
        host3 = ProxyHostUpdate()
        assert host3.certificate_id is None
