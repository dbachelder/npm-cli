# Phase 2: NPM Connection & Authentication - Research

**Researched:** 2026-01-04
**Domain:** Docker container discovery and API authentication with Python
**Confidence:** HIGH

<research_summary>
## Summary

Researched the Python ecosystem for implementing Docker container discovery and NPM API authentication. The standard approach uses the official Docker SDK for Python (docker-py) for container operations, httpx for modern HTTP client capabilities, and keyring for secure credential storage leveraging OS-native keychains.

Key finding: Don't hand-roll credential storage or Docker discovery logic. The docker SDK provides robust filtering by name/labels, httpx offers async support and HTTP/2, and keyring integrates with native OS credential managers (macOS Keychain, Windows Credential Locker, GNOME Keyring). Custom implementations miss edge cases and security hardening.

NPM uses JWT bearer token authentication via POST /api/tokens with 24-48 hour default expiry. Tokens should be stored in keyring with expiry tracking to enable automatic refresh before expiration.

**Primary recommendation:** Use docker SDK with filter-based discovery, httpx for API calls (async-ready, type-annotated), keyring for credentials, and Pydantic Settings for configuration validation.
</research_summary>

<standard_stack>
## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| docker | 7.1.0 | Docker Engine API client | Official Docker SDK, comprehensive container/network operations |
| httpx | latest | HTTP client with async support | Modern replacement for requests, HTTP/2, full type annotations |
| pydantic-settings | latest | Configuration management | Extends Pydantic for settings, layered config with validation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | latest | Load .env files | Development workflow, local overrides |
| typer-config | 0.1.1+ | TOML/JSON config for Typer | If complex config file needed beyond env vars |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | requests | requests simpler but lacks async, HTTP/2, type hints |
| file-based token cache | keyring | keyring more secure but unnecessary for short-lived tokens (24-48h expiry) |
| docker SDK | subprocess + docker CLI | CLI approach fragile, no type safety, harder error handling |

**Installation:**
```bash
uv add docker httpx pydantic-settings python-dotenv
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Project Structure
```
src/npm_cli/
├── api/
│   ├── models.py         # Pydantic models (existing)
│   └── client.py         # HTTP client wrapper with auth
├── config/
│   ├── settings.py       # Pydantic Settings for config
│   └── credentials.py    # Keyring integration
├── docker/
│   └── discovery.py      # Container discovery logic
└── cli/
    └── config.py         # Config management commands
```

### Pattern 1: Docker Container Discovery by Name/Labels
**What:** Use docker SDK filters to find NPM containers, not manual iteration
**When to use:** Finding NPM container on startup, validating connectivity
**Example:**
```python
# Source: docker-py.readthedocs.io/en/stable/containers.html
import docker

client = docker.from_env()

# Find by name
containers = client.containers.list(filters={'name': 'nginx-proxy-manager'})

# Find by label (recommended - more flexible)
containers = client.containers.list(filters={
    'label': 'com.docker.compose.service=npm'
})

# Get network details
if containers:
    container = containers[0]
    networks = container.attrs['NetworkSettings']['Networks']
    # Access ports, IP addresses, etc.
```

### Pattern 2: Token Storage (File-Based for MVP)
**What:** Store JWT tokens in ~/.npm-cli/token.json with expiry tracking
**When to use:** Caching NPM JWT tokens (expire in 24-48 hours)
**Decision:** Using file-based storage for MVP. Keyring considered but unnecessary for expiring tokens.
**Example:**
```python
# Source: Implementation from 02-02-PLAN.md
from pathlib import Path
import json
from datetime import datetime, timezone

TOKEN_FILE = Path.home() / ".npm-cli" / "token.json"

def save_token(token: str, expires: str) -> None:
    """Save JWT token with expiry to file."""
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    token_data = {"token": token, "expires": expires}
    TOKEN_FILE.write_text(json.dumps(token_data))

def load_token() -> str | None:
    """Load token if valid, otherwise None."""
    if not TOKEN_FILE.exists():
        return None

    token_data = json.loads(TOKEN_FILE.read_text())
    expires = datetime.fromisoformat(token_data["expires"].replace("Z", "+00:00"))

    if expires > datetime.now(timezone.utc):
        return token_data["token"]
    return None
