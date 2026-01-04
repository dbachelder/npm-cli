# Phase 4: SSL Certificate Automation - Research

**Researched:** 2026-01-04
**Domain:** NPM certificate API, Let's Encrypt integration, certificate lifecycle management
**Confidence:** MEDIUM-HIGH

<research_summary>
## Summary

Researched NPM's certificate management API and Let's Encrypt integration for implementing end-to-end SSL certificate workflows. NPM uses an undocumented API with endpoints discovered through source code inspection and community reverse-engineering.

NPM internally delegates to Certbot for Let's Encrypt certificate acquisition, supporting both HTTP-01 and DNS-01 challenges with multiple DNS provider plugins (Cloudflare, Route53, DigitalOcean, etc.). The standard workflow involves: (1) create certificate via NPM API, (2) NPM invokes Certbot internally, (3) attach certificate to proxy host via certificate_id field.

**Key finding:** Don't implement ACME protocol directly - NPM handles Let's Encrypt integration through Certbot. Our CLI interacts only with NPM's certificate API, which abstracts the complexity.

**Primary recommendation:** Use NPM certificate API endpoints (`/api/nginx/certificates`) for create/list/delete operations. Model certificate data with Pydantic (following proxy host pattern). Certificate attachment is done via proxy host update with certificate_id field.
</research_summary>

<standard_stack>
## Standard Stack

### Core Dependencies (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | latest | HTTP client for NPM API | Already used for proxy hosts, async-capable |
| pydantic | latest | API model validation | Already used, strict validation for undocumented API |
| typer | latest | CLI framework | Already used for commands |
| rich | latest | Console output | Already used for formatting |

### Optional - Certificate Validation (Not Needed for MVP)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| cryptography | 45.0+ | Certificate parsing/validation | Only if implementing local cert validation/inspection |
| pyOpenSSL | 25.3+ | Legacy OpenSSL wrapper | NOT RECOMMENDED - Python cryptography library preferred by maintainers |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| NPM API | Direct Certbot invocation | Bypasses NPM, breaks integration, loses audit trail |
| NPM API | python-acme library | Reimplements what NPM already does, unnecessary complexity |
| httpx | requests library | httpx already in use, async-ready for future |

**Installation:**
No new dependencies needed for MVP. NPM handles Let's Encrypt integration.

```bash
# Optional for certificate inspection features (defer to v2)
uv add cryptography
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Code Structure
```
src/npm_cli/
├── api/
│   ├── models.py           # Add Certificate* Pydantic models
│   ├── client.py           # Add certificate_* methods to NPMClient
│   └── exceptions.py       # Already exists
├── cli/
│   ├── cert.py            # NEW: Certificate commands (create, list, show, delete)
│   └── proxy.py           # MODIFY: Support --certificate option
```

### Pattern 1: Certificate Model Hierarchy
**What:** Mirror proxy host pattern - separate models for create/read/update operations
**When to use:** All certificate API operations
**Example:**
```python
# In src/npm_cli/api/models.py

class CertificateCreate(BaseModel):
    """Request model for creating Let's Encrypt certificate."""
    model_config = ConfigDict(extra="ignore", strict=True)

    # Required for Let's Encrypt
    domain_names: list[str] = Field(
        min_length=1,
        description="Domains for certificate (first is primary, rest are SANs)"
    )
    meta: dict = Field(
        description="Provider-specific metadata (letsencrypt_email, dns_provider, etc.)"
    )

    # Optional fields
    nice_name: str = Field(
        default="",
        description="Human-readable certificate name"
    )
    provider: Literal["letsencrypt"] = Field(
        default="letsencrypt",
        description="Certificate provider"
    )

class Certificate(CertificateCreate):
    """Response model with read-only fields."""
    id: int = Field(ge=1, description="Certificate ID")
    created_on: str = Field(description="Creation timestamp")
    modified_on: str = Field(description="Last modification timestamp")
    expires_on: str = Field(description="Certificate expiration timestamp")
    owner_user_id: int = Field(ge=1, description="Owner user ID")
```

### Pattern 2: NPMClient Certificate Methods
**What:** Add certificate operations to existing NPMClient class
**When to use:** All certificate API interactions
**Example:**
```python
# In src/npm_cli/api/client.py

