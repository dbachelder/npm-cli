# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-04)

**Core value:** Transform multi-step manual operations (SQL queries, file editing, docker exec commands) into single-command workflows with validation and safety.
**Current focus:** Phase 1 — Foundation

## Current Position

Phase: 7 of 7 (Distribution)
Plan: 1 of 1 in current phase
Status: Complete
Last activity: 2026-01-04 — Completed 07-01-PLAN.md

Progress: ██████████████ 100% (14 of 14 plans complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 14
- Average duration: 11 min
- Total execution time: 153 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Foundation | 1 | 8 min | 8 min |
| 2. Connection & Auth | 3 | 34 min | 11 min |
| 3. Proxy Host Management | 3 | 52 min | 17 min |
| 4. SSL Certificate Automation | 3 | 25 min | 8 min |
| 5. Configuration Templates | 1 | 6 min | 6 min |
| 6. Testing & Documentation | 2 | 13 min | 6 min |
| 7. Distribution | 1 | 15 min | 15 min |

**Recent Trend:**
- Last plan: 15 min (PyPI packaging and verification)
- Trend: Complete package preparation with local testing

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

| Phase | Decision | Rationale |
|-------|----------|-----------|
| 1 | Python 3.11+ with modern type hints | Performance improvements and compatibility with modern Python patterns |
| 1 | Strict Pydantic models with extra="forbid" | Catch NPM API schema changes early given undocumented API |
| 1 | Typer subcommands with Rich console output | Professional CLI UX following RESEARCH.md patterns |
| 2 | TDD approach for settings module | RED-GREEN-REFACTOR cycle with atomic commits improves design quality |
| 2 | NPM_ environment variable prefix | Clear namespacing for configuration |
| 2 | File-based token caching (not keyring) | Simpler for MVP, tokens expire anyway in 24-48 hours |
| 2 | httpx client with 30s timeout | Prevent CLI hangs per RESEARCH.md Pitfall #4 |
| 2 | Three-strategy Docker discovery | Maximum compatibility across deployment patterns (name → label → patterns) |
| 2 | Username display in status command | Debug visibility for .env configuration validation |
| 2 | Enhanced error messages with API response details | Critical for debugging authentication and connection issues |
| 2 | Email format required for NPM authentication | NPM API requires email in identity field, not plain username |
| 3 | Custom exception hierarchy with response preservation | NPMAPIError base with httpx.Response for debugging, specialized subclasses for connection/validation errors |
| 3 | ProxyHost model inheritance pattern | ProxyHost inherits from ProxyHostCreate to avoid duplication while adding read-only fields |
| 3 | Relaxed validation (extra="ignore") instead of extra="forbid" | NPM API undocumented, returns extra fields - validate required fields but don't break on API additions |
| 3 | GET-merge-PUT pattern for proxy host updates | NPM PUT requires full object but rejects read-only fields - extract writable fields only, normalize nulls, merge updates |
| 3 | Domain-based lookup for show command | UX improvement - users remember domains better than IDs, searches domain_names field |
| 4 | Certificate model inheritance pattern | Certificate inherits from CertificateCreate following proven ProxyHost pattern |
| 4 | meta field as dict type | Flexible structure to accommodate various DNS provider configurations for future DNS challenge support |
| 4 | Workflow helper pattern for cert attachment | attach_certificate_to_proxy combines cert creation + proxy update into single operation, simplifies common 3-step workflow |
| 4 | ValueError for business logic errors | Use ValueError (not NPMAPIError) when proxy host not found - clearer error semantics than API errors |
| 4 | Empty meta field for HTTP-01 challenges | NPM stores letsencrypt_email at account level, not per-certificate - meta={} for HTTP-01, only populate for DNS challenges |
| 4 | Certificate lookup by domain name | Following proxy pattern, cert show accepts ID or domain - searches domain_names array, improves UX over ID-only lookup |
| 5 | Pure template functions over classes | Template functions return strings - simpler, more testable, easier to compose than class-based approach |
| 5 | Literal type for template names | Provides CLI autocomplete/validation for template_name argument - better UX than plain strings |
| 5 | Combined template composition | authentik_with_bypass() composes existing functions instead of duplicating - DRY principle, maintains single source of truth |
| 5 | Auto-detect backend from proxy host | CLI auto-constructs backend URL from proxy host if --backend not provided - reduces typing for common case |
| 5 | Default vpn_only=True for authentik-bypass | Security-first default matching production best practice - opt-out if needed rather than opt-in |
| 6 | NPM Container Complexity - Pattern Over Implementation | NPM requires MySQL/MariaDB database setup - testcontainers pattern demonstrated but marked as skip, focus on CliRunner and pytest-httpx for immediate testing value |
| 6 | Three-tier testing strategy | CliRunner for CLI testing, pytest-httpx for API mocking, manual testing against production NPM for end-to-end validation |
| 6 | Typer's built-in completion over custom scripts | Typer provides --install-completion by default (enabled in 0.12+), no need for hand-rolled completion scripts |
| 6 | README structure following CLI best practices | Clear value proposition, quick start, extensive examples, template reference, development/testing sections (Simon Willison pattern) |
| 7 | LICENSE file reference format in pyproject.toml | Use `license = { file = "LICENSE" }` instead of `license = "MIT"` to ensure LICENSE file included in package distribution per PyPI requirements |
| 7 | Development Status Beta classifier | Reflects current maturity level - functional but may need refinement based on user feedback |
| 7 | Python version support 3.11-3.13 | Explicit classifiers for tested versions, 3.14 works but not officially declaring support yet |

### Deferred Issues

None yet.

### Blockers/Concerns

None yet.

### Roadmap Evolution

- Phase 7 added: Distribution (package and publish to PyPI)

## Session Continuity

Last session: 2026-01-04
Stopped at: Completed 07-01-PLAN.md (Phase 7 complete - all phases done!)
Resume file: None
Next action: Complete PyPI publication (configure credentials, publish, tag release) or archive milestone 1.0