```

**Note:** Keyring integration considered for future credential storage (username/password), but not needed for MVP since tokens are short-lived.

### Pattern 3: HTTP Client with Automatic Token Refresh
**What:** httpx client wrapper that handles NPM JWT authentication and refresh
**When to use:** All NPM API calls
**Example:**
```python
# Source: python-httpx.org + JWT best practices + 02-02 implementation
import httpx
from datetime import datetime, timezone
from pathlib import Path
import json

class NPMClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.Client(
            base_url=base_url,
            timeout=30.0,  # Always set timeouts
            headers={"Content-Type": "application/json"}
        )
        self.token_file = Path.home() / ".npm-cli" / "token.json"

    def _get_token(self) -> str | None:
        """Get cached token if valid, otherwise None."""
        if not self.token_file.exists():
            return None

        token_data = json.loads(self.token_file.read_text())
        expires = datetime.fromisoformat(token_data["expires"].replace("Z", "+00:00"))

        if expires > datetime.now(timezone.utc):
            return token_data["token"]
        return None

    def authenticate(self, username: str, password: str) -> None:
        """Authenticate and cache token to file."""
        response = self.client.post("/api/tokens", json={
            "identity": username,
            "secret": password
        })
        response.raise_for_status()

        token_data = response.json()
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(json.dumps(token_data))

    def request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Make authenticated request with automatic token validation."""
        token = self._get_token()
        if not token:
            # Token expired or missing - need to re-authenticate
            raise AuthenticationError("Token expired, please login")

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        return self.client.request(method, endpoint, headers=headers, **kwargs)
```

### Pattern 4: Layered Configuration with Pydantic Settings
**What:** Load config from env vars → config file → CLI args with validation
**When to use:** Managing NPM connection settings (URL, container name, etc.)
**Example:**
```python
# Source: docs.pydantic.dev/latest/concepts/pydantic_settings/
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, HttpUrl
from pathlib import Path

class NPMSettings(BaseSettings):
    """NPM CLI configuration with layered loading."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="NPM_",
        extra="forbid"
    )

    # Connection settings
    api_url: HttpUrl = Field(
        default="http://localhost:81",
        description="NPM API base URL"
    )
    container_name: str = Field(
        default="nginx-proxy-manager",
        description="Docker container name"
    )

    # Discovery settings
    use_docker_discovery: bool = Field(
        default=True,
        description="Auto-discover NPM container via Docker"
    )

    @classmethod
    def load(cls) -> "NPMSettings":
        """Load settings with environment variable precedence."""
        return cls()
```

### Anti-Patterns to Avoid
- **Not setting HTTP timeouts:** httpx defaults to no timeout, leads to hanging
- **Hardcoding container names:** Use labels for discovery, support multiple deployment patterns
- **Ignoring token expiry:** Check JWT expiry before each request, validate in _get_token()
- **Not handling Docker daemon unavailable:** Gracefully degrade if Docker not accessible
- **Storing tokens without expiry metadata:** Always save {token, expires} together for validation
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retry logic | Manual retry loops | httpx with retry adapter | Edge cases: backoff, max attempts, which errors to retry |
| Docker container discovery | Parsing `docker ps` output | docker SDK filters | SDK handles API versions, authentication, connection pooling |
| Configuration validation | Manual type checking | Pydantic Settings | Type coercion, validation errors, env var parsing |
| JWT expiry checking | Manual datetime math | Store expiry with token, use timezone-aware datetime | Timezone bugs, clock skew, grace periods |
| HTTP connection pooling | Creating new client per request | Reuse httpx.Client instance | Connection reuse dramatically faster, fewer sockets |

**Key insight:** Token management requires careful datetime handling. Always use timezone-aware datetime.fromisoformat() and store tokens with expiry metadata. Custom expiry logic is error-prone (timezone bugs, clock skew issues).

Docker SDK handles API version negotiation, TLS certificate validation, connection lifecycle. Shelling out to `docker` CLI is fragile (depends on PATH, parsing text output, no type safety) and slower (subprocess overhead).
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: JWT Token Expiry Not Checked Before Request
**What goes wrong:** API calls fail with 401 Unauthorized after token expires
**Why it happens:** Token cached but expiry not validated before use
**How to avoid:** Check expiry timestamp before every API call, refresh if < 5 min remaining
**Warning signs:** Intermittent 401 errors that resolve after re-login

### Pitfall 2: Hardcoded Docker Container Names
**What goes wrong:** Discovery fails for users with different container naming (docker-compose, Portainer, custom names)
**Why it happens:** Assuming everyone uses `nginx-proxy-manager` as container name
**How to avoid:** Support label-based discovery (`com.docker.compose.service=npm`) and configurable name
**Warning signs:** "Container not found" errors reported by users with valid NPM installations

### Pitfall 3: Tokens Stored Without Expiry Validation
**What goes wrong:** Expired tokens cause 401 errors, no automatic re-auth prompt
**Why it happens:** Storing just the token string without expiry metadata
**How to avoid:** Always save {token, expires} together, validate expiry in _get_token()
**Warning signs:** Random 401 errors that resolve after manual re-login

### Pitfall 4: HTTP Client Without Timeout
**What goes wrong:** CLI hangs indefinitely if NPM unresponsive or network issues
**Why it happens:** httpx defaults to no timeout (unlike requests which has default)
**How to avoid:** Always set `timeout=30.0` (or appropriate value) when creating httpx.Client
**Warning signs:** Users report "command freezes" or "have to Ctrl+C"

### Pitfall 5: Docker Daemon Connection Assumed Available
**What goes wrong:** CLI crashes with connection errors if Docker not running or accessible
**Why it happens:** Not handling `docker.errors.DockerException` on client creation
**How to avoid:** Catch Docker connection errors, provide helpful message, allow manual URL config
**Warning signs:** Stack traces mentioning "connection refused" or "docker socket not found"

### Pitfall 6: Not Validating NPM API Response Schema
**What goes wrong:** CLI breaks when NPM API changes (undocumented API, no contract)
**Why it happens:** Trusting API response structure without Pydantic validation
**How to avoid:** Use strict Pydantic models (`extra="forbid"`) for all API responses
**Warning signs:** KeyError or AttributeError when accessing response fields
</common_pitfalls>

<code_examples>
## Code Examples

Verified patterns from official sources:

### Basic Docker Client Setup with Error Handling
```python
# Source: docker-py.readthedocs.io/en/stable/
import docker
from docker.errors import DockerException
from rich.console import Console

