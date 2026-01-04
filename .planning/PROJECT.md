# NPM CLI

## What This Is

A Python command-line tool for managing Nginx Proxy Manager (NPM) via its API. Automates the three most painful NPM workflows: proxy host management with templates, end-to-end SSL certificate automation, and reusable configuration patterns (Authentik forward auth, VPN-only access, API bypass).

## Core Value

Transform multi-step manual operations (SQL queries, file editing, docker exec commands) into single-command workflows with validation and safety.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Proxy host management - Create, list, update, delete proxy hosts via NPM API with template support
- [ ] SSL certificate automation - End-to-end workflow: cert creation, NPM integration, attachment to proxy hosts
- [ ] Configuration template system - Reusable templates for common patterns (Authentik forward auth, VPN-only access, API bypass paths, WebSocket support)
- [ ] ZSH autocomplete - Tab completion for commands and options
- [ ] Connect to NPM in Docker - Discover and connect to NPM container, handle authentication
- [ ] Reproducible test suite - Non-destructive tests using dedicated NPM container
- [ ] User-friendly documentation - README with clear setup and usage instructions for public release

### Out of Scope

- Monitoring/metrics integration (Prometheus/Grafana) — defer to future version, focus on core management first
- Import/export and migration tools (backup/restore, Traefik/Caddy import) — not needed for v1 workflows
- Infrastructure as Code (YAML declarative configs, Ansible/Terraform) — adds complexity, defer until core workflows proven
- Direct database operations — use NPM API exclusively; database was a hack from lack of API knowledge
- Bulk operations and advanced querying — start with single-entity operations, add batch later if needed
- Real-time log streaming and monitoring — defer to future version
- Certificate renewal automation — focus on initial creation first, add renewal in future version

## Context

### Pain Points Being Solved

Current NPM management requires:
- Hand-crafted SQL queries with JSON field escaping
- Multi-step SSL workflows (certbot → database entry → symlink creation → nginx config → reload)
- Copy-pasting nginx config snippets for repetitive patterns (Authentik forward auth, network ACLs)
- Manual docker exec commands for validation and reloads
- No validation before applying changes (discover errors after nginx reload)

### Technical Environment

- NPM runs in Docker containers (production instance exists, must not break)
- NPM architecture: Node.js web UI → MySQL database → generated nginx configs
- Docker network setup with multiple services (Authentik, various apps)
- Homelab environment with VPN access (WireGuard) and LAN restrictions
- Common patterns: Authentik forward auth, network ACLs, API/webhook bypass paths

### NPM API Unknown Territory

The comprehensive requirements document from previous project shows database operations, but these were likely expedient hacks. Need to analyze NPM codebase to understand actual API capabilities before implementing features. API-first approach is mandatory.

### Existing Production Setup

- Production NPM instance in Docker (cannot break)
- Multiple proxy hosts already configured (n8n, Open WebUI, WireGuard UI, Homepage, etc.)
- Mix of HTTP-01 and DNS-01 SSL certificates
- Authentik integration for SSO
- Network restrictions (VPN/LAN only access patterns)

## Constraints

- **NPM Version Compatibility**: Must work with existing NPM version in production — cannot require upgrades or break existing setup
- **Installation Method**: Use uv for dependency management and installation (uv sync, NOT uv run pip) — aligns with modern Python tooling
- **Dependency Minimalism**: Prefer Python stdlib where possible — reduce dependency bloat and installation complexity
- **API-First Approach**: Use NPM API exclusively, avoid direct database operations — cleaner, more maintainable, respects NPM's architecture
- **Testing Safety**: Tests must be reproducible and non-destructive using dedicated NPM container — cannot risk production instance

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python with uv | User preference, modern Python tooling, good CLI ecosystem (Click/Typer) | — Pending |
| API-first (no database) | Previous DB operations were hacks; respect NPM architecture, more maintainable | — Pending |
| Minimal v1 scope | Focus on core trinity (proxy, SSL, templates) rather than kitchen sink | — Pending |
| Dedicated test container | Reproducible tests, production safety, can be destructive without fear | — Pending |
| ZSH autocomplete | User's primary shell, improves UX significantly | — Pending |

---
*Last updated: 2026-01-04 after initialization*
