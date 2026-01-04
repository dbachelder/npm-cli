"""SSL certificate management commands."""

from datetime import datetime, timezone

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from npm_cli.api.client import NPMClient
from npm_cli.api.models import CertificateCreate
from npm_cli.api.exceptions import NPMAPIError, NPMConnectionError, NPMValidationError
from npm_cli.config.settings import NPMSettings

app = typer.Typer(help="Manage SSL certificates")
console = Console()


@app.command("list")
def list_certificates() -> None:
    """List all SSL certificates with expiration status."""
    try:
        # Load settings
        settings = NPMSettings()

        # Create client and authenticate
        client = NPMClient(base_url=str(settings.api_url), timeout=30.0)
        if settings.username and settings.password:
            try:
                client.authenticate(settings.username, settings.password)
            except RuntimeError:
                # Token already valid
                pass

        # Fetch certificates
        certs = client.certificate_list()

        if not certs:
            console.print("[yellow]No certificates found[/]")
            return

        # Create Rich table
        table = Table(title="SSL Certificates", show_lines=True)
        table.add_column("ID", style="cyan", width=6)
        table.add_column("Domains", style="green")
        table.add_column("Provider", style="yellow", width=12)
        table.add_column("Expires", style="magenta")
        table.add_column("Days Left", style="blue", width=10)
        table.add_column("Status", width=15)

        for cert in certs:
            domains = "\n".join(cert.domain_names)
            provider = cert.provider or "letsencrypt"

            # Parse expiration date
            if cert.expires_on:
                # Parse ISO 8601 timestamp
                expires = datetime.fromisoformat(cert.expires_on.replace("Z", "+00:00"))
                expires_str = expires.strftime("%Y-%m-%d")

                # Calculate days left
                now = datetime.now(timezone.utc)
                days_left = (expires - now).days
                days_left_str = str(days_left)

                # Color-code status
                if days_left < 7:
                    status = "[red]⚠️  EXPIRING SOON[/]"
                elif days_left < 30:
                    status = "[yellow]⚠️  EXPIRING SOON[/]"
                else:
                    status = "[green]✓ Valid[/]"
            else:
                expires_str = "Unknown"
                days_left_str = "N/A"
                status = "[dim]Unknown[/]"

            table.add_row(
                str(cert.id),
                domains,
                provider,
                expires_str,
                days_left_str,
                status
            )

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
def create_certificate(
    domain: list[str] = typer.Option(..., "--domain", "-d", help="Domain names (first is primary, rest are SANs)"),
    email: str = typer.Option(..., "--email", "-e", help="Let's Encrypt registration email"),
    name: str | None = typer.Option(None, "--name", "-n", help="Human-readable certificate name"),
    dns_provider: str | None = typer.Option(None, "--dns-provider", help="DNS provider for DNS-01 challenge (cloudflare, route53, etc.)"),
    dns_credentials: str | None = typer.Option(None, "--dns-credentials", help="DNS provider credentials (format: 'key=value')"),
    propagation_seconds: int = typer.Option(30, help="DNS propagation delay for DNS-01 challenges"),
) -> None:
    """Create new Let's Encrypt certificate."""
    try:
        # Build meta dict
        # NOTE: NPM GUI creates certificates with empty meta {}.
        # Email and agreement are stored at account level, not in certificate meta.
        # For DNS challenges, meta contains dns_challenge, dns_provider, credentials.
        meta = {}
        if dns_provider:
            meta["dns_challenge"] = True
            meta["dns_provider"] = dns_provider
            meta["letsencrypt_email"] = email  # Only for DNS challenges
            meta["letsencrypt_agree"] = True
        if dns_credentials:
            meta["dns_provider_credentials"] = dns_credentials
        if propagation_seconds != 30:
            meta["propagation_seconds"] = propagation_seconds

        # Build certificate creation data
        cert_data = CertificateCreate(
            provider="letsencrypt",
            nice_name=name or f"Certificate for {domain[0]}",
            domain_names=domain,
            meta=meta,
        )

        # Load settings
        settings = NPMSettings()

        # Create client and authenticate
        client = NPMClient(base_url=str(settings.api_url), timeout=30.0)
        if settings.username and settings.password:
            try:
                client.authenticate(settings.username, settings.password)
            except RuntimeError:
                pass

        # Create certificate
        console.print(f"[yellow]Creating certificate for {', '.join(domain)}...[/]")
        console.print("[dim]This may take a minute as Let's Encrypt validates domain ownership[/]")
        result = client.certificate_create(cert_data)

        # Parse expiration
        if result.expires_on:
            expires = datetime.fromisoformat(result.expires_on.replace("Z", "+00:00"))
            expires_str = expires.strftime("%Y-%m-%d")
        else:
            expires_str = "Unknown"

        # Display success panel
        details = f"""[bold]Certificate ID:[/] {result.id}
[bold]Domains:[/]
  {chr(10).join(f'  • {d}' for d in result.domain_names)}

[bold]Provider:[/] {result.provider}
[bold]Expires:[/] {expires_str}

[dim]To attach to a proxy host:[/]
  npm-cli proxy update <domain> --certificate {result.id} --ssl"""

        panel = Panel(details, title="✓ Certificate Created", border_style="green")
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
        console.print("\n[yellow]Common issues:[/]")
        console.print("  • Domain must be publicly accessible for HTTP-01 challenge")
        console.print("  • Check DNS records point to NPM server")
        console.print("  • Rate limits: 5 certs/week per domain")
        raise typer.Exit(1)
    except NPMValidationError as e:
        console.print(f"[bold red]Validation Error:[/] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)


@app.command("show")
def show_certificate(
    identifier: str = typer.Argument(..., help="Certificate ID or domain name")
) -> None:
    """Show certificate details."""
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
            cert = client.certificate_get(int(identifier))
        else:
            # It's a domain name - search for it
            all_certs = client.certificate_list()
            matching_certs = [c for c in all_certs if identifier in c.domain_names]

            if not matching_certs:
                console.print(f"[bold red]Error:[/] No certificate found with domain '{identifier}'")
                raise typer.Exit(1)
            elif len(matching_certs) > 1:
                console.print(f"[yellow]Warning:[/] Multiple certificates match domain '{identifier}':")
                for c in matching_certs:
                    console.print(f"  ID {c.id}: {', '.join(c.domain_names)}")
                console.print("\nUsing the first match. Use ID for specific certificate.")

            cert = matching_certs[0]

        # Parse dates
        if cert.expires_on:
            expires = datetime.fromisoformat(cert.expires_on.replace("Z", "+00:00"))
            expires_str = expires.strftime("%Y-%m-%d %H:%M:%S UTC")

            now = datetime.now(timezone.utc)
            days_left = (expires - now).days

            if days_left < 7:
                status = f"[red]⚠️  EXPIRING SOON ({days_left} days)[/]"
            elif days_left < 30:
                status = f"[yellow]⚠️  EXPIRING SOON ({days_left} days)[/]"
            else:
                status = f"[green]✓ Valid ({days_left} days left)[/]"
        else:
            expires_str = "Unknown"
            status = "[dim]Unknown[/]"

        created_str = cert.created_on or "Unknown"

        # Get proxy hosts using this certificate
        proxy_hosts = client.list_proxy_hosts()
        attached_proxies = [h for h in proxy_hosts if h.certificate_id == cert.id]

        # Build details
        details = f"""[bold]ID:[/] {cert.id}
[bold]Domains:[/]
  {chr(10).join(f'  • {d}' for d in cert.domain_names)}

[bold]Provider:[/] {cert.provider or 'letsencrypt'}
[bold]Nice Name:[/] {cert.nice_name or 'N/A'}

[bold]Dates:[/]
  Created: {created_str}
  Expires: {expires_str}
  Status: {status}

[bold]Attached to proxy hosts:[/]"""

        if attached_proxies:
            for proxy in attached_proxies:
                details += f"\n  • ID {proxy.id}: {', '.join(proxy.domain_names)}"
        else:
            details += "\n  [dim]Not attached to any proxy hosts[/]"

        panel = Panel(details, title=f"Certificate {cert.id}", border_style="cyan")
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


@app.command("delete")
def delete_certificate(
    cert_id: int = typer.Argument(..., help="Certificate ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip usage check and confirmation"),
) -> None:
    """Delete certificate with safety checks."""
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

        # Safety check: see if certificate is in use (unless --force)
        if not force:
            proxy_hosts = client.list_proxy_hosts()
            attached_proxies = [h for h in proxy_hosts if h.certificate_id == cert_id]

            if attached_proxies:
                console.print(f"[bold red]Error:[/] Certificate {cert_id} is attached to {len(attached_proxies)} proxy host(s):")
                for proxy in attached_proxies:
                    console.print(f"  • ID {proxy.id}: {', '.join(proxy.domain_names)}")
                console.print("\n[yellow]Deleting this certificate will break SSL for these hosts.[/]")
                console.print("Use --force to delete anyway, or detach certificate first:")
                console.print("  npm-cli proxy update <host-id> --certificate 0")
                raise typer.Exit(1)

        # Confirm deletion
        if not force:
            typer.confirm(f"Delete certificate {cert_id}?", abort=True)

        # Delete certificate
        client.certificate_delete(cert_id)

        console.print(f"[green]✓[/] Deleted certificate [cyan]{cert_id}[/]")

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
