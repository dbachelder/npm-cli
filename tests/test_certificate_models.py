"""Tests for certificate Pydantic models."""

import pytest
from pydantic import ValidationError

from npm_cli.api.models import Certificate, CertificateCreate


class TestCertificateCreate:
    """Tests for CertificateCreate model (request model for POST)."""

    def test_minimal_valid_certificate(self):
        """CertificateCreate validates with required fields (domain_names + meta)."""
        data = {
            "domain_names": ["example.com"],
            "meta": {"letsencrypt_email": "admin@example.com"},
        }
        cert = CertificateCreate(**data)

        assert cert.domain_names == ["example.com"]
        assert cert.meta == {"letsencrypt_email": "admin@example.com"}
        # Check defaults
        assert cert.nice_name == ""
        assert cert.provider == "letsencrypt"

    def test_all_fields_populated(self):
        """CertificateCreate accepts all valid fields."""
        data = {
            "domain_names": ["*.example.com", "example.com"],
            "meta": {
                "letsencrypt_email": "admin@example.com",
                "dns_provider": "cloudflare",
                "dns_provider_credentials": "dns_cloudflare_api_token = TOKEN_VALUE",
                "propagation_seconds": 30,
            },
            "nice_name": "Example Wildcard Certificate",
            "provider": "letsencrypt",
        }
        cert = CertificateCreate(**data)

        assert cert.domain_names == ["*.example.com", "example.com"]
        assert cert.meta["letsencrypt_email"] == "admin@example.com"
        assert cert.meta["dns_provider"] == "cloudflare"
        assert cert.nice_name == "Example Wildcard Certificate"
        assert cert.provider == "letsencrypt"

    def test_ignores_extra_fields(self):
        """CertificateCreate ignores unknown fields (extra='ignore')."""
        data = {
            "domain_names": ["example.com"],
            "meta": {"letsencrypt_email": "admin@example.com"},
            "unknown_field": "should be ignored",
            "extra_field": 123,
        }
        # Should not raise ValidationError
        cert = CertificateCreate(**data)

        assert cert.domain_names == ["example.com"]
        # Extra fields should be silently ignored
        assert not hasattr(cert, "unknown_field")
        assert not hasattr(cert, "extra_field")

    def test_requires_domain_names(self):
        """CertificateCreate requires domain_names field."""
        data = {
            "meta": {"letsencrypt_email": "admin@example.com"},
        }

        with pytest.raises(ValidationError) as exc_info:
            CertificateCreate(**data)

        assert "domain_names" in str(exc_info.value).lower()

    def test_domain_names_min_length_one(self):
        """CertificateCreate requires at least one domain name."""
        data = {
            "domain_names": [],  # Empty list
            "meta": {"letsencrypt_email": "admin@example.com"},
        }

        with pytest.raises(ValidationError) as exc_info:
            CertificateCreate(**data)

        assert "domain_names" in str(exc_info.value).lower()

    def test_requires_meta(self):
        """CertificateCreate requires meta field."""
        data = {
            "domain_names": ["example.com"],
        }

        with pytest.raises(ValidationError) as exc_info:
            CertificateCreate(**data)

        assert "meta" in str(exc_info.value).lower()

    def test_meta_validates_letsencrypt_email_present(self):
        """CertificateCreate meta field must contain letsencrypt_email."""
        # Note: This test validates expected usage pattern, though Pydantic
        # dict type doesn't enforce specific keys. In practice, NPM API
        # requires letsencrypt_email in meta.
        data = {
            "domain_names": ["example.com"],
            "meta": {"letsencrypt_email": "admin@example.com"},
        }
        cert = CertificateCreate(**data)

        assert "letsencrypt_email" in cert.meta
        assert cert.meta["letsencrypt_email"] == "admin@example.com"

    def test_meta_accepts_dns_provider(self):
        """CertificateCreate meta field accepts optional dns_provider."""
        data = {
            "domain_names": ["*.example.com"],
            "meta": {
                "letsencrypt_email": "admin@example.com",
                "dns_provider": "cloudflare",
            },
        }
        cert = CertificateCreate(**data)

        assert cert.meta["dns_provider"] == "cloudflare"

    def test_meta_accepts_dns_provider_credentials(self):
        """CertificateCreate meta field accepts optional dns_provider_credentials."""
        data = {
            "domain_names": ["*.example.com"],
            "meta": {
                "letsencrypt_email": "admin@example.com",
                "dns_provider": "cloudflare",
                "dns_provider_credentials": "dns_cloudflare_api_token = SECRET",
            },
        }
        cert = CertificateCreate(**data)

        assert "dns_provider_credentials" in cert.meta

    def test_provider_defaults_to_letsencrypt(self):
        """CertificateCreate provider defaults to 'letsencrypt'."""
        data = {
            "domain_names": ["example.com"],
            "meta": {"letsencrypt_email": "admin@example.com"},
        }
        cert = CertificateCreate(**data)

        assert cert.provider == "letsencrypt"

    def test_provider_only_accepts_letsencrypt(self):
        """CertificateCreate provider only accepts 'letsencrypt' literal."""
        data = {
            "domain_names": ["example.com"],
            "meta": {"letsencrypt_email": "admin@example.com"},
            "provider": "custom",  # Invalid
        }

        with pytest.raises(ValidationError) as exc_info:
            CertificateCreate(**data)

        assert "provider" in str(exc_info.value).lower()

    def test_nice_name_defaults_to_empty_string(self):
        """CertificateCreate nice_name defaults to empty string."""
        data = {
            "domain_names": ["example.com"],
            "meta": {"letsencrypt_email": "admin@example.com"},
        }
        cert = CertificateCreate(**data)

        assert cert.nice_name == ""