class NPMClient:
    # ... existing methods ...

    def certificate_create(self, cert: CertificateCreate) -> Certificate:
        """Create new Let's Encrypt certificate.

        POST /api/nginx/certificates
        NPM delegates to Certbot internally.
        """
        response = self._request(
            "POST",
            "/api/nginx/certificates",
            json=cert.model_dump(exclude_unset=True)
        )
        return Certificate.model_validate(response)

    def certificate_list(self) -> list[Certificate]:
        """List all certificates.

        GET /api/nginx/certificates
        """
        response = self._request("GET", "/api/nginx/certificates")
        return [Certificate.model_validate(c) for c in response]

    def certificate_get(self, cert_id: int) -> Certificate:
        """Get certificate by ID.

        GET /api/nginx/certificates/{id}
        """
        response = self._request("GET", f"/api/nginx/certificates/{cert_id}")
        return Certificate.model_validate(response)

    def certificate_delete(self, cert_id: int) -> None:
        """Delete certificate.

        DELETE /api/nginx/certificates/{id}
        Revokes Let's Encrypt cert and removes from NPM.
        """
        self._request("DELETE", f"/api/nginx/certificates/{cert_id}")
```

### Pattern 3: Certificate Attachment via Proxy Host Update
**What:** Attach certificate to proxy host by updating certificate_id field
**When to use:** After creating certificate, to enable SSL
**Example:**
```python
# In CLI or client code

# 1. Create certificate
cert = client.certificate_create(
    CertificateCreate(
        domain_names=["example.com"],
        meta={"letsencrypt_email": "admin@example.com"}
    )
)

# 2. Attach to proxy host
proxy_host = client.proxy_host_update(
    host_id=proxy_host_id,
    updates=ProxyHostUpdate(
        certificate_id=cert.id,
        ssl_forced=True,
        hsts_enabled=True
    )
)
```

### Pattern 4: DNS Provider Credentials in meta Field
**What:** Pass DNS provider credentials in meta field for DNS-01 challenges
**When to use:** Wildcard certificates or when HTTP-01 not possible
**Example:**
```python
# Cloudflare DNS-01 challenge
cert = CertificateCreate(
    domain_names=["*.example.com", "example.com"],
    meta={
        "letsencrypt_email": "admin@example.com",
        "dns_provider": "cloudflare",
        "dns_provider_credentials": "dns_cloudflare_api_token = YOUR_TOKEN",
        "propagation_seconds": 30  # Optional: DNS propagation delay
    }
)

