# Phase 3: Proxy Host Management - Research

**Researched:** 2026-01-04
**Domain:** Nginx Proxy Manager API (undocumented REST API)
**Confidence:** MEDIUM

<research_summary>
## Summary

Researched the Nginx Proxy Manager API for implementing proxy host CRUD operations. The NPM API is completely undocumented - there is no official API documentation, and the Swagger schema is incomplete and contains errors. The API must be reverse-engineered through source code inspection, browser DevTools, the Audit Log feature, and community implementations.

Key finding: The standard approach for undocumented APIs is strict Pydantic validation with `extra="forbid"` to catch schema changes early, combined with httpx for modern HTTP client features (connection pooling, timeout enforcement, HTTP/2). Community wrappers exist but use older patterns (requests library, loose validation).

**Primary recommendation:** Use httpx Client with connection pooling, Pydantic strict models for all endpoints, comprehensive error handling with Rich-formatted output, and defensive validation to detect NPM API changes immediately.
</research_summary>

<standard_stack>
## Standard Stack

The established libraries/tools for Python REST API clients with undocumented APIs:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28+ | HTTP client with sync/async support | Modern replacement for requests, connection pooling, enforced timeouts, HTTP/2 support |
| pydantic | 2.10+ | Request/response validation | Runtime type safety, 5-50x faster than v1, catches schema changes with `extra="forbid"` |
| typer | 0.15+ | CLI framework | Type-safe CLI with subcommands, integrates with Rich for beautiful output |
| rich | 14.1+ | Console formatting | Beautiful tables, error messages, progress bars - default in Typer |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | 9.0+ | Retry with exponential backoff | Network errors, transient failures (not 404/401) |
| python-dotenv | 1.0+ | Environment variable loading | Configuration management (already in project) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | requests | requests is stable but lacks async, HTTP/2, and enforced timeouts |
| Pydantic v2 | dataclasses | dataclasses lack runtime validation and schema evolution detection |
| Rich | click echo | click's basic output vs Rich's tables/formatting/colors |

**Installation:**
```bash
# Already in project via uv
uv add httpx pydantic typer[all]  # typer[all] includes rich
uv add tenacity  # For retry logic
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Project Structure
```
src/npm_cli/
├── api/
│   ├── client.py           # NPM API client with httpx
│   ├── models.py           # Pydantic models (already exists)
│   └── exceptions.py       # Custom exceptions for API errors
├── cli/
│   ├── proxy.py            # Proxy host commands (create, list, update, delete)
│   └── ...
└── __main__.py             # Typer app setup
```

### Pattern 1: httpx Client with Connection Pooling
**What:** Reuse httpx.Client instance across requests for connection pooling
**When to use:** All NPM API operations
**Example:**
```python
# Source: https://www.python-httpx.org/advanced/clients/
import httpx

class NPMClient:
    def __init__(self, base_url: str, token: str):
        self.client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,  # Prevent CLI hangs (per project decision)
            http2=True     # Enable HTTP/2 if NPM supports it
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    def get_proxy_hosts(self) -> list[ProxyHost]:
        response = self.client.get("/api/nginx/proxy-hosts")
        response.raise_for_status()
        # Validate with Pydantic
        return [ProxyHost.model_validate(item) for item in response.json()]
```

### Pattern 2: Pydantic Strict Validation for Undocumented APIs
**What:** Use `extra="forbid"` to detect unexpected fields from API changes
**When to use:** All request/response models for undocumented NPM API
**Example:**
```python
# Source: Project decision + https://docs.pydantic.dev/latest/
from pydantic import BaseModel, Field, ConfigDict

class ProxyHost(BaseModel):
    model_config = ConfigDict(extra="forbid")  # Fail on unknown fields

    id: int = Field(ge=1, description="Proxy host ID")
    domain_names: list[str] = Field(max_length=15, description="Max 15 domains")
    forward_scheme: Literal["http", "https"]
    forward_host: str = Field(min_length=1, max_length=255)
    forward_port: int = Field(ge=1, le=65535)
    certificate_id: int | Literal["new"] = 0
    ssl_forced: bool = False
    enabled: bool = True
    # ... all fields from schema