class TestCertificate:
    """Tests for Certificate model (response model with read-only fields)."""

    def test_inherits_from_certificate_create(self):
        """Certificate inherits all fields from CertificateCreate."""
        data = {
            "id": 1,
            "domain_names": ["example.com"],
            "meta": {"letsencrypt_email": "admin@example.com"},
            "nice_name": "My Certificate",
            "provider": "letsencrypt",
            "created_on": "2026-01-04T10:00:00.000Z",
            "modified_on": "2026-01-04T10:00:00.000Z",
            "expires_on": "2026-04-04T10:00:00.000Z",
            "owner_user_id": 1,
        }
        cert = Certificate(**data)

        # Check inherited fields
        assert cert.domain_names == ["example.com"]
        assert cert.meta["letsencrypt_email"] == "admin@example.com"
        assert cert.nice_name == "My Certificate"
        assert cert.provider == "letsencrypt"

        # Check read-only fields
        assert cert.id == 1
        assert cert.created_on == "2026-01-04T10:00:00.000Z"
        assert cert.modified_on == "2026-01-04T10:00:00.000Z"
        assert cert.expires_on == "2026-04-04T10:00:00.000Z"
        assert cert.owner_user_id == 1

    def test_requires_id_field(self):
        """Certificate requires id field."""
        data = {
            "domain_names": ["example.com"],
            "meta": {"letsencrypt_email": "admin@example.com"},
            "created_on": "2026-01-04T10:00:00.000Z",
            "modified_on": "2026-01-04T10:00:00.000Z",
            "expires_on": "2026-04-04T10:00:00.000Z",
            "owner_user_id": 1,
        }

        with pytest.raises(ValidationError) as exc_info:
            Certificate(**data)

        assert "id" in str(exc_info.value).lower()

    def test_id_must_be_positive(self):
        """Certificate enforces id >= 1."""
        data = {
            "id": 0,  # Invalid
            "domain_names": ["example.com"],
            "meta": {"letsencrypt_email": "admin@example.com"},
            "created_on": "2026-01-04T10:00:00.000Z",
            "modified_on": "2026-01-04T10:00:00.000Z",
            "expires_on": "2026-04-04T10:00:00.000Z",
            "owner_user_id": 1,
        }

        with pytest.raises(ValidationError) as exc_info:
            Certificate(**data)

        assert "id" in str(exc_info.value).lower()

    def test_requires_created_on(self):
        """Certificate requires created_on field."""
        data = {
            "id": 1,
            "domain_names": ["example.com"],
            "meta": {"letsencrypt_email": "admin@example.com"},
            "modified_on": "2026-01-04T10:00:00.000Z",
            "expires_on": "2026-04-04T10:00:00.000Z",
            "owner_user_id": 1,
        }

        with pytest.raises(ValidationError) as exc_info:
            Certificate(**data)

        assert "created_on" in str(exc_info.value).lower()

    def test_requires_modified_on(self):
        """Certificate requires modified_on field."""
        data = {
            "id": 1,
            "domain_names": ["example.com"],
            "meta": {"letsencrypt_email": "admin@example.com"},
            "created_on": "2026-01-04T10:00:00.000Z",
            "expires_on": "2026-04-04T10:00:00.000Z",
            "owner_user_id": 1,
        }

        with pytest.raises(ValidationError) as exc_info:
            Certificate(**data)

        assert "modified_on" in str(exc_info.value).lower()

    def test_requires_expires_on(self):
        """Certificate requires expires_on field."""
        data = {
            "id": 1,
            "domain_names": ["example.com"],
            "meta": {"letsencrypt_email": "admin@example.com"},
            "created_on": "2026-01-04T10:00:00.000Z",
            "modified_on": "2026-01-04T10:00:00.000Z",
            "owner_user_id": 1,
        }

        with pytest.raises(ValidationError) as exc_info:
            Certificate(**data)

        assert "expires_on" in str(exc_info.value).lower()

    def test_requires_owner_user_id(self):
        """Certificate requires owner_user_id field."""
        data = {
            "id": 1,
            "domain_names": ["example.com"],
            "meta": {"letsencrypt_email": "admin@example.com"},
            "created_on": "2026-01-04T10:00:00.000Z",
            "modified_on": "2026-01-04T10:00:00.000Z",
            "expires_on": "2026-04-04T10:00:00.000Z",
        }

        with pytest.raises(ValidationError) as exc_info:
            Certificate(**data)

        assert "owner_user_id" in str(exc_info.value).lower()

    def test_owner_user_id_must_be_positive(self):
        """Certificate enforces owner_user_id >= 1."""
        data = {
            "id": 1,
            "domain_names": ["example.com"],
            "meta": {"letsencrypt_email": "admin@example.com"},
            "created_on": "2026-01-04T10:00:00.000Z",
            "modified_on": "2026-01-04T10:00:00.000Z",
            "expires_on": "2026-04-04T10:00:00.000Z",
            "owner_user_id": 0,  # Invalid
        }

        with pytest.raises(ValidationError) as exc_info:
            Certificate(**data)

        assert "owner_user_id" in str(exc_info.value).lower()

    def test_ignores_extra_fields(self):
        """Certificate ignores unknown fields (extra='ignore')."""
        data = {
            "id": 1,
            "domain_names": ["example.com"],
            "meta": {"letsencrypt_email": "admin@example.com"},
            "created_on": "2026-01-04T10:00:00.000Z",
            "modified_on": "2026-01-04T10:00:00.000Z",
            "expires_on": "2026-04-04T10:00:00.000Z",
            "owner_user_id": 1,
            "unknown_field": "should be ignored",
            "extra_api_field": 999,
        }
        # Should not raise ValidationError
        cert = Certificate(**data)

        assert cert.id == 1
        assert cert.domain_names == ["example.com"]
        # Extra fields should be silently ignored
        assert not hasattr(cert, "unknown_field")
        assert not hasattr(cert, "extra_api_field")
