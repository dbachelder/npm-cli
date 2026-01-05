"""NPM CLI configuration settings with environment variable support."""

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class NPMSettings(BaseSettings):
    """NPM CLI configuration with layered loading from environment variables.

    Configuration is loaded from environment variables with NPM_ prefix
    and optional .env file. All fields have sensible defaults except
    username/password which are optional and can be stored in keyring instead.

    Example:
        # Load from environment
        settings = NPMSettings()

        # Override specific values
        settings = NPMSettings(api_url="http://192.168.1.100:81")

        # Environment variables:
        # NPM_API_URL=http://localhost:81
        # NPM_CONTAINER_NAME=nginx-proxy-manager
        # NPM_USERNAME=admin@example.com
        # NPM_PASSWORD=secret
        # NPM_USE_DOCKER_DISCOVERY=true
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="NPM_",
        extra="ignore",
    )

    api_url: HttpUrl = Field(
        default="http://localhost:81",
        description="NPM API base URL (HTTP or HTTPS)",
    )

    container_name: str = Field(
        default="nginx-proxy-manager",
        description="Docker container name for NPM",
    )

    username: str | None = Field(
        default=None,
        description="NPM username (optional, can use keyring instead)",
    )

    password: str | None = Field(
        default=None,
        description="NPM password (optional, can use keyring instead)",
    )

    use_docker_discovery: bool = Field(
        default=True,
        description="Auto-discover NPM container via Docker API",
    )
