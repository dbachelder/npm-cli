"""Integration setup tests for NPM container fixture.

NOTE: NPM container tests are currently skipped because NPM requires MySQL/MariaDB
database setup which adds significant complexity. The testcontainers dependency and
fixture pattern are demonstrated but not actively used.

For actual integration testing:
1. Use CliRunner tests (test_cli_integration.py) for CLI commands
2. Use pytest-httpx mocking (test_api_client_mocked.py) for API client
3. Manually test against production NPM instance for end-to-end workflows

See .planning/ISSUES.md for details on implementing full container integration.
"""

import pytest


@pytest.mark.skip(reason="NPM container requires MySQL/MariaDB - see .planning/ISSUES.md")
def test_npm_container_starts(npm_container):
    """Verify NPM container fixture starts and provides connection info.

    This test demonstrates the testcontainers pattern but is skipped because
    NPM requires database setup.

    Would test:
    - NPM_HOST environment variable is set
    - NPM_PORT environment variable is set
    - Container is reachable on port 81
    - NPM API responds on /api/schema endpoint
    """
    pass  # Test body removed since fixture is skipped
