from unittest.mock import MagicMock, patch

from pydantic import BaseModel

from weekforge.checkpoint import CheckpointStore
from weekforge.hitl import AcceptResult, run_accept_gate
from weekforge.models.llm_call_cost import CallMetadata, RunCost


class DummyState(BaseModel):
    step: str = "accept"


@patch("weekforge.hitl.hitl_confirm")
def test_accept_gate_approve(mock_confirm, tmp_path):
    mock_confirm.return_value = MagicMock(approved=True, quit=False, feedback=None)
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    cost = RunCost()

    result = run_accept_gate(
        render_fn=lambda: "summary text",
        approved_step="write",
        cost=cost,
        calls=[],
        max_iterations=3,
        store=store,
        thread_id="tid",
        workflow="test",
        step="accept",
        state=DummyState(),
    )

    assert result.step == "write"
    assert result.feedback is None


@patch("weekforge.hitl.hitl_confirm")
def test_accept_gate_quit(mock_confirm, tmp_path):
    mock_confirm.return_value = MagicMock(approved=False, quit=True, feedback=None)
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    cost = RunCost()

    result = run_accept_gate(
        render_fn=lambda: "summary text",
        approved_step="write",
        cost=cost,
        calls=[],
        max_iterations=3,
        store=store,
        thread_id="tid",
        workflow="test",
        step="accept",
        state=DummyState(),
    )

    assert result.step is None
    assert result.feedback is None


@patch("weekforge.hitl.hitl_confirm")
def test_accept_gate_feedback(mock_confirm, tmp_path):
    mock_confirm.return_value = MagicMock(approved=False, quit=False, feedback="more detail")
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    cost = RunCost()

    result = run_accept_gate(
        render_fn=lambda: "summary text",
        approved_step="write",
        cost=cost,
        calls=[],
        max_iterations=3,
        store=store,
        thread_id="tid",
        workflow="test",
        step="accept",
        state=DummyState(),
    )

    assert result.step == "agent"
    assert result.feedback == "more detail"


@patch("weekforge.hitl.hitl_confirm")
def test_accept_gate_burn_warning(mock_confirm, tmp_path):
    mock_confirm.return_value = MagicMock(approved=True, quit=False, feedback=None)
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    cost = RunCost()
    meta = CallMetadata(input_tokens=10, output_tokens=10, latency_ms=100, model_used="test", cost_eur=0.01)

    result = run_accept_gate(
        render_fn=lambda: "summary text",
        approved_step="write",
        cost=cost,
        calls=[meta, meta, meta],  # at max_iterations
        max_iterations=3,
        store=store,
        thread_id="tid",
        workflow="test",
        step="accept",
        state=DummyState(),
    )

    assert result.step == "write"
    # Verify burn warning was in context passed to hitl_confirm
    call_kwargs = mock_confirm.call_args[1] if mock_confirm.call_args[1] else {}
    context_arg = call_kwargs.get("context", mock_confirm.call_args[0][0] if mock_confirm.call_args[0] else "")
    assert "burn warning" in context_arg.lower()