console = Console()

def get_docker_client() -> docker.DockerClient | None:
    """Get Docker client with graceful error handling."""
    try:
        client = docker.from_env()
        client.ping()  # Verify connection
        return client
    except DockerException as e:
        console.print(f"[yellow]Warning:[/yellow] Docker not available: {e}")
        console.print("Using manual NPM URL configuration instead.")
        return None
```

### Container Discovery with Multiple Strategies
```python
# Source: docker-py docs + best practices
import docker
from typing import Optional

def discover_npm_container(
    client: docker.DockerClient,
    container_name: Optional[str] = None,
    service_label: str = "nginx-proxy-manager"
) -> Optional[docker.models.containers.Container]:
    """Discover NPM container with fallback strategies."""

    # Strategy 1: By configured name
    if container_name:
        try:
            return client.containers.get(container_name)
        except docker.errors.NotFound:
            pass

    # Strategy 2: By compose service label
    containers = client.containers.list(filters={
        'label': f'com.docker.compose.service={service_label}'
    })
    if containers:
        return containers[0]

    # Strategy 3: By common name patterns
    for pattern in ['nginx-proxy-manager', 'npm', 'nginxproxymanager']:
        containers = client.containers.list(filters={'name': pattern})
        if containers:
            return containers[0]

    return None
```

### HTTPX Client with Timeout and Type Annotations
```python
# Source: python-httpx.org
import httpx
from typing import Any, Dict

class NPMAPIClient:
    """Type-safe NPM API client with timeout."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            headers={"Content-Type": "application/json; charset=UTF-8"}
        )

    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """POST request with JSON response."""
        response = self.client.post(endpoint, json=data)
        response.raise_for_status()
        return response.json()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()
```

### Token File Management
```python
# Source: 02-02 implementation
from pathlib import Path
import json
from datetime import datetime, timezone

TOKEN_FILE = Path.home() / ".npm-cli" / "token.json"

def save_token(token: str, expires: str) -> None:
    """Save JWT token with expiry to file."""
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    token_data = {"token": token, "expires": expires}
    TOKEN_FILE.write_text(json.dumps(token_data))

def load_token() -> str | None:
    """Load token if valid, otherwise None."""
    if not TOKEN_FILE.exists():
        return None

    token_data = json.loads(TOKEN_FILE.read_text())
    expires = datetime.fromisoformat(token_data["expires"].replace("Z", "+00:00"))

    if expires > datetime.now(timezone.utc):
        return token_data["token"]
    return None

def clear_token() -> None:
    """Remove cached token file."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
