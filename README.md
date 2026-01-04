# NPM CLI

**Command-line tool for managing Nginx Proxy Manager via API**

Transform multi-step manual operations (SQL queries, file editing, docker exec commands) into single-command workflows with validation and safety.

## Features

- **Proxy Host Management** - Create, list, update, and delete proxy hosts via NPM API
- **SSL Certificate Automation** - End-to-end workflow: certificate creation, NPM integration, and attachment to proxy hosts
- **Configuration Templates** - Reusable patterns for common scenarios:
  - Authentik forward authentication with SSO
  - API/webhook bypass for unauthenticated endpoints
  - VPN-only access restrictions
  - WebSocket protocol support
  - Combined Authentik + bypass patterns
- **Tab Completion** - ZSH autocomplete for commands, subcommands, and options
- **Docker Integration** - Automatic discovery and connection to NPM containers
- **Rich CLI Output** - Beautiful tables and formatted output using Rich

## Installation

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Running Nginx Proxy Manager instance

### Install with uv

```bash
# Install as a tool (recommended)
uv tool install npm-cli

# Or install in a virtual environment
uv pip install npm-cli
```

### Enable ZSH Completion

```bash
npm-cli --install-completion zsh
```

Restart your shell for completion to take effect. Tab completion will work for all commands and subcommands.

### Environment Setup

Configure connection to your NPM instance using environment variables:

```bash
export NPM_HOST=localhost        # NPM host (default: localhost)
export NPM_PORT=81              # NPM port (default: 81)
export NPM_EMAIL=admin@example.com  # NPM admin email
export NPM_PASSWORD=changeme    # NPM admin password
```

Or create a `.env` file in your project directory:

```env
NPM_HOST=localhost
NPM_PORT=81
NPM_EMAIL=admin@example.com
NPM_PASSWORD=changeme
```

Alternatively, use Docker auto-discovery (see Quick Start).

## Quick Start

### 1. Connect to NPM

If NPM is running in Docker, auto-discover the container:

```bash
npm-cli config connect
```

This will find your NPM container and save connection details.

### 2. Authenticate

```bash
npm-cli config auth
```

This caches an authentication token at `~/.config/npm-cli/token` (valid for 24-48 hours).

### 3. Check Status

```bash
npm-cli config status
```

Verify connection and authentication status.

### 4. List Proxy Hosts

```bash
npm-cli proxy list
```

View all configured proxy hosts in a formatted table.

## Usage Examples

### Proxy Host Management

**Create a new proxy host:**

```bash
npm-cli proxy create \
  --domain example.com \
  --forward-host 192.168.1.100 \
  --forward-port 8080
```

**List all proxy hosts:**

```bash
npm-cli proxy list
```

**Show proxy host details:**

```bash
# By domain name
npm-cli proxy show example.com

# Or by ID
npm-cli proxy show 42
```

**Update a proxy host:**

```bash
npm-cli proxy update example.com \
  --forward-port 8081 \
  --websockets-support
```

**Delete a proxy host:**

```bash
npm-cli proxy delete example.com
```

### SSL Certificate Management

**Create and attach a certificate:**

```bash
# Create certificate with HTTP-01 challenge
npm-cli cert create --domain example.com

# Attach to proxy host
npm-cli cert attach --domain example.com
```

**List certificates:**

```bash
npm-cli cert list
```

**Show certificate details:**

```bash
# By domain name
npm-cli cert show example.com

# Or by ID
npm-cli cert show 5
```

**Create certificate with DNS challenge:**

```bash
npm-cli cert create \
  --domain example.com \
  --provider cloudflare \
  --credentials '{"api_token": "your-token"}'
```

### Configuration Templates

Apply production-tested nginx configuration templates to proxy hosts.

**Authentik forward authentication:**

```bash
npm-cli proxy template apply <proxy-id> authentik \
  --backend http://app:3000
```

**API/webhook bypass (unauthenticated endpoints):**

```bash
npm-cli proxy template apply <proxy-id> api-bypass \
  --path "/api/" \
  --path "/webhook/" \
  --backend http://n8n:5678
```

**VPN-only access restrictions:**

```bash
npm-cli proxy template apply <proxy-id> vpn-only \
  --vpn-network 10.10.10.0/24 \
  --lan-network 192.168.7.0/24
```

**WebSocket support:**

```bash
npm-cli proxy template apply <proxy-id> websocket
```

**Combined Authentik + API bypass:**

```bash
npm-cli proxy template apply <proxy-id> authentik-bypass \
  --path "/api/" \
  --path "/webhook/" \
  --backend http://n8n:5678
```

**Auto-detect backend from proxy:**

```bash
# CLI auto-constructs backend URL from proxy's forward_host:forward_port
npm-cli proxy template apply <proxy-id> authentik
```

**Append to existing configuration:**

```bash
# Use --append to add template to existing advanced_config
npm-cli proxy template apply <proxy-id> websocket --append
```

## Template Reference