```

### Pattern 3: Rich Console Error Formatting
**What:** Use Rich console for formatted error messages with context
**When to use:** All CLI error output (network failures, validation errors, API errors)
**Example:**
```python
# Source: https://rich.readthedocs.io/en/stable/console.html
from rich.console import Console
from rich.table import Table

console = Console()

try:
    proxy_hosts = npm_client.get_proxy_hosts()
except httpx.HTTPStatusError as e:
    console.print(f"[bold red]Error:[/] NPM API returned {e.response.status_code}")
    console.print(f"[dim]Response:[/] {e.response.text[:200]}")
    raise typer.Exit(1)
except ValidationError as e:
    console.print("[bold red]Error:[/] NPM API response schema changed!")
    console.print(f"[dim]Validation errors:[/]\n{e}")
    raise typer.Exit(1)

# Display as table
table = Table(title="Proxy Hosts")
table.add_column("ID", style="cyan")
table.add_column("Domains", style="green")
table.add_column("Forward", style="yellow")

for host in proxy_hosts:
    domains = ", ".join(host.domain_names)
    forward = f"{host.forward_scheme}://{host.forward_host}:{host.forward_port}"
    table.add_row(str(host.id), domains, forward)

console.print(table)
```

### Pattern 4: Retry with Exponential Backoff (Selective)
**What:** Retry transient failures (timeouts, 503) but not permanent errors (404, 401)
**When to use:** Network operations that may have transient failures
**Example:**
```python
# Source: https://oxylabs.io/blog/python-requests-retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.ConnectTimeout)),
    reraise=True
)
def create_proxy_host(self, host_data: ProxyHostCreate) -> ProxyHost:
    response = self.client.post(
        "/api/nginx/proxy-hosts",
        json=host_data.model_dump(exclude_none=True)
    )
    response.raise_for_status()
    return ProxyHost.model_validate(response.json())
