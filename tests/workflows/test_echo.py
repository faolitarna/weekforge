from unittest.mock import patch

from weekforge.checkpoint import CheckpointStore
from weekforge.hitl import HitlDecision
from weekforge.workflows.echo import run_echo


def _mem_store() -> CheckpointStore:
    return CheckpointStore(":memory:")


def test_echo_produces_prefixed_message() -> None:
    """Why test: Echo logic must prefix the message before HITL — the workflow's only transformation."""
    store = _mem_store()
    with patch("weekforge.workflows.echo.hitl_confirm", return_value=HitlDecision(approved=True)) as mock_hitl:
        run_echo(message="hello world", thread_id="tid-1", store=store)

    call_kwargs = mock_hitl.call_args
    assert "Echoed: hello world" in call_kwargs.kwargs["context"]


def test_echo_passes_checkpoint_to_hitl() -> None:
    """Why test: hitl_confirm is responsible for saving state (per hitl.py contract).

    Verifies that run_echo hands the right store/thread_id/workflow to hitl_confirm
    so the crash-safety save happens with the correct metadata.
    """
    store = _mem_store()
    with patch("weekforge.workflows.echo.hitl_confirm", return_value=HitlDecision(approved=True)) as mock_hitl:
        run_echo(message="test", thread_id="tid-1", store=store)

    assert mock_hitl.call_args.kwargs["checkpoint"] is store
    assert mock_hitl.call_args.kwargs["thread_id"] == "tid-1"
    assert mock_hitl.call_args.kwargs["workflow"] == "echo"


def test_echo_resumes_from_checkpoint() -> None:
    """Why test: Resume path must ignore the `message` argument and restore from saved state.

    Without this, a resumed run would overwrite the previously computed result and
    present different output than what the user confirmed.
    """
    store = _mem_store()
    from weekforge.models.state import State
    store.save("tid-1", "echo", "confirm", State(message="Echoed: prior message"))

    with patch("weekforge.workflows.echo.hitl_confirm", return_value=HitlDecision(approved=True)) as mock_hitl:
        run_echo(message="ignored", thread_id="tid-1", store=store)

    context = mock_hitl.call_args.kwargs["context"]
    assert "prior message" in context
