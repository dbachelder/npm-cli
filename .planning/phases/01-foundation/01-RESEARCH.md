# Phase 1: Foundation - Research

**Researched:** 2026-01-04
**Domain:** Nginx Proxy Manager API integration with Python CLI tooling
**Confidence:** MEDIUM-HIGH

<research_summary>
## Summary

Researched the Nginx Proxy Manager (NPM) API ecosystem and modern Python CLI development tooling for building a comprehensive CLI tool. The key finding is that NPM has a fully functional but **completely undocumented** REST API - there is no official API documentation, and the Swagger schema is incomplete. The community has reverse-engineered API endpoints through source code inspection, browser network analysis, and the built-in Audit Log feature.

For Python CLI tooling, the modern stack consists of uv for project management (replacing pip, poetry, pyenv), Typer for CLI framework (modern type-hint based approach built on Click), httpx for HTTP client (async support + HTTP/2), pydantic-settings for configuration management, and Rich for beautiful terminal output.

**Primary recommendation:** Use source code and Audit Log inspection to discover NPM API endpoints during implementation. Build with uv + Typer + httpx + pydantic-settings + Rich stack. Plan for API discovery as an ongoing activity rather than upfront documentation reading.
</research_summary>

<standard_stack>
## Standard Stack

The established libraries/tools for Python CLI development with API integration:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| uv | 0.5+ | Project & dependency management | 10-100x faster than pip, replaces pip/poetry/pyenv/virtualenv |
| Typer | 0.12+ | CLI framework | Modern type-hint driven, built on Click, auto-generates help |
| httpx | 0.27+ | HTTP client | Async support, HTTP/2, requests-compatible API |
| pydantic | 2.x | Data validation | Type-safe models, runtime validation |
| pydantic-settings | 2.x | Configuration management | TOML/env/multiple sources, type-safe config |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Rich | 13.x+ | Terminal formatting | Progress bars, spinners, tables, syntax highlighting |
| pytest | 8.x+ | Testing framework | Standard Python testing |
| ruff | 0.7+ | Linting & formatting | Fast Rust-based linter/formatter replacing black+flake8 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Typer | Click | Click requires more boilerplate but is more mature |
| Typer | argparse | argparse is stdlib but verbose and lacks modern features |
| httpx | requests | requests is simpler but no async/HTTP/2 support |
| httpx | aiohttp | aiohttp async-only, httpx supports both sync/async |
| uv | poetry | poetry slower but more mature, larger ecosystem |
| pydantic-settings | dynaconf | dynaconf more flexible but less type-safe |

**Installation:**
```bash
# Initialize project with uv
uv init --package npm-cli
cd npm-cli

# Add dependencies
uv add typer httpx pydantic pydantic-settings rich
uv add --dev pytest ruff
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Project Structure
```
npm-cli/
├── src/
│   └── npm_cli/
│       ├── __init__.py
│       ├── __main__.py      # Entry point
│       ├── cli/             # CLI commands
│       │   ├── __init__.py
│       │   ├── proxy.py     # Proxy host commands
│       │   ├── cert.py      # Certificate commands
│       │   └── config.py    # Configuration commands
│       ├── api/             # NPM API client
│       │   ├── __init__.py
│       │   ├── client.py    # Base HTTP client
│       │   ├── auth.py      # Authentication
│       │   ├── models.py    # Pydantic models
│       │   └── endpoints/   # Endpoint-specific logic
│       │       ├── proxy_hosts.py
│       │       ├── certificates.py
│       │       └── users.py
│       ├── config/          # Configuration management
│       │   ├── __init__.py
│       │   ├── settings.py  # Pydantic settings
│       │   └── discovery.py # Docker container discovery
│       └── utils/           # Shared utilities
│           ├── __init__.py
│           └── output.py    # Rich formatting helpers
├── tests/
│   ├── test_api/
│   ├── test_cli/
│   └── conftest.py
├── pyproject.toml
├── uv.lock
└── README.md
```

### Pattern 1: Typer CLI with Type Hints
**What:** Use Python type hints to define CLI arguments and options
**When to use:** All CLI command definitions
**Example:**
```python
# src/npm_cli/cli/proxy.py
import typer
from typing import Annotated