```

### Anti-Patterns to Avoid
- **Not using Client instances:** Individual httpx requests create new connections each time (slow)
- **Loose Pydantic validation:** `extra="allow"` hides NPM API schema changes until runtime bugs
- **Generic error messages:** Users need context (status code, response snippet) to debug
- **Retrying authentication failures:** 401 means bad token, not transient failure
- **Print instead of Rich console:** Loses formatting, colors, and structured output
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retry logic | Custom retry loops with sleep() | tenacity library | Handles exponential backoff, jitter, selective retry, max attempts |
| Connection pooling | Manual socket reuse | httpx.Client | Built-in connection pooling, timeout management, HTTP/2 |
| JSON validation | Manual dict key checks | Pydantic models | Runtime type checking, automatic serialization, schema evolution detection |
| CLI tables/formatting | Manual string formatting | Rich library | Handles terminal width, colors, borders, alignment automatically |
| Timeout enforcement | Manual threading.Timer | httpx timeout parameter | Built-in, tested, handles edge cases (connect vs read timeouts) |
| API error context | Generic "Request failed" | httpx.HTTPStatusError with Rich | Preserves status code, response body, request details |

**Key insight:** Undocumented APIs require defensive programming. Pydantic's `extra="forbid"` catches schema changes immediately (validation error) rather than silently accepting new fields that might break assumptions. httpx enforces timeouts by default (5s) preventing CLI hangs that requests allows.
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: NPM API Schema Changes (Undocumented API)
**What goes wrong:** NPM update adds/removes/renames fields, breaking the CLI
**Why it happens:** No API contract, no versioning, schema changes without notice
**How to avoid:**
- Use Pydantic `extra="forbid"` to fail fast on unknown fields
- Comprehensive error messages showing raw API response
- Version detection (check NPM version, warn if unknown)
**Warning signs:**
- Validation errors after NPM upgrade
- Fields missing that were previously present
- New required fields not in our models

### Pitfall 2: Missing Timeout Causes CLI Hang
**What goes wrong:** NPM container is down, CLI hangs indefinitely waiting for response
**Why it happens:** httpx default is NO timeout for `response.read()`
**How to avoid:**
- Always set `timeout=30.0` (or appropriate value) in httpx.Client
- Project decision already established 30s timeout
- Test with stopped NPM container to verify timeout works
**Warning signs:**
- User reports CLI "freezes"
- No error message, just waiting forever
- Ctrl+C required to exit

### Pitfall 3: Connection Pool Exhaustion
**What goes wrong:** CLI creates hundreds of httpx.Client instances, exhausts ports
**Why it happens:** Creating client per request instead of reusing
**How to avoid:**
- Single httpx.Client instance in NPMClient class
- Use context manager (__enter__/__exit__) to ensure cleanup
- Close client explicitly in CLI teardown
**Warning signs:**
- "Too many open files" errors
- Slow performance on repeated commands
- Port exhaustion in `netstat`

### Pitfall 4: Retrying Non-Transient Failures
**What goes wrong:** 401 Unauthorized retried 3 times, wasting 15+ seconds
**Why it happens:** Retry logic doesn't distinguish permanent vs transient errors
**How to avoid:**
- Only retry ConnectError, ConnectTimeout, 503 Service Unavailable
- Never retry 401, 403, 404, 400 (client errors)
- Use tenacity's `retry_if_exception_type` to be selective
**Warning signs:**
- Slow error responses for bad credentials
- Retry logs showing repeated 404s
- Users confused why CLI is slow to fail

### Pitfall 5: Audit Log as Documentation Trap
**What goes wrong:** Audit log shows requests but omits optional fields, leading to incomplete models
**Why it happens:** Audit log only shows fields user set, not all possible fields
**How to avoid:**
- Use backend schema files as source of truth (GitHub repo)
- Cross-reference community implementations
- Test edge cases (websocket, caching, custom config)
**Warning signs:**
- Features exist in NPM UI but not in CLI
- "Unknown field" errors when NPM returns optional fields
- Community reports fields we don't support
</common_pitfalls>

<code_examples>
## Code Examples

Verified patterns from official sources and project decisions:

### NPM API Client Structure
```python
# Source: Project architecture + httpx best practices
# File: src/npm_cli/api/client.py

import httpx
from pydantic import ValidationError
from .models import ProxyHost, ProxyHostCreate, ProxyHostUpdate
from .exceptions import NPMAPIError, NPMConnectionError, NPMValidationError