# Route53 DNS-01 challenge (uses AWS env vars)
cert = CertificateCreate(
    domain_names=["*.example.com", "example.com"],
    meta={
        "letsencrypt_email": "admin@example.com",
        "dns_provider": "route53"
        # No credentials needed - Route53 uses AWS env vars
    }
)
```

### Anti-Patterns to Avoid
- **Implementing ACME protocol directly:** NPM already integrates Certbot - don't reimplement
- **Using extra="forbid" for certificates:** NPM API returns additional fields, use extra="ignore"
- **Hardcoding DNS provider list:** DNS providers are Certbot plugin-dependent, discover from NPM capabilities
- **Storing certificates locally:** NPM manages certificate storage, our CLI is just an API client
- **Manual Certbot invocation:** Bypasses NPM, breaks audit trail and UI integration
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

Problems that NPM or Certbot already solve:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ACME protocol | Custom Let's Encrypt client | NPM API → Certbot | ACME has rate limits, challenge complexities, renewal logic - Certbot handles all |
| Certificate validation | PEM parsing, expiry checks | NPM API responses | NPM tracks expiration, renewal status - trust API as source of truth |
| DNS provider plugins | Custom DNS API clients | NPM's Certbot integration | Certbot has 50+ DNS provider plugins - leverage existing work |
| Certificate storage | Local cert management | NPM certificate API | NPM stores certs in /etc/letsencrypt/, manages symlinks, handles permissions |
| Renewal automation | Custom renewal scheduler | NPM's internal renewal | NPM checks expiration hourly, auto-renews using Certbot |

**Key insight:** NPM is a wrapper around Certbot with persistent storage and nginx integration. Our CLI wraps NPM's API. Don't bypass abstraction layers - each layer exists for good reasons (audit logging, UI consistency, automated renewal).

**What to build:**
- Pydantic models for NPM certificate API
- NPMClient methods for certificate CRUD
- CLI commands for user-friendly certificate management
- Workflow helpers (create cert + attach to proxy host in one command)

**What NOT to build:**
- ACME client implementation
- Certificate file parsing (unless adding inspection features in v2)
- DNS provider integrations (use NPM's Certbot integration)
- Renewal scheduling (NPM handles this)
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Let's Encrypt Rate Limits
**What goes wrong:** Hit 5 failed authorizations per hour limit during testing
**Why it happens:** Testing against production Let's Encrypt instead of staging
**How to avoid:** NPM doesn't expose staging environment toggle via API - test with dedicated NPM container, not production
**Warning signs:** API returns rate limit errors, certificates not issued

### Pitfall 2: Certificate Not Attached to Proxy Host
**What goes wrong:** Certificate created but proxy host still shows HTTP
**Why it happens:** Creating certificate doesn't automatically attach it - requires separate proxy host update
**How to avoid:** Always update proxy host with certificate_id after creation, or provide workflow command that does both
**Warning signs:** Certificate exists in NPM but proxy host still on port 80

### Pitfall 3: Wrong DNS Provider Credentials Format
**What goes wrong:** DNS-01 challenge fails despite correct API token
**Why it happens:** Certbot expects specific credential file format per provider (e.g., "dns_cloudflare_api_token = VALUE")
**How to avoid:** Document credential format per provider, validate format before API call
**Warning signs:** NPM API returns validation error, Certbot fails in NPM logs

### Pitfall 4: Deleting Certificate Attached to Proxy Hosts
**What goes wrong:** Deleting certificate breaks proxy hosts using it (Issue #4288)
**Why it happens:** NPM doesn't prevent deleting in-use certificates
**How to avoid:** Before deletion, check if certificate_id is referenced by any proxy hosts, warn user
**Warning signs:** Proxy hosts return 502 errors after certificate deletion

### Pitfall 5: Certificate Lifetime Assumptions
**What goes wrong:** Hard-coded 90-day renewal logic breaks
**Why it happens:** Let's Encrypt reducing certificate lifetime to 45 days (announced Dec 2025)
**How to avoid:** Use NPM's expiry tracking, don't hardcode renewal intervals
**Warning signs:** Certificates expire unexpectedly, renewal window too narrow

### Pitfall 6: Undocumented API Schema Changes
**What goes wrong:** API calls fail with validation errors after NPM update
**Why it happens:** NPM API is undocumented, schema can change between versions
**How to avoid:** Use extra="ignore" in Pydantic models, log API response on validation failures for debugging
**Warning signs:** Pydantic validation errors on previously working code
</common_pitfalls>

<code_examples>
## Code Examples

Verified patterns from NPM source code and community scripts:

### Basic Certificate Creation (HTTP-01)
```python
# Source: NPM backend/internal/certificate.js + community scripts
# For single domain or apex + www (HTTP-01 challenge)

from npm_cli.api.models import CertificateCreate
from npm_cli.api.client import NPMClient

client = NPMClient(base_url="http://localhost:81", token="...")

# Simple domain certificate
cert = client.certificate_create(
    CertificateCreate(
        domain_names=["example.com", "www.example.com"],
        meta={
            "letsencrypt_email": "admin@example.com"
        },
        nice_name="Example.com Certificate"
    )
)

print(f"Certificate created: ID={cert.id}, expires={cert.expires_on}")
```

### Wildcard Certificate with DNS-01 (Cloudflare)
```python
# Source: NPM backend/internal/certificate.js + Certbot Cloudflare plugin docs
# For wildcard domains requiring DNS-01 challenge

cert = client.certificate_create(
    CertificateCreate(
        domain_names=["*.example.com", "example.com"],
        meta={
            "letsencrypt_email": "admin@example.com",
            "dns_provider": "cloudflare",
            "dns_provider_credentials": "dns_cloudflare_api_token = YOUR_CLOUDFLARE_TOKEN",
            "propagation_seconds": 30  # Wait 30s for DNS propagation
        },
        nice_name="Example.com Wildcard"
    )
)
```

### End-to-End: Create Certificate and Attach to Proxy Host
```python
# Source: Combining NPM certificate + proxy host patterns
# Complete workflow for SSL-enabled proxy host

from npm_cli.api.models import CertificateCreate, ProxyHostUpdate

# 1. Create certificate
cert = client.certificate_create(
    CertificateCreate(
        domain_names=["app.example.com"],
        meta={"letsencrypt_email": "admin@example.com"}
    )
)

# 2. Find proxy host by domain
proxy_hosts = client.proxy_host_list()
host = next((h for h in proxy_hosts if "app.example.com" in h.domain_names), None)

if not host:
    raise ValueError("Proxy host not found for app.example.com")

