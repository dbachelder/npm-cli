"""Pytest configuration and fixtures."""

import os
import pytest


@pytest.fixture(scope="module")
def npm_container(request):
    """Module-scoped NPM container fixture.

    NOTE: This fixture demonstrates the testcontainers pattern but is currently
    marked for skip in test_integration_setup.py due to NPM container requiring
    MySQL/MariaDB database setup. See .planning/ISSUES.md for details.

    For actual NPM integration testing, use the production NPM instance or
    implement a docker-compose setup with MySQL container.

    This fixture is kept to show the pattern for future implementation.
    """
    pytest.skip(
        "NPM container requires database setup - see .planning/ISSUES.md. "
        "Use CliRunner tests (test_cli_integration.py) and HTTP mocking "
        "(test_api_client_mocked.py) for testing patterns."
    )
