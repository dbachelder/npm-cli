# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python CLI tool for managing Nginx Proxy Manager (NPM) via its undocumented API. Automates proxy host management, SSL certificate workflows, and configuration templates. Built with uv, Typer, and Pydantic.

**Core value:** Transform multi-step manual operations (SQL queries, docker exec commands, nginx config editing) into single-command workflows with validation and safety.

## Development Commands

### Environment Setup
```bash
# Install dependencies
uv sync

# Run CLI
uv run npm-cli --help
uv run npm-cli version
```

### Testing and Quality
```bash
# Run tests
uv run pytest

# Run specific test
uv run pytest tests/test_file.py::test_function

# Linting
uv run ruff check src/
uv run ruff check src/ --fix

# Type checking (when added)
uv run mypy src/
```

### Running the CLI During Development
```bash
# Use uv run to execute with project dependencies
uv run npm-cli proxy list
uv run npm-cli cert create --domain example.com

# Or install in editable mode
uv pip install -e .
npm-cli --help
```

## Architecture

### Package Structure
```
src/npm_cli/
├── __main__.py          # Entry point, Typer app setup, subcommand registration
├── api/
│   └── models.py        # Pydantic models for NPM API (TokenRequest, TokenResponse, etc.)
├── cli/
│   ├── proxy.py         # Proxy host commands (create, list, update, delete)
│   ├── cert.py          # SSL certificate commands
│   └── config.py        # Configuration commands
```

### CLI Framework Pattern
- **Typer** for CLI with subcommands (`app.add_typer()`)
- **Rich** for formatted console output (use `console.print()`, not `print()`)
- **Pydantic** for API request/response validation with strict models (`extra="forbid"` for API models, `extra="ignore"` for Settings to allow non-NPM env vars)
- Type hints on all CLI arguments (not decorator strings)

### NPM API Critical Context

**The NPM API is completely undocumented.** There is no official API documentation. API endpoints are discovered through:
1. NPM source code inspection (`backend/routes/api`)
2. Browser DevTools network analysis
3. Built-in Audit Log feature
4. Community reverse-engineering (GitHub discussions)

**Discovery process:**
- Read `.planning/phases/01-foundation/API-DISCOVERY.md` for authenticated endpoints
- Inspect NPM source code before implementing new API calls
- Test against dedicated NPM container (NOT production)
- Document findings in API-DISCOVERY.md

**Authentication:**
- POST `/api/tokens` with `{identity, secret}` returns JWT bearer token
- Include token in `Authorization: Bearer {token}` header
- Tokens expire in 24-48 hours unless explicitly set
- See `src/npm_cli/api/models.py` for validated request/response models

## Critical Constraints

### API-First Approach
**Use NPM API exclusively.** The comprehensive requirements document (`.planning/REQUIREMENTS.md`) shows database operations, but these were expedient hacks from before API discovery. Respect NPM's architecture - use the API, not direct database access.

### Production Safety
- Production NPM instance exists in Docker (cannot break it)
- All destructive testing must use dedicated test container
- Validate changes before applying (nginx config syntax, API responses)
- Tests must be reproducible and non-destructive

### NPM Version Compatibility
Must work with existing NPM version in production. Cannot require upgrades or break existing setup.

### Dependency Management
- Use **uv** for all dependency operations (`uv sync`, `uv add`, NOT `uv run pip`)
- Prefer Python stdlib where possible (minimize dependencies)
- Pin major versions in pyproject.toml

## Project Context

### What This Tool Replaces
Current NPM management requires:
- Hand-crafted SQL queries with JSON field escaping
- Multi-step SSL workflows (certbot → database → symlinks → config → reload)
- Copy-pasting nginx config snippets (Authentik forward auth, network ACLs)
- Manual docker exec commands for validation
- No validation before applying (discover errors after reload)