app = typer.Typer(help="Manage proxy hosts")

@app.command()
def create(
    domain: Annotated[str, typer.Argument(help="Domain name for proxy host")],
    forward_host: Annotated[str, typer.Option("--host", help="Upstream host")],
    forward_port: Annotated[int, typer.Option("--port", help="Upstream port")] = 80,
    ssl: Annotated[bool, typer.Option("--ssl", help="Enable SSL")] = False,
):
    """Create a new proxy host."""
    typer.echo(f"Creating proxy host for {domain}...")
```

### Pattern 2: Async HTTP Client with Context Manager
**What:** Use httpx.AsyncClient with context manager for connection pooling
**When to use:** All API interactions
**Example:**
```python
# src/npm_cli/api/client.py
import httpx
from typing import Any

class NPMClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    async def get(self, path: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{path}",
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
```

### Pattern 3: Pydantic Settings with Multiple Sources
**What:** Use pydantic-settings to load config from TOML, env vars, and discovery
**When to use:** Application configuration
**Example:**
```python
# src/npm_cli/config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        toml_file="npm-cli.toml",
        env_prefix="NPM_",
        case_sensitive=False
    )

    npm_url: Optional[str] = None
    npm_email: Optional[str] = None
    npm_password: Optional[str] = None
    token: Optional[str] = None

    # Auto-discovered via Docker API
    container_name: Optional[str] = "nginx-proxy-manager"
```

### Pattern 4: Rich Progress Feedback
**What:** Use Rich for progress indicators and formatted output
**When to use:** Long-running operations and formatted data display
**Example:**
```python
# src/npm_cli/utils/output.py
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def show_proxy_hosts(hosts: list[dict]):
    table = Table(title="Proxy Hosts")
    table.add_column("ID", style="cyan")
    table.add_column("Domain", style="green")
    table.add_column("Forward", style="yellow")

    for host in hosts:
        table.add_row(
            str(host["id"]),
            host["domain_names"][0],
            f"{host['forward_host']}:{host['forward_port']}"
        )

    console.print(table)

def with_spinner(message: str):
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}")
    )
