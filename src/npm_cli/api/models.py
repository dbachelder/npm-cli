"""Pydantic models for NPM API requests and responses."""

from pydantic import BaseModel, ConfigDict


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
