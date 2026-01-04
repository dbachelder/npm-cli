"""Pydantic models for NPM API requests and responses."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TokenRequest(BaseModel):
    """Request model for NPM authentication.

    Used to authenticate with the NPM API and obtain a bearer token.
    """
    model_config = ConfigDict(extra="forbid", strict=True)

    identity: str  # User email
    secret: str    # User password


class TokenResponse(BaseModel):
    """Response model for NPM authentication.

    Contains the JWT bearer token and expiration timestamp.
    """
    model_config = ConfigDict(extra="forbid", strict=True)

    token: str      # JWT bearer token
    expires: str    # ISO 8601 timestamp


class ProxyHostCreate(BaseModel):
    """Request model for creating a proxy host.

    Used for POST /api/nginx/proxy-hosts to create new proxy host entries.
    Based on NPM JSON Schema v2.9.6.
    """
    model_config = ConfigDict(extra="ignore", strict=True)

    # Required fields
    domain_names: list[str] = Field(
        min_length=1,
        max_length=15,
        description="List of domain names to proxy (max 15)"
    )
    forward_scheme: Literal["http", "https"] = Field(
        description="Protocol for backend connection"
    )
    forward_host: str = Field(
        min_length=1,
        max_length=255,
        description="Backend hostname or IP address"
    )
    forward_port: int = Field(
        ge=1,
        le=65535,
        description="Backend port number"
    )

    # Optional fields with defaults
    certificate_id: int | Literal["new"] = Field(
        default=0,
        description="SSL certificate ID, 0 for none, 'new' to create"
    )
    ssl_forced: bool = Field(
        default=False,
        description="Force SSL/HTTPS redirect"
    )
    hsts_enabled: bool = Field(
        default=False,
        description="Enable HTTP Strict Transport Security"
    )
    hsts_subdomains: bool = Field(
        default=False,
        description="Include subdomains in HSTS"
    )
    http2_support: bool = Field(
        default=True,
        description="Enable HTTP/2 support"
    )
    block_exploits: bool = Field(
        default=True,
        description="Block common exploit paths"
    )
    caching_enabled: bool = Field(
        default=False,
        description="Enable asset caching"
    )
    allow_websocket_upgrade: bool = Field(
        default=False,
        description="Allow WebSocket protocol upgrade"
    )
    access_list_id: int = Field(
        default=0,
        ge=0,
        description="Access control list ID, 0 for none"
    )
    advanced_config: str = Field(
        default="",
        description="Custom nginx configuration"
    )
    enabled: bool = Field(
        default=True,
        description="Enable/disable this proxy host"
    )
    meta: dict = Field(
        default_factory=dict,
        description="Metadata storage"
    )
    locations: list[dict] | None = Field(
        default=None,
        description="Custom location blocks"
    )


class ProxyHost(ProxyHostCreate):
    """Response model for proxy host with read-only fields.

    Used for GET /api/nginx/proxy-hosts responses.
    Inherits all fields from ProxyHostCreate and adds server-generated fields.
    """

    id: int = Field(ge=1, description="Unique proxy host ID")
    created_on: str = Field(description="Creation timestamp (ISO 8601)")
    modified_on: str = Field(description="Last modification timestamp (ISO 8601)")
    owner_user_id: int = Field(ge=1, description="User ID who created this host")


class ProxyHostUpdate(BaseModel):
    """Request model for updating a proxy host.

    Used for PUT /api/nginx/proxy-hosts/{id} to update existing entries.
    All fields are optional to support partial updates.
    """
    model_config = ConfigDict(extra="ignore", strict=True)

    domain_names: list[str] | None = Field(
        default=None,
        min_length=1,
        max_length=15,
        description="List of domain names to proxy (max 15)"
    )
    forward_scheme: Literal["http", "https"] | None = Field(
        default=None,
        description="Protocol for backend connection"
    )
    forward_host: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Backend hostname or IP address"
    )
    forward_port: int | None = Field(
        default=None,
        ge=1,
        le=65535,
        description="Backend port number"
    )
    certificate_id: int | Literal["new"] | None = Field(
        default=None,
        description="SSL certificate ID, 0 for none, 'new' to create"
    )
    ssl_forced: bool | None = Field(
        default=None,
        description="Force SSL/HTTPS redirect"
    )
    hsts_enabled: bool | None = Field(
        default=None,
        description="Enable HTTP Strict Transport Security"
    )
    hsts_subdomains: bool | None = Field(
        default=None,
        description="Include subdomains in HSTS"
    )
    http2_support: bool | None = Field(
        default=None,
        description="Enable HTTP/2 support"
    )
    block_exploits: bool | None = Field(
        default=None,
        description="Block common exploit paths"
    )
    caching_enabled: bool | None = Field(
        default=None,
        description="Enable asset caching"
    )
    allow_websocket_upgrade: bool | None = Field(
        default=None,
        description="Allow WebSocket protocol upgrade"
    )
    access_list_id: int | None = Field(
        default=None,
        ge=0,
        description="Access control list ID, 0 for none"
    )
    advanced_config: str | None = Field(
        default=None,
        description="Custom nginx configuration"
    )
    enabled: bool | None = Field(
        default=None,
        description="Enable/disable this proxy host"
    )
    meta: dict | None = Field(
        default=None,
        description="Metadata storage"
    )
    locations: list[dict] | None = Field(
        default=None,
        description="Custom location blocks"
    )


class CertificateCreate(BaseModel):
    """Request model for creating Let's Encrypt certificate.

    Used for POST /api/nginx/certificates to create new SSL certificates via NPM.
    NPM delegates to Certbot internally for Let's Encrypt certificate acquisition.
    """
    model_config = ConfigDict(extra="ignore", strict=True)

    # Required fields
    domain_names: list[str] = Field(
        min_length=1,
        description="Domains for certificate (first is primary, rest are SANs)"
    )
    meta: dict = Field(
        description="Provider-specific metadata (letsencrypt_email, dns_provider, etc.)"
    )

    # Optional fields with defaults
    nice_name: str = Field(
        default="",
        description="Human-readable certificate name"
    )
    provider: Literal["letsencrypt"] = Field(
        default="letsencrypt",
        description="Certificate provider"
    )


class Certificate(CertificateCreate):
    """Response model for certificate with read-only fields.

    Used for GET /api/nginx/certificates responses.
    Inherits all fields from CertificateCreate and adds server-generated fields.
    """

    id: int = Field(ge=1, description="Certificate ID")
    created_on: str = Field(description="Creation timestamp (ISO 8601)")
    modified_on: str = Field(description="Last modification timestamp (ISO 8601)")
    expires_on: str = Field(description="Certificate expiration timestamp (ISO 8601)")
    owner_user_id: int = Field(ge=1, description="Owner user ID")