```

### Anti-Patterns to Avoid
- **Synchronous HTTP in async context:** Don't mix requests and asyncio - use httpx for both sync/async
- **Hardcoded API endpoints:** Don't hardcode URLs - discover via Docker or config files
- **String-based CLI args:** Don't use raw sys.argv - use Typer with type hints
- **Manual JSON parsing:** Don't use dict for API responses - use Pydantic models for validation
- **print() for output:** Don't use print() - use Rich console for consistent formatting
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI argument parsing | Manual sys.argv parsing | Typer | Type safety, auto-help, validation, subcommands |
| HTTP requests | urllib/socket code | httpx | Connection pooling, retries, timeouts, async support |
| Configuration loading | Custom config parser | pydantic-settings | Multiple sources (TOML/env/files), validation, type safety |
| Terminal formatting | ANSI escape codes | Rich | Cross-platform, tables, progress, syntax highlighting |
| Data validation | Manual type checks | Pydantic | Runtime validation, serialization, JSON schema |
| JWT token parsing | Manual base64 decode | python-jose or PyJWT | Signature verification, expiry handling, edge cases |
| Docker API interaction | subprocess + docker CLI | docker-py or httpx to socket | Type-safe, connection handling, error handling |
| Progress indicators | Custom spinner/progress | Rich Progress | Smooth animations, multiple tasks, time estimation |

**Key insight:** Modern Python CLI development has mature libraries for every common need. The NPM API being undocumented means focus should be on clean abstraction layers (Pydantic models, httpx client) rather than fighting with low-level HTTP/JSON/validation code.
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Assuming NPM API is Documented
**What goes wrong:** Spending time searching for API docs that don't exist
**Why it happens:** Most APIs have documentation, NPM's API is an exception
**How to avoid:** Use source code inspection (github.com/NginxProxyManager/nginx-proxy-manager/tree/develop/backend/routes/api), Audit Log in web UI, and browser DevTools to discover endpoints
**Warning signs:** Swagger schema exists but is incomplete, community discussions mention "no API docs"

### Pitfall 2: Token Expiration Not Handled
**What goes wrong:** CLI works initially then fails with 401 errors
**Why it happens:** NPM tokens auto-expire after 24-48 hours unless expiry is explicitly set
**How to avoid:** Implement token refresh flow, store token with expiry timestamp, or create long-lived tokens (up to 999 years tested) during authentication
**Warning signs:** Intermittent authentication failures, works after re-login

### Pitfall 3: Using requests Instead of httpx
**What goes wrong:** Can't implement async operations efficiently
**Why it happens:** requests is familiar and widely used
**How to avoid:** Start with httpx from the beginning - same API as requests but with async support and HTTP/2
**Warning signs:** Need for async leads to rewriting HTTP client code, or concurrent operations are slow

### Pitfall 4: Not Using Rich with Typer
**What goes wrong:** Poor user experience with plain text output
**Why it happens:** Not knowing Rich integrates seamlessly with Typer
**How to avoid:** Import Rich console and use it for all output - Typer automatically uses Rich for errors and help when installed
**Warning signs:** Users complain about hard-to-read output, no visual feedback during long operations

### Pitfall 5: Mixing Sync and Async Code Incorrectly
**What goes wrong:** Runtime errors or blocking behavior in async functions
**Why it happens:** Using sync httpx client in async context or vice versa
**How to avoid:** Be consistent - either all sync or all async. httpx supports both, but don't mix in the same code path
**Warning signs:** "coroutine never awaited" warnings, async functions blocking

### Pitfall 6: Ignoring CORS Token Vulnerability (CVE-2025-50579)
**What goes wrong:** Security risk when interacting with NPM API
**Why it happens:** NPM v2.12.3 and earlier have CORS misconfiguration allowing token theft
**How to avoid:** Warn users about NPM version, implement secure token storage, don't expose tokens in logs/URLs
**Warning signs:** Tokens leaked in error messages, stored in plain text, passed in query strings

### Pitfall 7: Not Validating API Responses
**What goes wrong:** Runtime errors when API returns unexpected data
**Why it happens:** Trusting undocumented API to always return consistent structure
**How to avoid:** Use Pydantic models for all API responses - catches schema changes early
**Warning signs:** KeyError exceptions, unexpected None values, type errors
</common_pitfalls>

<code_examples>
## Code Examples

Verified patterns from official sources and best practices:

### NPM Authentication Flow
```python
# Source: GitHub Discussion #3265
import httpx
from pydantic import BaseModel

class TokenRequest(BaseModel):
    identity: str  # email
    secret: str    # password

class TokenResponse(BaseModel):
    token: str
    expires: str

async def authenticate(base_url: str, email: str, password: str) -> str:
    """Authenticate with NPM and return Bearer token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/api/tokens",
            json={"identity": email, "secret": password},
            headers={"Content-Type": "application/json; charset=UTF-8"}
        )
        response.raise_for_status()
        data = TokenResponse(**response.json())
        return data.token
```

### Typer CLI with Rich Progress
```python
# Source: Typer + Rich official docs
import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer()

@app.command()
def sync():
    """Synchronize proxy hosts from config."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        task = progress.add_task("Syncing proxy hosts...", total=None)
        # Perform sync operation
        progress.update(task, description="✓ Sync complete")
```

### Pydantic Settings with TOML
```python
# Source: pydantic-settings documentation
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        toml_file="npm-cli.toml",
        env_prefix="NPM_",
        env_file=".env",
        env_file_encoding="utf-8"
    )

    npm_url: str = "http://localhost:81"
    npm_email: str
    npm_password: str

    @classmethod
    def from_files(cls) -> "Settings":
        """Load settings from TOML file or env vars."""
        return cls()
```

### API Client with Error Handling
```python
# Source: httpx + Typer best practices
import httpx
import typer
from typing import Any

class NPMAPIError(Exception):
    """NPM API error."""
    pass

