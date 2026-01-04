"""Configuration management commands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(help="Manage configuration")
console = Console()


@app.command()
def init() -> None:
    """Initialize NPM CLI configuration interactively."""
    console.print(Panel.fit(
        "[bold cyan]NPM CLI Configuration Setup[/bold cyan]\n\n"
        "This will create a .env file with your NPM connection settings.",
        border_style="cyan"
    ))
    console.print()

    # Prompt for configuration values
    api_url = typer.prompt(
        "NPM API URL",
        default="http://localhost:81"
    )

    username = typer.prompt("NPM Username")

    password = typer.prompt(
        "NPM Password",
        hide_input=True
    )

    container_name = typer.prompt(
        "NPM Docker Container Name",
        default="nginx-proxy-manager"
    )

    # Validate URL format (basic check)
    if not (api_url.startswith("http://") or api_url.startswith("https://")):
        console.print("[red]Error:[/red] API URL must start with http:// or https://")
        raise typer.Exit(1)

    # Create .env file
    env_path = Path(".env")
    env_content = f"""# NPM CLI Configuration
NPM_API_URL={api_url}
NPM_USERNAME={username}
NPM_PASSWORD={password}
NPM_CONTAINER_NAME={container_name}
NPM_USE_DOCKER_DISCOVERY=true
"""

    env_path.write_text(env_content)
    console.print(f"\n[green]✓[/green] Configuration saved to {env_path.absolute()}")

    # Create/update .gitignore
    gitignore_path = Path(".gitignore")
    if gitignore_path.exists():
        gitignore_content = gitignore_path.read_text()
        if ".env" not in gitignore_content:
            with gitignore_path.open("a") as f:
                f.write("\n.env\n")
            console.print("[green]✓[/green] Added .env to .gitignore")
        else:
            console.print("[dim]• .env already in .gitignore[/dim]")
    else:
        gitignore_path.write_text(".env\n")
        console.print("[green]✓[/green] Created .gitignore with .env")

    # Show next steps
    console.print()
    console.print(Panel.fit(
        "[bold green]Setup Complete![/bold green]\n\n"
        "Run [cyan]npm-cli config status[/cyan] to verify your connection.",
        border_style="green"
    ))


@app.command()
def status() -> None:
    """Show NPM connection status and verify configuration."""
    from datetime import datetime, timezone
    import json

    from npm_cli.config.settings import NPMSettings
    from npm_cli.docker.discovery import get_docker_client, discover_npm_container
    from npm_cli.api.client import NPMClient

    console.print(Panel.fit(
        "[bold cyan]NPM Connection Status[/bold cyan]",
        border_style="cyan"
    ))
    console.print()

    # 1. Load settings
    try:
        settings = NPMSettings()
    except Exception as e:
        console.print(f"[red]✗ Configuration Error:[/red] {e}")
        console.print("\n[dim]Run [cyan]npm-cli config init[/cyan] to set up configuration.[/dim]")
        raise typer.Exit(1)

    # Display NPM API URL
    console.print(f"[cyan]NPM API URL:[/cyan] {settings.api_url}")
    if settings.username:
        console.print(f"[cyan]NPM Username:[/cyan] {settings.username}")
    else:
        console.print("[yellow]NPM Username:[/yellow] Not set")

    # 2. Docker Discovery
    console.print()
    console.print("[bold]Docker Discovery[/bold]")
    docker_client = get_docker_client()

    if docker_client:
        container = discover_npm_container(
            docker_client,
            container_name=settings.container_name
        )
        if container:
            console.print(f"  [green]✓[/green] Container found: [cyan]{container.name}[/cyan]")
            console.print(f"  [dim]Status: {container.status}[/dim]")
        else:
            console.print("  [yellow]⚠[/yellow] NPM container not found")
            console.print(f"  [dim]Searched for: {settings.container_name}[/dim]")
    else:
        console.print("  [yellow]⚠[/yellow] Docker unavailable (using manual URL configuration)")

    # 3. Token Status
    console.print()
    console.print("[bold]Token Status[/bold]")
    token_path = Path.home() / ".npm-cli" / "token.json"

    if token_path.exists():
        try:
            token_data = json.loads(token_path.read_text())
            expires_str = token_data["expires"]

            # Parse expiry
            expires = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)

            if expires > now:
                time_left = expires - now
                hours = int(time_left.total_seconds() / 3600)
                minutes = int((time_left.total_seconds() % 3600) / 60)
                console.print("  [green]✓[/green] Token valid")
                console.print(f"  [dim]Expires in: {hours}h {minutes}m ({expires_str})[/dim]")
            else:
                console.print("  [red]✗[/red] Token expired")
                console.print(f"  [dim]Expired at: {expires_str}[/dim]")
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            console.print(f"  [red]✗[/red] Invalid token file: {e}")
    else:
        console.print("  [yellow]⚠[/yellow] No token found")
        console.print("  [dim]Token will be created on first authentication[/dim]")

    # 4. Connection Test
    console.print()
    console.print("[bold]Connection Test[/bold]")

    try:
        client = NPMClient(base_url=str(settings.api_url))

        # Check if token exists and is valid
        if token_path.exists():
            try:
                # Try a simple API call to verify connection
                response = client.request("GET", "/api/settings")
                if response.status_code == 200:
                    console.print("  [green]✓[/green] NPM API connection successful")
                else:
                    console.print(f"  [yellow]⚠[/yellow] NPM API returned status {response.status_code}")
            except RuntimeError:
                # Token expired or missing
                console.print("  [yellow]⚠[/yellow] Token required - authenticate first")
            except Exception as e:
                console.print(f"  [red]✗[/red] Connection failed: {e}")
        else:
            # Try to authenticate with provided credentials
            if settings.username and settings.password:
                try:
                    client.authenticate(settings.username, settings.password)
                    console.print("  [green]✓[/green] Authentication successful (token created)")
                except Exception as e:
                    console.print(f"  [red]✗[/red] Authentication failed: {e}")
                    console.print("  [dim]Check that NPM_USERNAME and NPM_PASSWORD are correct in .env[/dim]")
            else:
                console.print("  [yellow]⚠[/yellow] No credentials provided")
                console.print("  [dim]Set NPM_USERNAME and NPM_PASSWORD in .env[/dim]")

    except Exception as e:
        console.print(f"  [red]✗[/red] Error: {e}")

    console.print()


@app.command()
def show() -> None:
    """Show current configuration."""
    console.print("[yellow]Configuration display not yet implemented[/yellow]")