class NPMClient:
    """Client for Nginx Proxy Manager API"""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,  # Project decision: prevent hangs
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    def list_proxy_hosts(self) -> list[ProxyHost]:
        """GET /api/nginx/proxy-hosts"""
        try:
            response = self.client.get("/api/nginx/proxy-hosts")
            response.raise_for_status()
            data = response.json()
            return [ProxyHost.model_validate(item) for item in data]
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
        except httpx.ConnectError as e:
            raise NPMConnectionError(f"Cannot connect to NPM at {self.base_url}")

    def get_proxy_host(self, host_id: int) -> ProxyHost:
        """GET /api/nginx/proxy-hosts/{id}"""
        try:
            response = self.client.get(f"/api/nginx/proxy-hosts/{host_id}")
            response.raise_for_status()
            return ProxyHost.model_validate(response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise NPMAPIError(f"Proxy host {host_id} not found")
            raise NPMAPIError(
                f"Failed to get proxy host: {e.response.status_code}",
                response=e.response
            )

    def create_proxy_host(self, host: ProxyHostCreate) -> ProxyHost:
        """POST /api/nginx/proxy-hosts"""
        try:
            response = self.client.post(
                "/api/nginx/proxy-hosts",
                json=host.model_dump(exclude_none=True, mode="json")
            )
            response.raise_for_status()
            return ProxyHost.model_validate(response.json())
        except httpx.HTTPStatusError as e:
            raise NPMAPIError(
                f"Failed to create proxy host: {e.response.status_code}",
                response=e.response
            )

    def update_proxy_host(self, host_id: int, updates: ProxyHostUpdate) -> ProxyHost:
        """PUT /api/nginx/proxy-hosts/{id}"""
        try:
            response = self.client.put(
                f"/api/nginx/proxy-hosts/{host_id}",
                json=updates.model_dump(exclude_none=True, mode="json")
            )
            response.raise_for_status()
            return ProxyHost.model_validate(response.json())
        except httpx.HTTPStatusError as e:
            raise NPMAPIError(
                f"Failed to update proxy host: {e.response.status_code}",
                response=e.response
            )

    def delete_proxy_host(self, host_id: int) -> None:
        """DELETE /api/nginx/proxy-hosts/{id}"""
        try:
            response = self.client.delete(f"/api/nginx/proxy-hosts/{host_id}")
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise NPMAPIError(f"Proxy host {host_id} not found")
            raise NPMAPIError(
                f"Failed to delete proxy host: {e.response.status_code}",
                response=e.response
            )
```

### Proxy Host Pydantic Models
```python
# Source: NPM JSON Schema (v2.9.6) + project decisions
# File: src/npm_cli/api/models.py

from pydantic import BaseModel, Field, ConfigDict
from typing import Literal

class ProxyHostCreate(BaseModel):
    """Request model for creating proxy host"""
    model_config = ConfigDict(extra="forbid")

    # Required fields
    domain_names: list[str] = Field(
        min_length=1,
        max_length=15,
        description="List of domain names (max 15)"
    )
    forward_scheme: Literal["http", "https"] = Field(
        description="Backend protocol"
    )
    forward_host: str = Field(
        min_length=1,
        max_length=255,
        description="Backend hostname or IP"
    )
    forward_port: int = Field(
        ge=1,
        le=65535,
        description="Backend port"
    )

    # Optional fields
    certificate_id: int | Literal["new"] = Field(
        default=0,
        description="Certificate ID or 'new' to create"
    )
    ssl_forced: bool = Field(
        default=False,
        description="Force SSL redirect"
    )
    hsts_enabled: bool = False
    hsts_subdomains: bool = False
    http2_support: bool = True
    block_exploits: bool = True
    caching_enabled: bool = False
    allow_websocket_upgrade: bool = False
    access_list_id: int = Field(default=0, ge=0)
    advanced_config: str = ""
    enabled: bool = True
    meta: dict = Field(default_factory=dict)
    locations: list[dict] = Field(default_factory=list)


class ProxyHost(ProxyHostCreate):
    """Response model for proxy host (includes read-only fields)"""

    id: int = Field(ge=1, description="Proxy host ID")
    created_on: str = Field(description="ISO 8601 datetime")
    modified_on: str = Field(description="ISO 8601 datetime")
    owner_user_id: int = Field(ge=1)


class ProxyHostUpdate(BaseModel):
    """Request model for updating proxy host (all fields optional)"""
    model_config = ConfigDict(extra="forbid")

    domain_names: list[str] | None = None
    forward_scheme: Literal["http", "https"] | None = None
    forward_host: str | None = None
    forward_port: int | None = None
    certificate_id: int | Literal["new"] | None = None
    ssl_forced: bool | None = None
    enabled: bool | None = None
    # ... all other fields as optional
```

### CLI Commands with Rich Output
```python
# Source: Typer + Rich integration patterns
# File: src/npm_cli/cli/proxy.py

import typer
from rich.console import Console
from rich.table import Table
from ..api.client import NPMClient
from ..api.models import ProxyHostCreate
from ..api.exceptions import NPMAPIError, NPMConnectionError

app = typer.Typer(name="proxy", help="Manage proxy hosts")
console = Console()

@app.command("list")
def list_proxy_hosts():
    """List all proxy hosts"""
    try:
        # Get client from settings (already implemented in phase 2)
        with NPMClient(settings.npm_url, settings.token) as client:
            hosts = client.list_proxy_hosts()

        if not hosts:
            console.print("[yellow]No proxy hosts found[/]")
            return

        # Create Rich table
        table = Table(title="Proxy Hosts", show_lines=True)
        table.add_column("ID", style="cyan", width=6)
        table.add_column("Domains", style="green")
        table.add_column("Forward To", style="yellow")
        table.add_column("SSL", style="magenta", width=8)
        table.add_column("Status", style="blue", width=10)

        for host in hosts:
            domains = "\n".join(host.domain_names)
            forward = f"{host.forward_scheme}://{host.forward_host}:{host.forward_port}"
            ssl = "✓" if host.certificate_id else "✗"
            status = "[green]Enabled[/]" if host.enabled else "[red]Disabled[/]"

            table.add_row(str(host.id), domains, forward, ssl, status)

        console.print(table)

    except NPMConnectionError as e:
        console.print(f"[bold red]Connection Error:[/] {e}")
        console.print("[dim]Is the NPM container running?[/]")
        raise typer.Exit(1)
    except NPMAPIError as e:
        console.print(f"[bold red]API Error:[/] {e}")
        if e.response:
            console.print(f"[dim]Status:[/] {e.response.status_code}")
            console.print(f"[dim]Response:[/] {e.response.text[:200]}")
        raise typer.Exit(1)


@app.command("create")
def create_proxy_host(
    domain: str = typer.Argument(..., help="Domain name (e.g., app.example.com)"),
    forward_host: str = typer.Option(..., "--host", help="Backend hostname/IP"),
    forward_port: int = typer.Option(..., "--port", help="Backend port"),
    forward_scheme: Literal["http", "https"] = typer.Option("http", "--scheme"),
    ssl: bool = typer.Option(False, "--ssl", help="Enable SSL"),
):
    """Create a new proxy host"""
    try:
        host_data = ProxyHostCreate(
            domain_names=[domain],
            forward_host=forward_host,
            forward_port=forward_port,
            forward_scheme=forward_scheme,
            ssl_forced=ssl,
        )

        with NPMClient(settings.npm_url, settings.token) as client:
            created = client.create_proxy_host(host_data)

        console.print(f"[green]✓[/] Created proxy host [cyan]{created.id}[/]")
        console.print(f"  Domain: {domain}")
        console.print(f"  Forward: {forward_scheme}://{forward_host}:{forward_port}")

    except NPMAPIError as e:
        console.print(f"[bold red]Failed to create proxy host:[/] {e}")
        raise typer.Exit(1)
```
</code_examples>

<sota_updates>
## State of the Art (2024-2025)

What's changed recently in Python HTTP client and CLI development:

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| requests library | httpx | 2020+ | httpx adds async support, HTTP/2, enforced timeouts, better for modern APIs |
| Pydantic v1 | Pydantic v2 | 2023 | 5-50x performance improvement, better error messages, Rust-powered core |
| Manual CLI formatting | Rich library | 2020+ | Standardized beautiful terminal output, tables, progress bars, tracebacks |
| click for CLI | Typer | 2019+ | Type hints instead of decorators, automatic validation, Rich integration |
| Global requests.Session | httpx.Client context manager | 2021+ | Better resource cleanup, explicit connection management |

**New tools/patterns to consider:**
- **Pydantic TypeAdapter:** Validate lists/dicts without wrapper models (Pydantic v2 feature)
- **httpx HTTP/2:** Enable with `http2=True` for better performance with modern servers
- **Rich Traceback handler:** Set as default exception handler for beautiful error output
- **Typer CLI completion:** Built-in shell completion for bash/zsh/fish

**Deprecated/outdated:**
- **requests library:** Still works but lacks async, HTTP/2, and modern timeout handling
- **Pydantic v1:** No longer maintained, use v2 for 5-50x performance boost
- **Manual retry loops:** Use tenacity instead of hand-rolled retry logic
- **print() for CLI output:** Use Rich Console for formatted, colored output
</sota_updates>

<open_questions>
## Open Questions

Things that couldn't be fully resolved during research:

1. **NPM API Version Header**
   - What we know: Some sources mention `X-API-Version: next` header
   - What's unclear: Whether this is required, optional, or version-specific
   - Recommendation: Test both with/without header, document findings during implementation

2. **Proxy Host Locations Field Structure**
   - What we know: `locations` is an array for path-specific forwarding rules
   - What's unclear: Exact schema for location objects (path, forward_host, forward_port, etc.)
   - Recommendation: Defer to phase 5 (templates) when implementing complex routing patterns

3. **Certificate "new" Value Behavior**
   - What we know: `certificate_id` accepts integer ID or string "new"
   - What's unclear: What "new" actually does (creates Let's Encrypt cert? Requires additional fields?)
   - Recommendation: Defer to phase 4 (SSL automation), use existing cert IDs for phase 3

4. **NPM Version Detection and Compatibility**
   - What we know: NPM versions have different features and schema changes
   - What's unclear: How to detect NPM version via API, what versions to support
   - Recommendation: Test against production NPM version, warn on unknown versions
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- [NPM JSON Schema v2.9.6 Gist](https://gist.github.com/chaptergy/a8b28330b74159355f5ecc5ffa488b17) - Complete proxy host schema definition
- [NPM GitHub Discussion #3265](https://github.com/NginxProxyManager/nginx-proxy-manager/discussions/3265) - REST API endpoints, authentication, token generation
- [httpx Documentation: Timeouts](https://www.python-httpx.org/advanced/timeouts/) - Official timeout configuration
- [httpx Documentation: Clients](https://www.python-httpx.org/advanced/clients/) - Connection pooling patterns
- [Pydantic Documentation: Web and API Requests](https://docs.pydantic.dev/latest/examples/requests/) - Validation with httpx
- [Rich Documentation: Console API](https://rich.readthedocs.io/en/stable/console.html) - Console formatting, tables
- [Typer Documentation: Exceptions](https://typer.tiangolo.com/tutorial/exceptions/) - Error handling with Rich

### Secondary (MEDIUM confidence)
- [How to Retry Failed Python Requests 2025](https://oxylabs.io/blog/python-requests-retry) - Retry patterns verified against tenacity docs
- [Python HTTPX Retry Failed Requests (ScrapeOps)](https://scrapeops.io/python-web-scraping-playbook/python-httpx-retry-failed-requests/) - httpx retry configuration
- [Getting Started with HTTPX (Better Stack)](https://betterstack.com/community/guides/scaling-python/httpx-explained/) - httpx best practices
- [10 Best Python HTTP Clients 2025](https://iproyal.com/blog/best-python-http-clients/) - httpx vs requests comparison
- [Building Modern CMD Tool with Typer and Rich (codecentric)](https://www.codecentric.de/en/knowledge-hub/blog/lets-build-a-modern-cmd-tool-with-python-using-typer-and-rich) - Integration patterns

### Tertiary (LOW confidence - needs validation)
- [NPM GitHub Discussion #3527](https://github.com/NginxProxyManager/nginx-proxy-manager/discussions/3527) - Limited details on API documentation status
- Community Python wrappers (hosler/nginx-proxy-manager-api) - Implementation examples but uses older patterns (requests, not httpx)
</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: Nginx Proxy Manager undocumented REST API
- Ecosystem: Python HTTP clients (httpx), validation (Pydantic v2), CLI (Typer, Rich)
- Patterns: API client architecture, connection pooling, strict validation, error handling
- Pitfalls: Undocumented API changes, timeout handling, connection exhaustion, retry logic

**Confidence breakdown:**
- Standard stack: HIGH - verified with official docs, widely adopted in 2025
- Architecture: HIGH - from official httpx/Pydantic/Typer documentation and examples
- Pitfalls: MEDIUM - derived from NPM community discussions and HTTP client best practices
- Code examples: HIGH - from official library documentation and project architecture decisions

**Research date:** 2026-01-04
**Valid until:** 2026-02-04 (30 days - Python ecosystem stable, but NPM API may change)

**NPM API Coverage:**
- Proxy host endpoints: MEDIUM confidence (community reverse-engineering + JSON schema)
- Full schema structure: MEDIUM confidence (v2.9.6 schema may not match current version)
- Authentication: HIGH confidence (verified in phase 2 implementation)
- Error responses: LOW confidence (need to test actual API error formats)
</metadata>

---

*Phase: 03-proxy-host-management*
*Research completed: 2026-01-04*
*Ready for planning: yes*