async def api_request(
    method: str,
    url: str,
    token: str,
    **kwargs: Any
) -> dict[str, Any]:
    """Make authenticated API request with error handling."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise NPMAPIError("Authentication failed - token may be expired")
        elif e.response.status_code == 404:
            raise NPMAPIError(f"Resource not found: {url}")
        else:
            raise NPMAPIError(f"API error: {e.response.status_code}")
    except httpx.RequestError as e:
        raise NPMAPIError(f"Connection error: {e}")
```

### Docker Container Discovery
```python
# Source: Community pattern for NPM discovery
import httpx
from typing import Optional

async def discover_npm_container() -> Optional[str]:
    """
    Discover NPM container via Docker socket.
    Returns base URL if found.
    """
    socket_path = "/var/run/docker.sock"

    try:
        transport = httpx.AsyncHTTPTransport(uds=socket_path)
        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get(
                "http://docker/containers/json",
                params={"filters": '{"name":["nginx-proxy-manager"]}'}
            )
            containers = response.json()

            if containers:
                # Extract port mapping from first container
                container = containers[0]
                ports = container.get("Ports", [])
                for port in ports:
                    if port.get("PrivatePort") == 81:  # NPM admin port
                        public_port = port.get("PublicPort", 81)
                        return f"http://localhost:{public_port}"
    except Exception:
        return None
```

### Proxy Host Creation
```python
# Source: Reverse-engineered from NPM source + community
from pydantic import BaseModel, Field
from typing import Optional

class ProxyHostCreate(BaseModel):
    domain_names: list[str]
    forward_host: str
    forward_port: int
    forward_scheme: str = "http"  # or "https"
    access_list_id: int = 0
    certificate_id: int = 0
    ssl_forced: bool = False
    caching_enabled: bool = False
    block_exploits: bool = True
    allow_websocket_upgrade: bool = True
    http2_support: bool = False
    hsts_enabled: bool = False
    hsts_subdomains: bool = False
    advanced_config: str = ""
    locations: list = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)

async def create_proxy_host(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    host: ProxyHostCreate
) -> dict:
    """Create new proxy host via NPM API."""
    response = await client.post(
        f"{base_url}/api/nginx/proxy-hosts",
        json=host.model_dump(mode="json"),
        headers={"Authorization": f"Bearer {token}"}
    )
    response.raise_for_status()
    return response.json()
```
</code_examples>

<sota_updates>
## State of the Art (2025-2026)

What's changed recently:

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pip + virtualenv | uv | 2024-2025 | uv is 10-100x faster, single tool for all package management |
| Click | Typer | 2020+ | Type hints replace decorators, better DX with autocompletion |
| requests | httpx | 2021+ | Async support + HTTP/2, same familiar API |
| poetry | uv | 2024-2025 | uv faster and simpler, poetry still viable but slower |
| ConfigParser/JSON | pydantic-settings | 2023+ | Type-safe config with multiple sources (TOML/env/files) |

**New tools/patterns to consider:**
- **uv as complete toolchain:** Replaces pip, pip-tools, pipx, poetry, pyenv, virtualenv in single Rust-based tool
- **Ruff for linting:** Replaces black + flake8 + isort with 100x faster Rust-based tool
- **Rich for terminal UI:** Standard for modern CLI output, integrates with Typer automatically
- **Pydantic v2:** Major performance improvements (up to 50x faster), better error messages

**Deprecated/outdated:**
- **setuptools/setup.py:** Use pyproject.toml with uv or poetry instead
- **requirements.txt:** Use uv.lock or poetry.lock for reproducible installs
- **argparse for new projects:** Use Typer for better DX (argparse still fine for simple scripts)
- **requests for async:** Use httpx to avoid maintaining two HTTP clients
</sota_updates>

<open_questions>
## Open Questions

Things that couldn't be fully resolved:

1. **NPM API Versioning**
   - What we know: NPM API exists but is undocumented, recent version is v2.12.4+
   - What's unclear: Whether API endpoints/schemas change between NPM versions, if there's API versioning
   - Recommendation: Implement API discovery during development, use Pydantic validation to catch schema changes, test against specific NPM version and document it

2. **Optimal Token Management**
   - What we know: Tokens expire in 24-48 hours by default, can set custom expiry up to 999 years
   - What's unclear: Best practice for CLI token storage (keyring vs config file), whether to auto-refresh or use long-lived tokens
   - Recommendation: Offer both options - short-lived with auto-refresh for security-conscious users, long-lived for convenience. Use keyring for token storage where available.

3. **Docker Discovery Reliability**
   - What we know: Can discover NPM container via Docker socket API
   - What's unclear: Edge cases (multiple NPM containers, non-standard ports, remote Docker hosts, rootless Docker)
   - Recommendation: Implement discovery as convenience feature with manual configuration fallback, document requirements clearly

4. **NPM API Rate Limiting**
   - What we know: API exists and handles requests
   - What's unclear: Whether NPM implements rate limiting, connection limits, or request throttling
   - Recommendation: Implement respectful defaults (connection pooling, reasonable timeouts), monitor for 429 responses during testing

5. **Advanced Config Validation**
   - What we know: Proxy hosts accept `advanced_config` field for custom Nginx config
   - What's unclear: Validation rules, allowed directives, security restrictions on custom config
   - Recommendation: Treat as opaque string initially, add validation if NPM API returns errors for specific patterns
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- [uv documentation](https://docs.astral.sh/uv/) - Official uv project management docs
- [Typer documentation](https://typer.tiangolo.com/) - Official Typer CLI framework docs
- [httpx documentation](https://www.python-httpx.org/) - Official httpx HTTP client docs
- [pydantic-settings documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) - Official pydantic-settings docs
- [Rich documentation](https://rich.readthedocs.io/) - Official Rich terminal formatting docs

### Secondary (MEDIUM confidence)
- [NPM GitHub Discussion #3265](https://github.com/NginxProxyManager/nginx-proxy-manager/discussions/3265) - Community reverse-engineering of NPM API
- [NPM GitHub Discussion #3527](https://github.com/NginxProxyManager/nginx-proxy-manager/discussions/3527) - API documentation requests and community solutions
- [NPM API Issue #1790](https://github.com/NginxProxyManager/nginx-proxy-manager/issues/1790) - API access discussion
- [Real Python - Managing Python Projects With uv](https://realpython.com/python-uv/) - Comprehensive uv guide
- [Typer vs Click comparison](https://medium.com/@mohd_nass/navigating-the-cli-landscape-in-python-a-comparative-study-of-argparse-click-and-typer-480ebbb7172f) - CLI framework comparison

### Tertiary (LOW confidence - needs validation during implementation)
- NPM backend source code structure (routes/api, schema) - mentioned in discussions but not directly verified
- Token expiry of 999 years - community reported but not officially documented
- Specific API endpoint schemas - will need runtime validation via Pydantic

### Security Advisory
- [CVE-2025-50579](https://github.com/NginxProxyManager/nginx-proxy-manager/issues/4509) - CORS token theft vulnerability in NPM v2.12.3
</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: Nginx Proxy Manager API (undocumented REST API)
- Ecosystem: Python CLI development stack (uv, Typer, httpx, pydantic, Rich)
- Patterns: API client architecture, CLI command structure, config management, error handling
- Pitfalls: Undocumented API discovery, token management, async HTTP patterns

**Confidence breakdown:**
- Standard stack: HIGH - well-documented, widely adopted, verified via official sources
- Architecture: HIGH - patterns from official docs and established best practices
- Pitfalls: MEDIUM-HIGH - NPM API pitfalls from community experience, Python pitfalls from docs
- Code examples: HIGH - based on official documentation and verified community patterns
- NPM API specifics: MEDIUM - undocumented API, relying on community reverse-engineering

**Research date:** 2026-01-04
**Valid until:** 2026-02-04 (30 days - Python tooling stable, NPM API changes unknown)

**Key unknown:** NPM API schema and stability - ongoing discovery required during implementation
</metadata>

---

*Phase: 01-foundation*
*Research completed: 2026-01-04*
*Ready for planning: yes*
