"""NPM API client with JWT authentication and token caching.

This module provides the NPMClient class for interacting with the NPM API.
It handles JWT bearer token authentication, token caching to file, and
expiry validation before requests.

Token caching strategy:
- Tokens stored at ~/.npm-cli/token.json
- File-based caching (not keyring, as specified in plan)
- Expiry checked before each request
- Returns None if expired, prompting re-authentication
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from npm_cli.api.models import TokenRequest, TokenResponse


class NPMClient:
    """HTTP client for NPM API with automatic JWT authentication.

    Manages JWT bearer token lifecycle including authentication,
    file-based caching, and expiry validation.

    Example:
        >>> client = NPMClient(base_url="http://localhost:81")
        >>> client.authenticate(username="admin@example.com", password="secret")
        >>> response = client.request("GET", "/api/proxy-hosts")
    """

    def __init__(self, base_url: str, timeout: float = 30.0):
        """Initialize NPM API client.

        Args:
            base_url: NPM API base URL (e.g., http://localhost:81)
            timeout: Request timeout in seconds (default: 30.0)
        """
        self.base_url = base_url
        self.client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            headers={"Content-Type": "application/json; charset=UTF-8"}
        )
        self._token_path = Path.home() / ".npm-cli" / "token.json"

    def authenticate(self, username: str, password: str) -> None:
        """Authenticate with NPM API and cache token to file.

        Args:
            username: NPM username (email)
            password: NPM password

        Raises:
            httpx.HTTPStatusError: If authentication fails (401, etc.)
        """
        # Create TokenRequest using Pydantic model
        request_data = TokenRequest(identity=username, secret=password)

        # Call NPM authentication endpoint
        response = self.client.post("/api/tokens", json=request_data.model_dump())

        # Provide detailed error for debugging
        if not response.is_success:
            try:
                error_detail = response.json()
            except Exception:
                error_detail = response.text
            raise httpx.HTTPStatusError(
                f"Authentication failed: {response.status_code} - {error_detail}",
                request=response.request,
                response=response
            )

        response.raise_for_status()

        # Parse response using Pydantic model
        token_response = TokenResponse(**response.json())

        # Save token to file
        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        token_data = {
            "token": token_response.token,
            "expires": token_response.expires
        }
        self._token_path.write_text(json.dumps(token_data))

    def _get_token(self) -> str | None:
        """Get cached token if valid, otherwise None.

        Returns:
            JWT token string if valid and not expired, None otherwise
        """
        if not self._token_path.exists():
            return None

        try:
            token_data = json.loads(self._token_path.read_text())
            token = token_data["token"]
            expires_str = token_data["expires"]

            # Parse ISO 8601 timestamp (NPM format: 2026-01-05T10:32:00.000Z)
            expires = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))

            # Check if token is still valid
            if expires > datetime.now(timezone.utc):
                return token

            return None
        except (json.JSONDecodeError, KeyError, ValueError):
            # Invalid token file format
            return None

    def request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Make authenticated request to NPM API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path (e.g., /api/proxy-hosts)
            **kwargs: Additional arguments passed to httpx request

        Returns:
            httpx.Response object

        Raises:
            RuntimeError: If token is missing or expired
        """
        token = self._get_token()
        if not token:
            raise RuntimeError(
                "Token expired or missing. Please authenticate using "
                "client.authenticate(username, password)"
            )

        # Add Authorization header
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        return self.client.request(method, endpoint, headers=headers, **kwargs)
