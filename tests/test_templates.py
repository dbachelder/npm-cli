"""Tests for nginx configuration templates."""

import pytest

from npm_cli.templates.nginx import (
    authentik_forward_auth,
    api_webhook_bypass,
    vpn_only_access,
    websocket_support,
    authentik_with_bypass,
)


class TestAuthentikForwardAuth:
    """Tests for Authentik forward auth template."""

    def test_basic_authentik_config(self):
        """Test basic Authentik forward auth without VPN restrictions."""
        config = authentik_forward_auth(backend="http://app:8000", vpn_only=False)

        # Verify outpost location block
        assert "location /outpost.goauthentik.io" in config
        assert "internal;" in config
        assert "proxy_pass http://authentik-server:9000/outpost.goauthentik.io" in config

        # Verify main location block with auth_request
        assert "location /" in config
        assert "auth_request /outpost.goauthentik.io/auth" in config
        assert "proxy_pass http://app:8000" in config

        # Verify auth headers preservation
        assert "auth_request_set $auth_cookie $upstream_http_set_cookie" in config
        assert "auth_request_set $authentik_username $upstream_http_x_authentik_username" in config
        assert "proxy_set_header X-authentik-username $authentik_username" in config

        # Should NOT have network restrictions
        assert "allow 10.10.10.0/24" not in config
        assert "deny all" not in config

    def test_authentik_with_vpn_only(self):
        """Test Authentik forward auth with VPN network restrictions."""
        config = authentik_forward_auth(
            backend="http://app:8000",
            vpn_only=True,
            vpn_network="10.10.10.0/24",
            lan_network="192.168.7.0/24"
        )

        # Should have network restrictions in main location block
        assert "allow 10.10.10.0/24" in config
        assert "allow 192.168.7.0/24" in config
        assert "deny all" in config

    def test_authentik_custom_networks(self):
        """Test Authentik with custom network CIDRs."""
        config = authentik_forward_auth(
            backend="http://custom:9999",
            vpn_only=True,
            vpn_network="172.16.0.0/16",
            lan_network="10.0.0.0/24"
        )

        assert "allow 172.16.0.0/16" in config
        assert "allow 10.0.0.0/24" in config
        assert "proxy_pass http://custom:9999" in config


class TestApiWebhookBypass:
    """Tests for API/webhook bypass template."""

    def test_single_bypass_path(self):
        """Test bypass template with single path."""
        config = api_webhook_bypass(
            backend="http://app:8000",
            paths=["/api/"]
        )

        assert "location /api/" in config
        assert "proxy_pass http://app:8000" in config

        # WebSocket headers should be included
        assert "proxy_http_version 1.1" in config
        assert 'proxy_set_header Upgrade $http_upgrade' in config
        assert 'proxy_set_header Connection "upgrade"' in config

    def test_multiple_bypass_paths(self):
        """Test bypass template with multiple paths."""
        config = api_webhook_bypass(
            backend="http://n8n:5678",
            paths=["/api/", "/webhook/", "/webhook-test/"]
        )

        # Each path should have its own location block
        assert "location /api/" in config
        assert "location /webhook/" in config
        assert "location /webhook-test/" in config

        # Each should proxy to the same backend
        assert config.count("proxy_pass http://n8n:5678") == 3

    def test_regex_path_pattern(self):
        """Test bypass template with regex path pattern."""
        config = api_webhook_bypass(
            backend="http://n8n:5678",
            paths=["~ ^/webhook(-test)?/"]
        )

        assert "location ~ ^/webhook(-test)?/" in config
        assert "proxy_pass http://n8n:5678" in config


class TestVpnOnlyAccess:
    """Tests for VPN-only network access template."""

    def test_default_networks(self):
        """Test VPN-only with default network CIDRs."""
        config = vpn_only_access()

        assert "allow 10.10.10.0/24" in config
        assert "allow 192.168.7.0/24" in config
        assert "deny all" in config

    def test_custom_networks(self):
        """Test VPN-only with custom network CIDRs."""
        config = vpn_only_access(
            vpn_network="172.16.0.0/16",
            lan_network="10.0.0.0/8"
        )

        assert "allow 172.16.0.0/16" in config
        assert "allow 10.0.0.0/8" in config
        assert "deny all" in config

    def test_inline_snippet(self):
        """Test that VPN-only returns inline snippet (no location wrapper)."""
        config = vpn_only_access()

        # Should NOT have location block wrapper
        assert "location" not in config.lower()


