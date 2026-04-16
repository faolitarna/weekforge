from unittest.mock import patch

from weekforge.checkpoint import CheckpointStore
from weekforge.hitl import HitlDecision
from weekforge.workflows.echo import run_echo


def _mem_store() -> CheckpointStore:
    return CheckpointStore(":memory:")


def test_echo_produces_prefixed_message() -> None:
    store = _mem_store()
    with patch("weekforge.workflows.echo.hitl_confirm", return_value=HitlDecision(approved=True)) as mock_hitl:
        run_echo(message="hello world", thread_id="tid-1", store=store)

    call_kwargs = mock_hitl.call_args
    assert "Echoed: hello world" in call_kwargs.kwargs["context"]


def test_echo_passes_checkpoint_to_hitl() -> None:
    store = _mem_store()
    with patch("weekforge.workflows.echo.hitl_confirm", return_value=HitlDecision(approved=True)) as mock_hitl:
        run_echo(message="test", thread_id="tid-1", store=store)

    # hitl_confirm is responsible for saving state (per spec); verify it receives the right args
    assert mock_hitl.call_args.kwargs["checkpoint"] is store
    assert mock_hitl.call_args.kwargs["thread_id"] == "tid-1"
    assert mock_hitl.call_args.kwargs["workflow"] == "echo"


def test_echo_resumes_from_checkpoint() -> None:
    store = _mem_store()
    # Simulate a prior interrupted run that already saved state
    from weekforge.models.state import State
    store.save("tid-1", "echo", "confirm", State(message="Echoed: prior message"))

    with patch("weekforge.workflows.echo.hitl_confirm", return_value=HitlDecision(approved=True)) as mock_hitl:
        run_echo(message="ignored", thread_id="tid-1", store=store)

    context = mock_hitl.call_args.kwargs["context"]
    assert "prior message" in context