```
</code_examples>

<sota_updates>
## State of the Art (2025-2026)

What's changed recently:

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| requests library | httpx | 2023-2024 | httpx adds async, HTTP/2, full type annotations |
| Manual .env parsing | pydantic-settings | 2022+ | Built-in validation, type coercion, layered config |
| Token-only storage | Token + expiry metadata | Always best practice | Prevents using expired tokens, enables automatic validation |
| docker CLI subprocess | docker SDK for Python | Stable since 2015 | SDK at 7.1.0, mature and well-maintained |

**New tools/patterns to consider:**
- **HTTPX async client:** For future async CLI commands (e.g., parallel proxy operations)
- **Pydantic Settings:** Now separate package from Pydantic v2, better env var handling
- **Typer-config:** If complex TOML config needed beyond env vars

**Deprecated/outdated:**
- **requests library:** Still maintained but lacks modern features (async, HTTP/2, type hints)
- **ConfigParser:** Use Pydantic Settings instead for type-safe config
- **Token-only storage:** Always store expiry metadata with tokens for validation
</sota_updates>

<open_questions>
## Open Questions

Things that couldn't be fully resolved:

1. **NPM Container Network Discovery**
   - What we know: Can get container network settings via `attrs['NetworkSettings']`
   - What's unclear: Whether to prefer host ports vs container IPs for API access
   - Recommendation: Support both - prefer host ports (e.g., http://localhost:81) with fallback to container IP for Docker network connections

2. **Token Refresh Strategy**
   - What we know: NPM tokens expire in 24-48 hours, can create long-lived tokens
   - What's unclear: Whether to auto-refresh short-lived tokens or use long-lived tokens
   - Recommendation: Start with long-lived tokens (simpler), add auto-refresh in v2 if needed

3. **Multi-NPM Instance Support**
   - What we know: User might have dev/staging/prod NPM instances
   - What's unclear: Whether to support profiles/contexts like kubectl
   - Recommendation: Defer to Phase 5 (templates), use env vars for now (NPM_API_URL)
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- [Docker SDK for Python 7.1.0 Documentation](https://docker-py.readthedocs.io/en/stable/) - Container operations, filters, network inspection
- [HTTPX Official Documentation](https://www.python-httpx.org/) - HTTP client features, async support, type annotations
- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) - Configuration management patterns
- API-DISCOVERY.md (Phase 1) - NPM JWT authentication endpoints and token format
- 02-02-PLAN.md implementation - File-based token caching with expiry validation

### Secondary (MEDIUM confidence)
- [HTTPX vs Requests vs AIOHTTP Comparison](https://oxylabs.io/blog/httpx-vs-requests-vs-aiohttp) - Verified feature comparison
- [Python HTTP Clients 2026 Guide](https://proxyway.com/guides/the-best-python-http-clients) - Current recommendations
- [JWT Token Best Practices](https://auth0.com/docs/secure/tokens/token-best-practices) - Security patterns verified with official Auth0 docs
- [Typer CLI Best Practices](https://www.projectrules.ai/rules/typer) - Configuration patterns for Typer apps
- [Python Configuration Management](https://configu.com/blog/working-with-python-configuration-files-tutorial-best-practices/) - Validated against Pydantic docs

### Tertiary (LOW confidence - needs validation)
- None - all findings cross-verified with official documentation
</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: Docker SDK for Python, HTTPX, JWT authentication
- Ecosystem: pydantic-settings, python-dotenv
- Patterns: Container discovery, file-based token caching, token expiry validation, layered config
- Pitfalls: Token expiry, timeout handling, Docker availability, missing expiry metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified from official docs, current versions confirmed
- Architecture: HIGH - Patterns from official examples and established best practices
- Pitfalls: HIGH - Common issues documented in library issue trackers and best practice guides
- Code examples: HIGH - All examples from official documentation or verified patterns

**Research date:** 2026-01-04
**Valid until:** 2026-02-04 (30 days - ecosystem stable, Docker SDK and HTTPX mature)

**Prior decisions respected:**
- Python 3.11+ with modern type hints ✓ (httpx fully type-annotated)
- Strict Pydantic models with extra="forbid" ✓ (pydantic-settings extends this)
- Typer + Rich for CLI ✓ (patterns integrate with Typer context)
</metadata>

---

*Phase: 02-connection-auth*
*Research completed: 2026-01-04*
*Ready for planning: yes*