| Template | Description | Required Options |
|----------|-------------|------------------|
| `authentik` | Authentik forward auth with optional VPN/LAN restrictions | `--backend` (or auto-detect) |
| `api-bypass` | Unauthenticated bypass for API/webhook endpoints | `--path` (one or more), `--backend` |
| `vpn-only` | VPN and LAN network access restrictions | None (uses defaults) |
| `websocket` | WebSocket protocol upgrade headers | None |
| `authentik-bypass` | Combined Authentik auth + API bypass (most common) | `--path` (one or more), `--backend` |

**Optional parameters:**

- `--vpn-network` - VPN network CIDR (default: 10.10.10.0/24)
- `--lan-network` - LAN network CIDR (default: 192.168.7.0/24)
- `--vpn-only` - Include VPN/LAN restrictions (default: true for authentik-bypass)
- `--append` - Append template to existing advanced_config instead of replacing

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NPM_HOST` | NPM API host | `localhost` |
| `NPM_PORT` | NPM API port | `81` |
| `NPM_EMAIL` | NPM admin email | Required |
| `NPM_PASSWORD` | NPM admin password | Required |

### Token Caching

Authentication tokens are cached at `~/.config/npm-cli/token` and expire in 24-48 hours. Re-authenticate with:

```bash
npm-cli config auth
```

### Docker Auto-Discovery

The `config connect` command automatically discovers NPM containers using:

1. Container name pattern (`nginx-proxy-manager`, `npm`)
2. Container labels (`app=nginx-proxy-manager`)
3. Image name pattern (`jc21/nginx-proxy-manager`)

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/npm-cli.git
cd npm-cli

# Install dependencies
uv sync

# Run CLI in development
uv run npm-cli --help
```

### Run Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_proxy.py

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=src/npm_cli
```

### Linting and Formatting

```bash
# Check code with ruff
uv run ruff check src/

# Auto-fix issues
uv run ruff check src/ --fix

# Format code
uv run ruff format src/
```

### Publishing

**Building the package:**

```bash
# Build wheel and source distribution
uv build

# Verify package contents
tar -tzf dist/npm_cli-*.tar.gz
```

**Test local installation:**

```bash
# Create test environment
uv venv test-install

# Install from wheel
uv pip install dist/npm_cli-*.whl --python test-install/bin/python

# Test CLI
test-install/bin/npm-cli --help
test-install/bin/npm-cli version

# Clean up
rm -rf test-install
```

**Publish to PyPI:**

```bash
# Set PyPI token
export PYPI_TOKEN="pypi-..."

# Publish
uv publish

# Create release tag
git tag -a v0.1.0 -m "Release v0.1.0 - Initial public release"
git push origin v0.1.0
```

### Project Structure

```
npm-cli/
├── src/npm_cli/
│   ├── __main__.py          # CLI entry point, Typer app setup
│   ├── api/
│   │   └── models.py        # Pydantic models for NPM API
│   ├── cli/
│   │   ├── proxy.py         # Proxy host commands
│   │   ├── cert.py          # SSL certificate commands
│   │   └── config.py        # Configuration commands
│   ├── templates/
│   │   └── nginx.py         # Nginx configuration templates
│   └── settings.py          # Configuration management
├── tests/                   # Test suite
└── pyproject.toml          # Project metadata and dependencies
```

## Testing

### Test Strategy

The project uses a three-tier testing approach:

1. **Unit Tests** - Fast, isolated tests for template generation and model validation
2. **API Mocking** - Tests CLI commands with mocked HTTP responses using pytest-httpx
3. **Manual Integration** - End-to-end testing against a real NPM instance

### Running Tests

```bash
# Run unit tests (fast)
uv run pytest tests/test_templates.py

# Run CLI tests with API mocking
uv run pytest tests/test_cli_*.py

# Run all tests
uv run pytest
```

### Test Coverage

Current test suite includes:
- Template generation tests (16 test cases, 100% coverage)
- CLI command tests with mocked API responses
- Pydantic model validation tests
- Settings and configuration tests

## Architecture

### Core Technologies

- **Python 3.11+** - Modern type hints and performance improvements
- **uv** - Fast, reliable package management (10-100x faster than pip)
- **Typer** - Type-safe CLI framework with automatic help generation
- **Rich** - Beautiful terminal output with tables and formatting
- **Pydantic** - Data validation with strict models
- **httpx** - Modern async-capable HTTP client
- **docker-py** - Docker container discovery and management

### Design Principles

- **API-First** - Uses NPM API exclusively, no direct database access
- **Type Safety** - Comprehensive type hints with Pydantic validation
- **Error Handling** - Clear error messages with API response details
- **Production Safety** - Validation before applying changes
- **Minimal Dependencies** - Prefer stdlib where possible

### NPM API Integration

The NPM API is undocumented. This tool uses:
- Reverse-engineered API endpoints from NPM source code
- Strict Pydantic models with `extra="ignore"` for forward compatibility
- Comprehensive error handling for API changes

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Run linting and tests before committing
5. Submit a pull request with clear description

## Acknowledgments

- Built for managing [Nginx Proxy Manager](https://nginxproxymanager.com/)
- Inspired by production homelab automation needs
- Template patterns based on real-world configurations with Authentik SSO

---

**Made with ❤️ for the NPM community**
