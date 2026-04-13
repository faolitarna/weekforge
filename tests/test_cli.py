from typer.testing import CliRunner

from weekforge.cli import app

runner = CliRunner()


def test_cli_help() -> None:
    """
    Why test: CLI Smoke Test.
    Ensure the Typer app initializes correctly and doesn't crash on standard arguments.
    """
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Weekforge" in result.stdout
