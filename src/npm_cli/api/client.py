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
from pydantic import ValidationError

from npm_cli.api.models import (
    TokenRequest,
    TokenResponse,
    ProxyHost,
    ProxyHostCreate,
    ProxyHostUpdate,
)
from npm_cli.api.exceptions import NPMAPIError, NPMConnectionError, NPMValidationError


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

    def list_proxy_hosts(self) -> list[ProxyHost]:
        """List all proxy hosts from NPM.

        Returns:
            List of ProxyHost objects

        Raises:
            NPMConnectionError: If NPM API cannot be reached
            NPMAPIError: If NPM API returns an error response
            NPMValidationError: If response schema doesn't match expected format
        """
        try:
            response = self.request("GET", "/api/nginx/proxy-hosts")
            response.raise_for_status()
            data = response.json()
            return [ProxyHost.model_validate(item) for item in data]
        except httpx.ConnectError:
            raise NPMConnectionError(f"Cannot connect to NPM at {self.base_url}")
        except httpx.HTTPStatusError as e:
            raise NPMAPIError(
                f"Failed to list proxy hosts: {e.response.status_code}",
                response=e.response
            )
        except ValidationError as e:
            raise NPMValidationError(
                "NPM API response schema changed",
                validation_error=e
            )

    def get_proxy_host(self, host_id: int) -> ProxyHost:
        """Get single proxy host by ID.

        Args:
            host_id: Proxy host ID to retrieve

        Returns:
            ProxyHost object

        Raises:
            NPMConnectionError: If NPM API cannot be reached
            NPMAPIError: If proxy host not found or other API error
            NPMValidationError: If response schema doesn't match expected format
        """
        try:
            response = self.request("GET", f"/api/nginx/proxy-hosts/{host_id}")
            response.raise_for_status()
            return ProxyHost.model_validate(response.json())
        except httpx.ConnectError:
            raise NPMConnectionError(f"Cannot connect to NPM at {self.base_url}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise NPMAPIError(f"Proxy host {host_id} not found")
            raise NPMAPIError(
                f"Failed to get proxy host: {e.response.status_code}",
                response=e.response
            )
        except ValidationError as e:
            raise NPMValidationError(
                "NPM API response schema changed",
                validation_error=e
            )

    def create_proxy_host(self, host: ProxyHostCreate) -> ProxyHost:
        """Create new proxy host.

        Args:
            host: ProxyHostCreate model with proxy host configuration

        Returns:
            ProxyHost object with server-generated fields

        Raises:
            NPMConnectionError: If NPM API cannot be reached
            NPMAPIError: If NPM API returns an error response
            NPMValidationError: If response schema doesn't match expected format
        """
        try:
            response = self.request(
                "POST",
                "/api/nginx/proxy-hosts",
                json=host.model_dump(exclude_none=True, mode="json")
            )
            response.raise_for_status()
            return ProxyHost.model_validate(response.json())
        except httpx.ConnectError:
            raise NPMConnectionError(f"Cannot connect to NPM at {self.base_url}")
        except httpx.HTTPStatusError as e:
            raise NPMAPIError(
                f"Failed to create proxy host: {e.response.status_code}",
                response=e.response
            )
        except ValidationError as e:
            raise NPMValidationError(
                "NPM API response schema changed",
                validation_error=e
            )

    def update_proxy_host(self, host_id: int, updates: ProxyHostUpdate) -> ProxyHost:
        """Update existing proxy host.

        The NPM API requires the full object for PUT requests, but only accepts
        writable fields (rejects read-only fields like id, created_on, etc).
        So we:
        1. GET the current proxy host
        2. Extract only writable fields (ProxyHostCreate fields)
        3. Merge the updates into writable fields
        4. PUT the merged writable fields back

        Args:
            host_id: Proxy host ID to update
            updates: ProxyHostUpdate model with fields to update (partial)

        Returns:
            Updated ProxyHost object

        Raises:
            NPMConnectionError: If NPM API cannot be reached
            NPMAPIError: If proxy host not found or other API error
            NPMValidationError: If response schema doesn't match expected format
        """
        try:
            # First, get the current proxy host
            current = self.get_proxy_host(host_id)

            # Convert to ProxyHostCreate (only writable fields, excludes id/created_on/etc)
            writable_fields = ProxyHostCreate.model_fields.keys()
            current_data = {
                k: v for k, v in current.model_dump(mode="json").items()
                if k in writable_fields
            }

            # Normalize null locations to empty array (API requires array, not null)
            if current_data.get("locations") is None:
                current_data["locations"] = []

            # Merge updates into writable fields
            update_data = updates.model_dump(exclude_none=True, mode="json")
            current_data.update(update_data)

            # Send only writable fields back
            response = self.request(
                "PUT",
                f"/api/nginx/proxy-hosts/{host_id}",
                json=current_data
            )
            response.raise_for_status()
            return ProxyHost.model_validate(response.json())
        except httpx.ConnectError:
            raise NPMConnectionError(f"Cannot connect to NPM at {self.base_url}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise NPMAPIError(f"Proxy host {host_id} not found")
            raise NPMAPIError(
                f"Failed to update proxy host: {e.response.status_code}",
                response=e.response
            )
        except ValidationError as e:
            raise NPMValidationError(
                "NPM API response schema changed",
                validation_error=e
            )

    def delete_proxy_host(self, host_id: int) -> None:
        """Delete proxy host.

        Args:
            host_id: Proxy host ID to delete

        Raises:
            NPMConnectionError: If NPM API cannot be reached
            NPMAPIError: If proxy host not found or other API error
        """
        try:
            response = self.request("DELETE", f"/api/nginx/proxy-hosts/{host_id}")
            response.raise_for_status()
        except httpx.ConnectError:
            raise NPMConnectionError(f"Cannot connect to NPM at {self.base_url}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise NPMAPIError(f"Proxy host {host_id} not found")
            raise NPMAPIError(
                f"Failed to delete proxy host: {e.response.status_code}",
                response=e.response
            )
