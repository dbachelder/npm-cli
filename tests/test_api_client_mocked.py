"""pytest-httpx mocking patterns for API client tests."""

import httpx
from npm_cli.api.client import NPMClient
from npm_cli.api.exceptions import NPMAPIError


def test_authenticate_success(httpx_mock):
    """Test successful authentication with mocked token response."""
    # Register mock response for POST /api/tokens
    httpx_mock.add_response(
        method="POST",
        url="http://npm-test:81/api/tokens",
        json={"token": "fake-jwt-token", "expires": "2026-12-31T23:59:59.000Z"}
    )

    client = NPMClient(base_url="http://npm-test:81")
    client.authenticate(username="admin@example.com", password="secret")

    # Verify token was saved (check by trying to use it)
    token = client._get_token()
    assert token == "fake-jwt-token", f"Expected token 'fake-jwt-token', got {token}"


def test_list_proxy_hosts_mocked(httpx_mock):
    """Test list proxy hosts with mocked response."""
    # Mock authentication
    httpx_mock.add_response(
        method="POST",
        url="http://npm-test:81/api/tokens",
        json={"token": "fake-jwt-token", "expires": "2026-12-31T23:59:59.000Z"}
    )

    # Mock GET /api/nginx/proxy-hosts
    httpx_mock.add_response(
        method="GET",
        url="http://npm-test:81/api/nginx/proxy-hosts",
        json=[
            {
                "id": 1,
                "created_on": "2026-01-01T00:00:00.000Z",
                "modified_on": "2026-01-01T00:00:00.000Z",
                "owner_user_id": 1,
                "domain_names": ["test.example.com"],
                "forward_scheme": "http",
                "forward_host": "backend",
                "forward_port": 8080,
                "access_list_id": 0,
                "certificate_id": 0,
                "ssl_forced": False,
                "hsts_enabled": False,
                "hsts_subdomains": False,
                "http2_support": False,
                "block_exploits": True,
                "caching_enabled": False,
                "allow_websocket_upgrade": False,
                "advanced_config": "",
                "enabled": True,
                "locations": [],
                "meta": {}
            }
        ]
    )

    client = NPMClient(base_url="http://npm-test:81")
    client.authenticate(username="admin@example.com", password="secret")

    proxies = client.list_proxy_hosts()

    assert len(proxies) == 1, f"Expected 1 proxy, got {len(proxies)}"
    assert proxies[0].id == 1, f"Expected proxy id 1, got {proxies[0].id}"
    assert "test.example.com" in proxies[0].domain_names, \
        f"Expected 'test.example.com' in domains, got {proxies[0].domain_names}"


def test_create_proxy_host_validation(httpx_mock):
    """Test create proxy host with 400 error validates NPMAPIError handling."""
    # Mock authentication
    httpx_mock.add_response(
        method="POST",
        url="http://npm-test:81/api/tokens",
        json={"token": "fake-jwt-token", "expires": "2026-12-31T23:59:59.000Z"}
    )

    # Mock POST /api/nginx/proxy-hosts with 400 error
    httpx_mock.add_response(
        method="POST",
        url="http://npm-test:81/api/nginx/proxy-hosts",
        status_code=400,
        json={"error": {"message": "Domain already exists"}}
    )

    from npm_cli.api.models import ProxyHostCreate

    client = NPMClient(base_url="http://npm-test:81")
    client.authenticate(username="admin@example.com", password="secret")

    host = ProxyHostCreate(
        domain_names=["test.example.com"],
        forward_scheme="http",
        forward_host="backend",
        forward_port=8080
    )

    # Should raise NPMAPIError with response details
    try:
        client.create_proxy_host(host)
        assert False, "Expected NPMAPIError to be raised"
    except NPMAPIError as e:
        assert "400" in str(e), f"Expected '400' in error message, got: {e}"
        assert e.response is not None, "Expected response to be preserved in exception"
