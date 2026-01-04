"""Proxy host management commands."""

from typing import Literal

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from npm_cli.api.client import NPMClient
from npm_cli.api.models import ProxyHostCreate, ProxyHostUpdate
from npm_cli.api.exceptions import NPMAPIError, NPMConnectionError, NPMValidationError
from npm_cli.config.settings import NPMSettings
from npm_cli.templates.nginx import (
    authentik_forward_auth,
    api_webhook_bypass,
    vpn_only_access,
    websocket_support,
    authentik_with_bypass,
)

app = typer.Typer(help="Manage proxy hosts")
console = Console()


@app.command("list")
def list_proxy_hosts() -> None:
    """List all proxy hosts."""
    try:
        # Load settings
        settings = NPMSettings()

        # Create client and authenticate
        client = NPMClient(base_url=str(settings.api_url), timeout=30.0)

        # Authenticate if token expired
        if settings.username and settings.password:
            try:
                client.authenticate(settings.username, settings.password)
            except RuntimeError:
                # Token already valid
                pass

        # Fetch proxy hosts
        hosts = client.list_proxy_hosts()

        if not hosts:
            console.print("[yellow]No proxy hosts found[/]")
            return

        # Create Rich table
        table = Table(title="Proxy Hosts", show_lines=True)
        table.add_column("ID", style="cyan", width=6)
        table.add_column("Domains", style="green")
        table.add_column("Forward To", style="yellow")
        table.add_column("SSL", style="magenta", width=8)
        table.add_column("Status", style="blue", width=10)

        for host in hosts:
            domains = "\n".join(host.domain_names)
            forward = f"{host.forward_scheme}://{host.forward_host}:{host.forward_port}"
            ssl = "✓" if host.certificate_id else "✗"
            status = "[green]Enabled[/]" if host.enabled else "[red]Disabled[/]"

            table.add_row(str(host.id), domains, forward, ssl, status)

        console.print(table)

    except NPMConnectionError as e:
        console.print(f"[bold red]Connection Error:[/] {e}")
        console.print("[dim]Is the NPM container running?[/]")
        raise typer.Exit(1)
    except NPMAPIError as e:
        console.print(f"[bold red]API Error:[/] {e}")
        if e.response:
            console.print(f"[dim]Status:[/] {e.response.status_code}")
            console.print(f"[dim]Response:[/] {e.response.text[:200]}")
        raise typer.Exit(1)
    except NPMValidationError as e:
        console.print(f"[bold red]Validation Error:[/] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)


@app.command("create")
def create_proxy_host(
    domain: str = typer.Argument(..., help="Domain name (e.g., app.example.com)"),
    forward_host: str = typer.Option(..., "--host", "-h", help="Backend hostname/IP"),
    forward_port: int = typer.Option(..., "--port", "-p", help="Backend port"),
    forward_scheme: Literal["http", "https"] = typer.Option("http", "--scheme", "-s", help="Backend protocol"),
    certificate: int | None = typer.Option(None, "--certificate", "-c", help="Attach SSL certificate by ID"),
    ssl: bool = typer.Option(False, "--ssl", help="Force HTTPS redirect (requires --certificate)"),
    websocket: bool = typer.Option(False, "--websocket", "-w", help="Allow WebSocket upgrade"),
    http2: bool = typer.Option(True, "--http2", help="Enable HTTP/2 support"),
) -> None:
    """Create a new proxy host."""
    try:
        # Validate SSL options
        if ssl and not certificate:
            console.print("[bold red]Error:[/] --ssl requires --certificate to be set")
            console.print("[dim]You cannot force HTTPS redirect without a certificate attached[/]")
            raise typer.Exit(1)

        # Load settings
        settings = NPMSettings()

        # Create proxy host data
        host_data = ProxyHostCreate(
            domain_names=[domain],
            forward_scheme=forward_scheme,
            forward_host=forward_host,
            forward_port=forward_port,
            certificate_id=certificate,
            ssl_forced=ssl,
            allow_websocket_upgrade=websocket,
            http2_support=http2,
        )

        # Create client and authenticate
        client = NPMClient(base_url=str(settings.api_url), timeout=30.0)
        if settings.username and settings.password:
            try:
                client.authenticate(settings.username, settings.password)
            except RuntimeError:
                pass

        # Create proxy host
        result = client.create_proxy_host(host_data)

        # Print success
        console.print(f"[green]✓[/] Created proxy host [cyan]{result.id}[/]")
        console.print(f"  Domain: {domain}")
        console.print(f"  Forward: {forward_scheme}://{forward_host}:{forward_port}")
        if certificate:
            console.print(f"  Certificate: ID {certificate}")
        console.print(f"  SSL Forced: {'Yes' if ssl else 'No'}")
        console.print(f"  WebSocket: {'Enabled' if websocket else 'Disabled'}")

    except NPMConnectionError as e:
        console.print(f"[bold red]Connection Error:[/] {e}")
        console.print("[dim]Is the NPM container running?[/]")
        raise typer.Exit(1)
    except NPMAPIError as e:
        console.print(f"[bold red]API Error:[/] {e}")
        if e.response:
            console.print(f"[dim]Status:[/] {e.response.status_code}")
            console.print(f"[dim]Response:[/] {e.response.text[:200]}")
        raise typer.Exit(1)
    except NPMValidationError as e:
        console.print(f"[bold red]Validation Error:[/] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)


@app.command("show")
def show_proxy_host(
    identifier: str = typer.Argument(..., help="Proxy host ID or domain name")
) -> None:
    """Show detailed proxy host information."""
    try:
        # Load settings
        settings = NPMSettings()

        # Create client and authenticate
        client = NPMClient(base_url=str(settings.api_url), timeout=30.0)
        if settings.username and settings.password:
            try:
                client.authenticate(settings.username, settings.password)
            except RuntimeError:
                pass

        # Determine if identifier is ID or domain name
        if identifier.isdigit():
            # It's an ID
            host = client.get_proxy_host(int(identifier))
        else:
            # It's a domain name - search for it
            all_hosts = client.list_proxy_hosts()
            matching_hosts = [h for h in all_hosts if identifier in h.domain_names]

            if not matching_hosts:
                console.print(f"[bold red]Error:[/] No proxy host found with domain '{identifier}'")
                raise typer.Exit(1)
            elif len(matching_hosts) > 1:
                console.print(f"[yellow]Warning:[/] Multiple hosts match domain '{identifier}':")
                for h in matching_hosts:
                    console.print(f"  ID {h.id}: {', '.join(h.domain_names)}")
                console.print("\nUsing the first match. Use ID for specific host.")

            host = matching_hosts[0]

        # Create formatted output
        details = f"""[bold]ID:[/] {host.id}
[bold]Domains:[/]
  {chr(10).join(f'  • {d}' for d in host.domain_names)}

[bold]Forward Configuration:[/]
  Scheme: {host.forward_scheme}
  Host: {host.forward_host}
  Port: {host.forward_port}

[bold]SSL/Security:[/]
  Certificate ID: {host.certificate_id if host.certificate_id else 'None'}
  SSL Forced: {'Yes' if host.ssl_forced else 'No'}
  HSTS Enabled: {'Yes' if host.hsts_enabled else 'No'}
  HSTS Subdomains: {'Yes' if host.hsts_subdomains else 'No'}
  HTTP/2 Support: {'Yes' if host.http2_support else 'No'}
  Block Exploits: {'Yes' if host.block_exploits else 'No'}

[bold]Features:[/]
  Caching: {'Enabled' if host.caching_enabled else 'Disabled'}
  WebSocket: {'Enabled' if host.allow_websocket_upgrade else 'Disabled'}
  Access List ID: {host.access_list_id if host.access_list_id else 'None'}

[bold]Status:[/]
  Enabled: {'Yes' if host.enabled else 'No'}
  Created: {host.created_on}
  Modified: {host.modified_on}
  Owner User ID: {host.owner_user_id}"""

        if host.advanced_config:
            details += f"\n\n[bold]Advanced Config:[/]\n{host.advanced_config}"

        panel = Panel(details, title=f"Proxy Host {host.id}", border_style="cyan")
        console.print(panel)

    except NPMConnectionError as e:
        console.print(f"[bold red]Connection Error:[/] {e}")
        console.print("[dim]Is the NPM container running?[/]")
        raise typer.Exit(1)
    except NPMAPIError as e:
        console.print(f"[bold red]API Error:[/] {e}")
        if e.response:
            console.print(f"[dim]Status:[/] {e.response.status_code}")
            console.print(f"[dim]Response:[/] {e.response.text[:200]}")
        raise typer.Exit(1)
    except NPMValidationError as e:
        console.print(f"[bold red]Validation Error:[/] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)


@app.command("update")
def update_proxy_host(
    host_id: int = typer.Argument(..., help="Proxy host ID"),
    domain: list[str] = typer.Option(None, "--domain", "-d", help="Domain names (repeat for multiple)"),
    forward_host: str = typer.Option(None, "--host", "-h", help="Backend hostname/IP"),
    forward_port: int = typer.Option(None, "--port", "-p", help="Backend port"),
    forward_scheme: Literal["http", "https"] = typer.Option(None, "--scheme", "-s", help="Backend protocol"),
    certificate: int | None = typer.Option(None, "--certificate", "-c", help="Attach SSL certificate by ID"),
    ssl: bool | None = typer.Option(None, "--ssl/--no-ssl", help="Enable/disable HTTPS redirect"),
    enabled: bool = typer.Option(None, "--enabled/--disabled", help="Enable or disable proxy host"),
) -> None:
    """Update proxy host configuration."""
    try:
        # Build update object with only provided fields
        update_data = {}

        if domain is not None:
            update_data["domain_names"] = domain
        if forward_host is not None:
            update_data["forward_host"] = forward_host
        if forward_port is not None:
            update_data["forward_port"] = forward_port
        if forward_scheme is not None:
            update_data["forward_scheme"] = forward_scheme
        if certificate is not None:
            update_data["certificate_id"] = certificate
        if ssl is not None:
            update_data["ssl_forced"] = ssl
        if enabled is not None:
            update_data["enabled"] = enabled

        if not update_data:
            console.print("[yellow]No updates specified[/]")
            raise typer.Exit(0)

        updates = ProxyHostUpdate(**update_data)

        # Load settings
        settings = NPMSettings()

        # Create client and authenticate
        client = NPMClient(base_url=str(settings.api_url), timeout=30.0)
        if settings.username and settings.password:
            try:
                client.authenticate(settings.username, settings.password)
            except RuntimeError:
                pass

        # Update proxy host
        client.update_proxy_host(host_id, updates)

        # Print success with field summary
        console.print(f"[green]✓[/] Updated proxy host [cyan]{host_id}[/]")
        console.print("\nUpdated fields:")
        for field, value in update_data.items():
            console.print(f"  {field}: {value}")

    except NPMConnectionError as e:
        console.print(f"[bold red]Connection Error:[/] {e}")
        console.print("[dim]Is the NPM container running?[/]")
        raise typer.Exit(1)
    except NPMAPIError as e:
        console.print(f"[bold red]API Error:[/] {e}")
        if e.response:
            console.print(f"[dim]Status:[/] {e.response.status_code}")
            console.print(f"[dim]Response:[/] {e.response.text[:200]}")
        raise typer.Exit(1)
    except NPMValidationError as e:
        console.print(f"[bold red]Validation Error:[/] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)


@app.command("delete")
def delete_proxy_host(
    host_id: int = typer.Argument(..., help="Proxy host ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a proxy host."""
    try:
        # Confirm deletion
        if not yes:
            typer.confirm(f"Delete proxy host {host_id}?", abort=True)

        # Load settings
        settings = NPMSettings()

        # Create client and authenticate
        client = NPMClient(base_url=str(settings.api_url), timeout=30.0)
        if settings.username and settings.password:
            try:
                client.authenticate(settings.username, settings.password)
            except RuntimeError:
                pass

        # Delete proxy host
        client.delete_proxy_host(host_id)

        console.print(f"[green]✓[/] Deleted proxy host [cyan]{host_id}[/]")

    except typer.Abort:
        console.print("[yellow]Cancelled[/]")
        raise typer.Exit(0)
    except NPMConnectionError as e:
        console.print(f"[bold red]Connection Error:[/] {e}")
        console.print("[dim]Is the NPM container running?[/]")
        raise typer.Exit(1)
    except NPMAPIError as e:
        console.print(f"[bold red]API Error:[/] {e}")
        if e.response:
            console.print(f"[dim]Status:[/] {e.response.status_code}")
            console.print(f"[dim]Response:[/] {e.response.text[:200]}")
        raise typer.Exit(1)
    except NPMValidationError as e:
        console.print(f"[bold red]Validation Error:[/] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)


@app.command("template")
def apply_template(
    host_id: int = typer.Argument(..., help="Proxy host ID to apply template to"),
    template_name: Literal["authentik", "api-bypass", "vpn-only", "websocket", "authentik-bypass"] = typer.Argument(..., help="Template to apply"),
    backend: str = typer.Option(None, "--backend", "-b", help="Backend URL (e.g., http://app:8000)"),
    paths: list[str] = typer.Option(None, "--path", "-p", help="Paths for api-bypass template (repeat for multiple)"),
    vpn_network: str = typer.Option("10.10.10.0/24", "--vpn-network", help="VPN network CIDR"),
    lan_network: str = typer.Option("192.168.7.0/24", "--lan-network", help="LAN network CIDR"),
    append: bool = typer.Option(False, "--append", "-a", help="Append to existing advanced_config instead of replacing"),
) -> None:
    """Apply nginx configuration template to proxy host."""
    try:
        # Load settings
        settings = NPMSettings()

        # Create client and authenticate
        client = NPMClient(base_url=str(settings.api_url), timeout=30.0)
        if settings.username and settings.password:
            try:
                client.authenticate(settings.username, settings.password)
            except RuntimeError:
                pass

        # Fetch existing proxy host
        host = client.get_proxy_host(host_id)

        # Determine backend URL
        if backend is None:
            backend = f"{host.forward_scheme}://{host.forward_host}:{host.forward_port}"

        # Validate required options and generate template config
        template_config = ""

        if template_name == "authentik":
            # Authentik requires backend
            template_config = authentik_forward_auth(
                backend=backend,
                vpn_only=False,  # Can be enhanced later
                vpn_network=vpn_network,
                lan_network=lan_network
            )

        elif template_name == "api-bypass":
            # API bypass requires paths
            if not paths:
                console.print("[bold red]Error:[/] --path is required for api-bypass template")
                console.print("[dim]Example: npm-cli proxy template 7 api-bypass --path /api/ --path /webhook/[/]")
                raise typer.Exit(1)

            template_config = api_webhook_bypass(backend=backend, paths=list(paths))

        elif template_name == "authentik-bypass":
            # Combined Authentik + API bypass requires paths
            if not paths:
                console.print("[bold red]Error:[/] --path is required for authentik-bypass template")
                console.print("[dim]Example: npm-cli proxy template 7 authentik-bypass --path /api/ --path /webhook/[/]")
                raise typer.Exit(1)

            template_config = authentik_with_bypass(
                backend=backend,
                bypass_paths=list(paths),
                vpn_only=True,  # Default to VPN restrictions for security
                vpn_network=vpn_network,
                lan_network=lan_network
            )

        elif template_name == "vpn-only":
            template_config = vpn_only_access(
                vpn_network=vpn_network,
                lan_network=lan_network
            )

        elif template_name == "websocket":
            template_config = websocket_support()

        # Apply template (append or replace)
        if append and host.advanced_config:
            new_config = f"{host.advanced_config}\n\n{template_config}"
        else:
            new_config = template_config

        # Update proxy host with new advanced_config
        client.update_proxy_host(
            host_id=host_id,
            updates=ProxyHostUpdate(advanced_config=new_config)
        )

        # Print success with preview
        console.print(f"[green]✓[/] Applied [cyan]{template_name}[/] template to proxy host [cyan]{host_id}[/]")
        console.print("\n[bold]Template preview (first 5 lines):[/]")

        preview_lines = template_config.split("\n")[:5]
        for line in preview_lines:
            console.print(f"  {line}")

        config_lines = template_config.split("\n")
        if len(config_lines) > 5:
            remaining = len(config_lines) - 5
            console.print(f"  [dim]... ({remaining} more lines)[/]")

        console.print(f"\n[dim]View full config: npm-cli proxy show {host_id}[/]")

    except NPMConnectionError as e:
        console.print(f"[bold red]Connection Error:[/] {e}")
        console.print("[dim]Is the NPM container running?[/]")
        raise typer.Exit(1)
    except NPMAPIError as e:
        console.print(f"[bold red]API Error:[/] {e}")
        if e.response:
            console.print(f"[dim]Status:[/] {e.response.status_code}")
            console.print(f"[dim]Response:[/] {e.response.text[:200]}")
        raise typer.Exit(1)
    except NPMValidationError as e:
        console.print(f"[bold red]Validation Error:[/] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)