class TestWebSocketSupport:
    """Tests for WebSocket support template."""

    def test_websocket_headers(self):
        """Test WebSocket upgrade headers."""
        config = websocket_support()

        assert "proxy_http_version 1.1" in config
        assert 'proxy_set_header Upgrade $http_upgrade' in config
        assert 'proxy_set_header Connection "upgrade"' in config

    def test_inline_snippet(self):
        """Test that WebSocket returns inline snippet (no location wrapper)."""
        config = websocket_support()

        # Should NOT have location block wrapper
        assert "location" not in config.lower()


class TestAuthentikWithBypass:
    """Tests for combined Authentik + API bypass template."""

    def test_combined_template_structure(self):
        """Test combined template has all required components."""
        config = authentik_with_bypass(
            backend="http://n8n:5678",
            bypass_paths=["/api/", "/webhook/"],
            vpn_only=True
        )

        # Should have bypass location blocks (unauthenticated)
        assert "location /api/" in config
        assert "location /webhook/" in config

        # Should have Authentik outpost location
        assert "location /outpost.goauthentik.io" in config
        assert "internal;" in config

        # Should have main location with auth_request
        assert "location /" in config
        assert "auth_request /outpost.goauthentik.io/auth" in config

        # All should proxy to same backend
        assert config.count("proxy_pass http://n8n:5678") == 3

    def test_combined_with_vpn_restrictions(self):
        """Test combined template includes network ACLs when vpn_only=True."""
        config = authentik_with_bypass(
            backend="http://app:8000",
            bypass_paths=["/api/"],
            vpn_only=True,
            vpn_network="10.10.10.0/24",
            lan_network="192.168.7.0/24"
        )

        # VPN restrictions should be in main location block (not bypass paths)
        assert "allow 10.10.10.0/24" in config
        assert "allow 192.168.7.0/24" in config
        assert "deny all" in config

    def test_combined_without_vpn_restrictions(self):
        """Test combined template without network ACLs."""
        config = authentik_with_bypass(
            backend="http://app:8000",
            bypass_paths=["/webhook/"],
            vpn_only=False
        )

        # Should NOT have network restrictions
        assert "allow 10.10.10.0/24" not in config
        assert "deny all" not in config

        # But should still have all other components
        assert "location /webhook/" in config
        assert "location /outpost.goauthentik.io" in config
        assert "auth_request /outpost.goauthentik.io/auth" in config

    def test_combined_with_multiple_bypass_paths(self):
        """Test combined template with multiple bypass paths."""
        config = authentik_with_bypass(
            backend="http://n8n:5678",
            bypass_paths=["/api/", "/webhook/", "/webhook-test/"]
        )

        # Each bypass path should have its own location block
        assert "location /api/" in config
        assert "location /webhook/" in config
        assert "location /webhook-test/" in config

        # Plus Authentik locations
        assert "location /outpost.goauthentik.io" in config
        assert "location /" in config

    def test_production_n8n_pattern(self):
        """Test template matches production n8n proxy pattern."""
        config = authentik_with_bypass(
            backend="http://n8n:5678",
            bypass_paths=["~ ^/webhook(-test)?/", "/api/"],
            vpn_only=True,
            vpn_network="10.10.10.0/24",
            lan_network="192.168.7.0/24"
        )

        # Regex webhook pattern
        assert "location ~ ^/webhook(-test)?/" in config

        # Standard API bypass
        assert "location /api/" in config

        # Authentik protection with VPN restrictions
        assert "location /outpost.goauthentik.io" in config
        assert "auth_request /outpost.goauthentik.io/auth" in config
        assert "allow 10.10.10.0/24" in config
        assert "allow 192.168.7.0/24" in config
        assert "deny all" in config
