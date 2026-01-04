"""Nginx configuration templates for common NPM proxy patterns.

Production-tested templates for Authentik forward auth, API/webhook bypass,
VPN-only access, and WebSocket support.
"""


def authentik_forward_auth(
    backend: str,
    vpn_only: bool = False,
    vpn_network: str = "10.10.10.0/24",
    lan_network: str = "192.168.7.0/24"
) -> str:
    """Generate Authentik forward auth configuration with optional network restrictions.

    Args:
        backend: Backend URL (e.g., "http://app:8000")
        vpn_only: Include VPN/LAN network restrictions in main location block
        vpn_network: VPN network CIDR (default: 10.10.10.0/24 for WireGuard)
        lan_network: LAN network CIDR (default: 192.168.7.0/24)

    Returns:
        Nginx configuration with Authentik outpost and auth_request directives
    """
    network_acl = ""
    if vpn_only:
        network_acl = f"""    # VPN and local network only
    allow {vpn_network};    # WireGuard VPN network
    allow {lan_network};   # Local LAN
    deny all;

"""

    return f"""# ---- Authentik forward auth outpost ----
location /outpost.goauthentik.io {{
    internal;
    proxy_pass http://authentik-server:9000/outpost.goauthentik.io;
    proxy_set_header Host $host;
    proxy_set_header X-Original-URL $scheme://$http_host$request_uri;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Content-Length "";
    proxy_pass_request_body off;
}}

# ---- Protect the main app with Authentik ----
location / {{
{network_acl}    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    auth_request /outpost.goauthentik.io/auth;
    auth_request_set $auth_cookie $upstream_http_set_cookie;
    add_header Set-Cookie $auth_cookie;

    # Preserve auth headers
    auth_request_set $authentik_username $upstream_http_x_authentik_username;
    auth_request_set $authentik_groups $upstream_http_x_authentik_groups;
    proxy_set_header X-authentik-username $authentik_username;
    proxy_set_header X-authentik-groups $authentik_groups;

    proxy_pass {backend};
}}"""


def api_webhook_bypass(backend: str, paths: list[str]) -> str:
    """Generate unauthenticated bypass location blocks for API/webhook endpoints.

    Args:
        backend: Backend URL (e.g., "http://n8n:5678")
        paths: List of paths to bypass auth (e.g., ["/api/", "/webhook/"])
                Can include regex patterns (e.g., ["~ ^/webhook(-test)?/"])

    Returns:
        Nginx configuration with location blocks for each bypass path
    """
    location_blocks = []

    for path in paths:
        location_blocks.append(f"""# Unauthenticated endpoint
location {path} {{
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    proxy_pass {backend};
}}""")

    return "\n\n".join(location_blocks)


def vpn_only_access(
    vpn_network: str = "10.10.10.0/24",
    lan_network: str = "192.168.7.0/24"
) -> str:
    """Generate VPN and LAN network access restrictions.

    Inline snippet (not wrapped in location block) for insertion into any location.

    Args:
        vpn_network: VPN network CIDR (default: 10.10.10.0/24 for WireGuard)
        lan_network: LAN network CIDR (default: 192.168.7.0/24)

    Returns:
        Nginx allow/deny directives for network access control
    """
    return f"""allow {vpn_network};    # WireGuard VPN network
allow {lan_network};   # Local LAN
deny all;"""


def websocket_support() -> str:
    """Generate WebSocket upgrade headers.

    Inline snippet for inserting into location blocks that need WebSocket support.

    Returns:
        Nginx proxy headers for WebSocket protocol upgrade
    """
    return """proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";"""


def authentik_with_bypass(
    backend: str,
    bypass_paths: list[str],
    vpn_only: bool = True,
    vpn_network: str = "10.10.10.0/24",
    lan_network: str = "192.168.7.0/24"
) -> str:
    """Generate combined Authentik auth + API/webhook bypass configuration.

    Most common production pattern: unauthenticated API/webhook endpoints
    with Authentik-protected main application and VPN/LAN restrictions.

    Based on production n8n proxy (ID 7) with webhook/API bypass + Authentik auth.

    Args:
        backend: Backend URL (e.g., "http://n8n:5678")
        bypass_paths: Paths to bypass auth (e.g., ["/api/", "/webhook/"])
        vpn_only: Include VPN/LAN network restrictions (default: True)
        vpn_network: VPN network CIDR (default: 10.10.10.0/24 for WireGuard)
        lan_network: LAN network CIDR (default: 192.168.7.0/24)

    Returns:
        Nginx configuration with bypass locations, Authentik outpost, and protected root
    """
    # Generate bypass location blocks (unauthenticated)
    bypass_config = api_webhook_bypass(backend=backend, paths=bypass_paths)

    # Generate Authentik forward auth config (with VPN restrictions)
    auth_config = authentik_forward_auth(
        backend=backend,
        vpn_only=vpn_only,
        vpn_network=vpn_network,
        lan_network=lan_network
    )

    # Combine in correct order: bypass paths first, then Authentik protection
    return f"""{bypass_config}

{auth_config}"""
