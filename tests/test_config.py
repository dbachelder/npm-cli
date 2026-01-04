"""Tests for NPM configuration settings."""

import pytest
from pydantic import ValidationError

from npm_cli.config.settings import NPMSettings


def test_valid_config_loads_successfully():
    """Valid configuration with all fields loads successfully."""
    settings = NPMSettings(
        api_url="http://localhost:81",
        container_name="nginx-proxy-manager",
        username="admin@example.com",
        password="secret",
        use_docker_discovery=True,
    )
    assert str(settings.api_url) == "http://localhost:81/"
    assert settings.container_name == "nginx-proxy-manager"
    assert settings.username == "admin@example.com"
    assert settings.password == "secret"
    assert settings.use_docker_discovery is True


def test_missing_required_fields_use_defaults(monkeypatch, tmp_path):
    """Missing optional fields use default values."""
    # Clear NPM_ environment variables to test defaults
    for key in ["NPM_API_URL", "NPM_CONTAINER_NAME", "NPM_USERNAME", "NPM_PASSWORD", "NPM_USE_DOCKER_DISCOVERY"]:
        monkeypatch.delenv(key, raising=False)

    # Change to temp directory to avoid loading project .env file
    monkeypatch.chdir(tmp_path)

    settings = NPMSettings()
    assert str(settings.api_url) == "http://localhost:81/"
    assert settings.container_name == "nginx-proxy-manager"
    assert settings.username is None
    assert settings.password is None
    assert settings.use_docker_discovery is True


def test_invalid_url_rejected():
    """Invalid URL (not HTTP/HTTPS) raises validation error."""
    with pytest.raises(ValidationError) as exc_info:
        NPMSettings(api_url="ftp://localhost:81")

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("api_url",)
    assert "url" in errors[0]["type"]


def test_extra_fields_rejected():
    """Extra fields not in schema are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        NPMSettings(
            api_url="http://localhost:81",
            extra_field="should_not_exist"
        )

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert "extra_forbidden" in errors[0]["type"]


def test_api_url_validates_as_http_url():
    """API URL is validated as HttpUrl type."""
    # Valid HTTP URL
    settings = NPMSettings(api_url="http://192.168.1.100:81")
    assert str(settings.api_url) == "http://192.168.1.100:81/"

    # Valid HTTPS URL
    settings = NPMSettings(api_url="https://npm.example.com")
    assert str(settings.api_url) == "https://npm.example.com/"


def test_env_prefix_npm():
    """Settings load from environment with NPM_ prefix."""
    import os

    # Set environment variables
    os.environ["NPM_API_URL"] = "http://192.168.1.50:81"
    os.environ["NPM_CONTAINER_NAME"] = "my-npm-container"
    os.environ["NPM_USERNAME"] = "test@example.com"
    os.environ["NPM_PASSWORD"] = "testpass"
    os.environ["NPM_USE_DOCKER_DISCOVERY"] = "false"

    try:
        settings = NPMSettings()
        assert str(settings.api_url) == "http://192.168.1.50:81/"
        assert settings.container_name == "my-npm-container"
        assert settings.username == "test@example.com"
        assert settings.password == "testpass"
        assert settings.use_docker_discovery is False
    finally:
        # Clean up environment
        for key in ["NPM_API_URL", "NPM_CONTAINER_NAME", "NPM_USERNAME", "NPM_PASSWORD", "NPM_USE_DOCKER_DISCOVERY"]:
            os.environ.pop(key, None)