### Technical Environment
- NPM in Docker containers (nginx-proxy-manager, mysql)
- NPM architecture: Node.js web UI → MySQL database → generated nginx configs
- Docker network with multiple services (Authentik, apps)
- Homelab with VPN (WireGuard) and LAN restrictions
- Common patterns: Authentik forward auth, network ACLs, API/webhook bypass

### Active Requirements
See `.planning/PROJECT.md` for full context. Core features:
1. Proxy host management (create, list, update, delete with templates)
2. SSL certificate automation (end-to-end: creation → integration → attachment)
3. Configuration templates (Authentik, VPN-only, API bypass, WebSocket)
4. ZSH autocomplete
5. NPM Docker connection and authentication
6. Reproducible test suite with dedicated container

### Out of Scope
- Direct database operations (use API exclusively)
- Monitoring/metrics integration (defer to v2)
- Infrastructure as Code declarative configs (defer until core proven)
- Import/export and migration tools (not needed for v1)
- Real-time log streaming (defer to v2)
- Certificate renewal automation (focus on creation first)

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Python 3.11+ with uv | User preference, modern tooling, 10-100x faster dependency resolution |
| Typer + Rich | Type-safe CLI with beautiful output formatting |
| Pydantic strict models | Catch NPM API schema changes early (undocumented API) |
| API-first (no database) | Respect NPM architecture, more maintainable than SQL hacks |
| Dedicated test container | Reproducible tests, production safety |

## Development Workflow

### Adding New API Endpoints
1. Inspect NPM source code (`backend/routes/api`) or use browser DevTools
2. Document findings in `.planning/phases/*/API-DISCOVERY.md`
3. Create Pydantic models in `src/npm_cli/api/models.py` with `extra="forbid"`
4. Test against dedicated NPM container (NOT production)
5. Update CLAUDE.md if new patterns emerge

### Adding New Commands
1. Create command in appropriate `cli/*.py` module
2. Use Typer with type hints (not decorator strings)
3. Output via Rich console (not print)
4. Register in `__main__.py` if new subcommand group
5. Add tests in `tests/`

### Before Committing
```bash
uv run ruff check src/ --fix
uv run pytest
```

## Distribution

**Published Package:**
- PyPI: https://pypi.org/project/npm-cli/
- GitHub: https://github.com/dbachelder/npm-cli
- Install: `uv tool install npm-cli` or `pip install npm-cli`
- Current version: 0.1.0

**Installation for Development:**
```bash
# Install from local directory as editable
uv tool install --reinstall .

# Or run without installing
uv run npm-cli proxy list
```

## Documentation Screenshots

**Demo Environment for Screenshots:**
The project includes demo setup scripts for taking documentation screenshots with fake data (no real domains/IPs exposed).

Demo scripts are created in the working directory when needed:
- `docker-compose.demo.yml` - Isolated NPM instance on ports 18080/18443/18181
- `scripts/setup-demo-simple.sh` - Automated setup with fake proxy hosts
- `scripts/teardown-demo.sh` - Complete cleanup
- `scripts/change-admin-password.py` - Programmatic password change via API

**Taking Screenshots:**
```bash
# Start demo instance and populate with fake data
docker compose -f docker-compose.demo.yml up -d
NPM_PASSWORD='demo1234' ./scripts/setup-demo-simple.sh

# Take screenshots
export NPM_API_URL='http://localhost:18181'
export NPM_USERNAME='admin@example.com'
export NPM_PASSWORD='demo1234'
uv run npm-cli proxy list  # Screenshot this output

# Clean up
./scripts/teardown-demo.sh
```

Screenshots are stored in `images/` directory and referenced in README.md with relative paths.

## Planning Context

This project uses the GSD (Get Shit Done) workflow with phases and plans in `.planning/`. All 7 phases are complete (Foundation, Connection & Auth, Proxy Host Management, SSL Certificate Automation, Configuration Templates, Testing & Documentation, Distribution). Package is published on PyPI. See `.planning/ROADMAP.md` for full history.
