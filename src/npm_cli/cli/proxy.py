"""Proxy host management commands."""

import typer
from rich.console import Console

app = typer.Typer(help="Manage proxy hosts")
console = Console()


@app.command()
def list() -> None:
    """List all proxy hosts."""
    console.print("[yellow]Proxy host listing not yet implemented[/yellow]")
