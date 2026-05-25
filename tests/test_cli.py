from unittest.mock import patch

from pydantic import BaseModel
from typer.testing import CliRunner

from weekforge.checkpoint import CheckpointStore
from weekforge.cli import app
from weekforge.models.workflow_state import DraftWeekState

runner = CliRunner()


def test_cli_help() -> None:
    """
    Why test: CLI Smoke Test.
    Ensure the Typer app initializes correctly and doesn't crash on standard arguments.
    """
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Weekforge" in result.stdout


def test_cli_resume_no_checkpoint_exits_1(tmp_path) -> None:
    """resume with a thread-id that has no checkpoint must exit with code 1."""
    with patch("weekforge.cli._make_store", return_value=CheckpointStore(str(tmp_path / "cp.sqlite"))):
        result = runner.invoke(app, ["resume", "--thread-id", "nonexistent-tid"])
    assert result.exit_code == 1
    assert "No checkpoint" in result.stdout


def test_cli_resume_unknown_workflow_exits_1(tmp_path) -> None:
    """resume with a checkpoint whose workflow isn't in _WORKFLOW_RUNNERS must exit 1."""
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    class _Dummy(BaseModel):
        step: str = "x"

    store.save("tid-ghost", "ghost_workflow", "x", _Dummy())

    with patch("weekforge.cli._make_store", return_value=store):
        result = runner.invoke(app, ["resume", "--thread-id", "tid-ghost"])
    assert result.exit_code == 1
    assert "Unknown workflow" in result.stdout


def test_cli_register_workflows_is_idempotent() -> None:
    """Calling _register_workflows() twice must not duplicate runners."""
    from weekforge.cli import _register_workflows, _WORKFLOW_RUNNERS
    _WORKFLOW_RUNNERS.clear()  # reset any cached state from prior tests

    runners_first = _register_workflows()
    first_keys = list(runners_first.keys())
    runners_second = _register_workflows()
    second_keys = list(runners_second.keys())

    assert first_keys == second_keys
    assert len(second_keys) == len(set(second_keys)), "no duplicate workflow keys after double registration"


def test_cli_draft_week_help() -> None:
    """draft-week command exists and shows help."""
    result = runner.invoke(app, ["draft-week", "--help"])
    assert result.exit_code == 0
    assert "draft" in result.stdout.lower()


def test_cli_plan_placeholder_removed() -> None:
    """Old 'plan' command no longer exists."""
    result = runner.invoke(app, ["plan"])
    assert result.exit_code != 0


def test_cli_resume_dispatches_draft_week(tmp_path) -> None:
    """resume with draft_week checkpoint dispatches to run_draft."""
    from weekforge.cli import _WORKFLOW_RUNNERS

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    state = DraftWeekState(week_prefix="W15", step="load_context")
    store.save("draft-week-W15", "draft_week", "load_context", state)

    with patch("weekforge.cli._make_store", return_value=store):
        with patch("weekforge.workflows.draft_week.run_draft") as mock_run:
            mock_run.side_effect = RuntimeError("Not yet implemented")
            # Clear cache so _register_workflows re-imports while mock is active.
            _WORKFLOW_RUNNERS.clear()
            result = runner.invoke(app, ["resume", "--thread-id", "draft-week-W15"])

    mock_run.assert_called_once()


def test_cli_register_workflows_includes_draft_week() -> None:
    """_register_workflows includes draft_week entry."""
    from weekforge.cli import _register_workflows, _WORKFLOW_RUNNERS
    _WORKFLOW_RUNNERS.clear()

    runners = _register_workflows()
    assert "draft_week" in runners
    assert "summarize_week" in runners
