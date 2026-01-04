"""NPM CLI main entry point."""

import typer
from rich.console import Console

from npm_cli.cli import proxy, cert, config

console = Console()
app = typer.Typer(help="NPM CLI - Manage Nginx Proxy Manager via API")


@app.command()
def version() -> None:
    """Show version information."""
    console.print("[bold cyan]npm-cli[/bold cyan] [green]0.1.0[/green]")


# Register subcommands
app.add_typer(proxy.app, name="proxy")
app.add_typer(cert.app, name="cert")
app.add_typer(config.app, name="config")


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
