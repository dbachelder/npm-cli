"""Integration setup tests for NPM container fixture."""

import os
import httpx


def test_npm_container_starts(npm_container):
    """Verify NPM container fixture starts and provides connection info.

    Tests that:
    - NPM_HOST environment variable is set
    - NPM_PORT environment variable is set
    - Container is reachable on port 81
    - NPM API responds on /api/schema endpoint
    """
    # Verify environment variables are set
    assert "NPM_HOST" in os.environ, "NPM_HOST environment variable not set"
    assert "NPM_PORT" in os.environ, "NPM_PORT environment variable not set"

    npm_host = os.environ["NPM_HOST"]
    npm_port = os.environ["NPM_PORT"]

    # Verify container is reachable
    npm_url = f"http://{npm_host}:{npm_port}/api/schema"
    response = httpx.get(npm_url, timeout=5.0)

    # NPM should respond (either 200 or auth-related status)
    assert response.status_code in [200, 401, 403], \
        f"Expected NPM to respond, got {response.status_code}"
