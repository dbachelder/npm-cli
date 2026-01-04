"""SSL certificate management commands."""

import typer
from rich.console import Console

app = typer.Typer(help="Manage SSL certificates")
console = Console()


@app.command()
def list() -> None:
    """List all SSL certificates."""
    console.print("[yellow]SSL certificate listing not yet implemented[/yellow]")
