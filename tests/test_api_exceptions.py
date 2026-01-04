"""Tests for API exception classes."""

import httpx
import pytest
from pydantic import ValidationError

from npm_cli.api.exceptions import NPMAPIError, NPMConnectionError, NPMValidationError


def test_npm_api_error_basic():
    """NPMAPIError can be created with just a message."""
    error = NPMAPIError("Something went wrong")
    assert str(error) == "Something went wrong"
    assert error.response is None


def test_npm_api_error_with_response():
    """NPMAPIError preserves response object for debugging."""
    # Create mock response
    request = httpx.Request("GET", "http://test/api/proxy-hosts")
    response = httpx.Response(
        status_code=500,
        request=request,
        content=b'{"error": "Internal server error"}'
    )

    error = NPMAPIError("API request failed", response=response)

    assert "API request failed" in str(error)
    assert error.response is response
    assert error.response.status_code == 500
    assert error.response.text == '{"error": "Internal server error"}'


def test_npm_api_error_str_includes_status_code():
    """NPMAPIError string representation includes status code when response present."""
    request = httpx.Request("POST", "http://test/api/tokens")
    response = httpx.Response(
        status_code=401,
        request=request,
        content=b"Unauthorized"
    )

    error = NPMAPIError("Authentication failed", response=response)
    error_str = str(error)

    assert "401" in error_str
    assert "Authentication failed" in error_str


def test_npm_connection_error_inheritance():
    """NPMConnectionError is a subclass of NPMAPIError."""
    error = NPMConnectionError("Cannot connect to NPM")

    assert isinstance(error, NPMAPIError)
    assert isinstance(error, Exception)
    assert str(error) == "Cannot connect to NPM"


def test_npm_connection_error_helpful_message():
    """NPMConnectionError provides helpful troubleshooting context."""
    error = NPMConnectionError("Cannot connect to NPM at http://localhost:81")
    error_str = str(error)

    assert "Cannot connect" in error_str
    assert "http://localhost:81" in error_str


def test_npm_validation_error_preserves_pydantic_error():
    """NPMValidationError preserves original Pydantic ValidationError."""
    # Create a Pydantic model to generate a real ValidationError
    from pydantic import BaseModel, Field

    class TestModel(BaseModel):
        required_field: str = Field(min_length=1)

    try:
        TestModel(required_field="")  # Will fail min_length validation
        pytest.fail("Should have raised ValidationError")
    except ValidationError as ve:
        error = NPMValidationError("Schema validation failed", validation_error=ve)

        assert isinstance(error, NPMAPIError)
        assert error.validation_error is ve
        assert "Schema validation failed" in str(error)


def test_npm_validation_error_str_includes_details():
    """NPMValidationError string includes validation error details."""
    from pydantic import BaseModel, Field

    class TestModel(BaseModel):
        port: int = Field(ge=1, le=65535)

    try:
        TestModel(port=99999)  # Invalid port
        pytest.fail("Should have raised ValidationError")
    except ValidationError as ve:
        error = NPMValidationError("Invalid port range", validation_error=ve)
        error_str = str(error)

        assert "Invalid port range" in error_str
        # Pydantic error details should be included
        assert "port" in error_str.lower()


def test_npm_validation_error_without_pydantic_error():
    """NPMValidationError can be created without validation_error (optional)."""
    error = NPMValidationError("Generic validation failure")

    assert str(error) == "Generic validation failure"
    assert error.validation_error is None