# 3. Attach certificate and enable SSL
updated_host = client.proxy_host_update(
    host_id=host.id,
    updates=ProxyHostUpdate(
        certificate_id=cert.id,
        ssl_forced=True,          # Redirect HTTP → HTTPS
        hsts_enabled=True,        # Enable HSTS
        hsts_subdomains=False,    # Don't include subdomains
        http2_support=True        # Enable HTTP/2
    )
)

print(f"SSL enabled for {host.domain_names[0]}")
```

### List Certificates with Expiration Check
```python
# Source: NPM certificate.js + community patterns
# Check certificate expiration status

from datetime import datetime, timezone

certs = client.certificate_list()

for cert in certs:
    expires = datetime.fromisoformat(cert.expires_on.replace("Z", "+00:00"))
    days_left = (expires - datetime.now(timezone.utc)).days

    status = "⚠️  EXPIRING SOON" if days_left < 30 else "✓ Valid"
    print(f"{status} {cert.nice_name or cert.domain_names[0]}: {days_left} days")
```

### Safe Certificate Deletion with Usage Check
```python
# Source: NPM Issue #4288 - prevent breaking proxy hosts
# Check certificate usage before deletion

def safe_certificate_delete(client: NPMClient, cert_id: int) -> None:
    """Delete certificate only if not in use by any proxy host."""

    # 1. Get certificate details
    cert = client.certificate_get(cert_id)

    # 2. Check all proxy hosts for usage
    proxy_hosts = client.proxy_host_list()
    in_use = [h for h in proxy_hosts if h.certificate_id == cert_id]

    if in_use:
        domains = ", ".join(h.domain_names[0] for h in in_use)
        raise ValueError(
            f"Cannot delete certificate: in use by {len(in_use)} proxy host(s): {domains}"
        )

    # 3. Safe to delete
    client.certificate_delete(cert_id)
    print(f"Deleted certificate: {cert.nice_name or cert.domain_names[0]}")
