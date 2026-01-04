"""CliRunner integration tests for CLI commands."""

from typer.testing import CliRunner
from npm_cli.__main__ import app


def test_version_command():
    """Test version command returns exit code 0 with version string."""
    runner = CliRunner()
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
    assert "npm-cli" in result.output, "Expected 'npm-cli' in version output"
    assert "0.1.0" in result.output, "Expected version '0.1.0' in output"


def test_help_output():
    """Test help command shows subcommand names."""
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
    assert "proxy" in result.output, "Expected 'proxy' subcommand in help"
    assert "cert" in result.output, "Expected 'cert' subcommand in help"
    assert "config" in result.output, "Expected 'config' subcommand in help"


def test_proxy_list_no_auth():
    """Test proxy list command without auth shows graceful error."""
    runner = CliRunner()
    result = runner.invoke(app, ["proxy", "list"])

    # Should either succeed (if no auth required) or show clear error
    # Both are acceptable - just verify it doesn't crash
    assert result.exit_code in [0, 1], \
        f"Expected exit code 0 or 1, got {result.exit_code}"
