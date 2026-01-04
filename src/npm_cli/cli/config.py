"""Configuration management commands."""

import typer
from rich.console import Console

app = typer.Typer(help="Manage configuration")
console = Console()


@app.command()
def show() -> None:
    """Show current configuration."""
    console.print("[yellow]Configuration display not yet implemented[/yellow]")