```
</code_examples>

<sota_updates>
## State of the Art (2025-2026)

What's changed recently in Let's Encrypt and certificate management:

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 90-day certificate lifetime | 45-day lifetime | Announced Dec 2025, rolling out 2026 | Must use ARI (ACME Renewal Info) for optimal renewal timing, not hardcoded 60-day intervals |
| Manual renewal timing | ARI-based renewal | ACMEv2 / 2023+ | Certbot checks renewal window dynamically, exempt from rate limits |
| ACMEv1 API | ACMEv2 (RFC 8555) | June 2021 (ACMEv1 sunset) | All modern clients use ACMEv2, validates only |
| pyOpenSSL for cert validation | cryptography library | 2025 recommendation | Python Cryptographic Authority recommends cryptography over pyOpenSSL |

**New patterns to consider:**
- **ACME Renewal Information (ARI):** Let's Encrypt servers tell clients optimal renewal window - Certbot supports, NPM inherits
- **Shorter certificate lifetimes:** 45-day certs require more frequent renewals, automation critical
- **Rate limit exemptions for renewals:** ARI renewals exempt from "New Certificates per Registered Domain" limit

**Deprecated/outdated:**
- **ACMEv1:** Sunset June 2021, all clients must use ACMEv2
- **Hardcoded 60-day renewal:** No longer sufficient with 45-day lifetimes
- **pyOpenSSL for new projects:** Use `cryptography` library instead per maintainer recommendation
- **Manual certificate renewal:** Automation mandatory with shorter lifetimes

**NPM-Specific State:**
- **Latest version:** v2.12.4 (January 2025) - improved API schema, copyright updated to 2025
- **Certbot integration:** NPM uses Certbot internally, inherits all Certbot DNS provider plugins
- **Renewal system:** Hourly timer checks expiring certificates, delegates to Certbot for renewal
</sota_updates>

<open_questions>
## Open Questions

Things that couldn't be fully resolved:

1. **Certificate API Endpoint Paths**
   - What we know: Endpoints are `/api/nginx/certificates` (POST, GET, DELETE), `/api/nginx/certificates/validate`, `/api/nginx/certificates/test-http`
   - What's unclear: Exact request/response schemas (API undocumented, inferred from source code)
   - Recommendation: Implement with extra="ignore" for Pydantic models, test against real NPM instance, log failures for schema refinement

2. **DNS Provider Credential Formats**
   - What we know: Each Certbot DNS plugin expects specific credential file format (e.g., `dns_cloudflare_api_token = VALUE`)
   - What's unclear: Complete list of all supported providers and their exact credential formats
   - Recommendation: Start with Cloudflare and Route53 (most common), document credential format per provider as discovered

3. **Custom Certificate Upload**
   - What we know: NPM supports provider="other" for custom certificates, has `/upload` endpoint
   - What's unclear: Exact API for uploading custom (non-Let's Encrypt) certificates
   - Recommendation: Defer custom certificate upload to Phase 5 or v2, focus on Let's Encrypt for MVP

4. **Certificate Renewal Trigger**
   - What we know: NPM has hourly timer that checks expiration and auto-renews
   - What's unclear: Whether API exposes manual renewal trigger endpoint
   - Recommendation: Assume NPM handles renewal automatically, implement "show renewal status" but not manual renewal for MVP

5. **Staging Environment Support**
   - What we know: Let's Encrypt has staging environment for testing, Certbot supports `--staging` flag
   - What's unclear: Whether NPM API exposes staging toggle or requires NPM configuration change
   - Recommendation: Use dedicated NPM test container, document that staging requires NPM-level configuration
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- [NPM backend/internal/certificate.js](https://github.com/NginxProxyManager/nginx-proxy-manager/blob/v2.11.3/backend/internal/certificate.js) - Certificate lifecycle implementation
- [NPM backend/schema directory](https://github.com/NginxProxyManager/nginx-proxy-manager/tree/develop/backend/schema) - API schema definitions
- [Let's Encrypt Rate Limits](https://letsencrypt.org/docs/rate-limits/) - Official rate limit documentation
- [Let's Encrypt 45-day certificate announcement](https://letsencrypt.org/2025/12/02/from-90-to-45) - Certificate lifetime changes
- [Certbot PyPI](https://pypi.org/project/certbot/) - Official Certbot package, Python 3.10+, latest Dec 2025

### Secondary (MEDIUM confidence)
- [NPM Discussion #3527](https://github.com/NginxProxyManager/nginx-proxy-manager/discussions/3527) - General API documentation discussion, confirmed API undocumented
- [NPM Discussion #3265](https://github.com/NginxProxyManager/nginx-proxy-manager/discussions/3265) - REST API proxy host configuration, mentioned audit log method
- [NPM Issue #4288](https://github.com/NginxProxyManager/nginx-proxy-manager/issues/4288) - Certificate deletion breaking proxy hosts bug
- [Community bash script](https://github.com/Erreur32/nginx-proxy-manager-API) - Reverse-engineered certificate endpoints
- [DeepWiki DNS-01 Challenges](https://deepwiki.com/NginxProxyManager/nginx-proxy-manager/3.3-dns-challenges) - DNS provider list and credential formats
- [pyOpenSSL documentation](https://www.pyopenssl.org/en/stable/api/crypto.html) - Version 25.3.0, recommends cryptography library instead

### Tertiary (LOW confidence - needs validation during implementation)
- [Let's Encrypt Community: NPM + Cloudflare](https://community.letsencrypt.org/t/local-dns-challenge-setup-with-nginx-proxy-manager-cloudflare/237859) - Setup patterns
- [Medium: NPM Cloudflare SSL](https://medium.com/@life-is-short-so-enjoy-it/homelab-nginx-proxy-manager-setup-ssl-certificate-with-domain-name-in-cloudflare-dns-732af64ddc0b) - Tutorial
- WebSearch findings on DNS providers - cross-referenced with Certbot plugin list
</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: NPM certificate API (undocumented, reverse-engineered)
- Ecosystem: Certbot (Let's Encrypt client), DNS provider plugins
- Patterns: Certificate CRUD via API, attachment to proxy hosts, DNS-01 challenges
- Pitfalls: Rate limits, certificate deletion, API schema changes, credential formats

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies needed, use existing httpx/pydantic/typer
- Architecture: HIGH - Follows established proxy host patterns, source code verified
- Pitfalls: MEDIUM-HIGH - Rate limits and lifetime changes documented, API schema pitfalls inferred from issues
- Code examples: MEDIUM - Synthesized from source code patterns + community scripts, need real NPM testing

**Research date:** 2026-01-04
**Valid until:** 2026-02-04 (30 days - NPM API stable, Let's Encrypt changes gradual)

**Critical for planning:**
- NPM API is undocumented - use extra="ignore" for resilience
- Don't implement ACME - NPM wraps Certbot
- Certificate attachment is separate step from creation
- DNS provider credentials go in meta field with specific format
- Test against dedicated NPM container, not production (rate limits)
</metadata>

---

*Phase: 04-ssl-automation*
*Research completed: 2026-01-04*
*Ready for planning: yes*
