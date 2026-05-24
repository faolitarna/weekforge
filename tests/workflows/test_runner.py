from unittest.mock import MagicMock, call, patch

import pytest
from pydantic import BaseModel, Field

from weekforge.checkpoint import CheckpointStore
from weekforge.models.llm_call_cost import CallMetadata, RunCost
from weekforge.workflows.runner import run_workflow


class FakeState(BaseModel):
    step: str = "step_a"
    value: int = 0
    calls: list[CallMetadata] = Field(default_factory=list)


def test_run_workflow_dispatches_steps(tmp_path):
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    def step_a(state: FakeState, cost: RunCost) -> str:
        state.value = 1
        return "step_b"

    def step_b(state: FakeState, cost: RunCost) -> str:
        state.value = 2
        return "done"

    steps = {"step_a": step_a, "step_b": step_b}
    initial = FakeState()

    run_workflow(
        workflow="test_wf",
        state_cls=FakeState,
        initial_state=initial,
        steps=steps,
        thread_id="tid-1",
        store=store,
    )

    assert store.load("tid-1") is None  # deleted on done


def test_run_workflow_resumes_from_checkpoint(tmp_path):
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    resumed_state = FakeState(step="step_b", value=10)
    store.save("tid-1", "test_wf", "step_b", resumed_state)

    def step_b(state: FakeState, cost: RunCost) -> str:
        state.value = state.value + 1
        return "done"

    steps = {"step_b": step_b}
    initial = FakeState()  # ignored — checkpoint takes precedence

    run_workflow(
        workflow="test_wf",
        state_cls=FakeState,
        initial_state=initial,
        steps=steps,
        thread_id="tid-1",
        store=store,
    )

    assert store.load("tid-1") is None


def test_run_workflow_quit_on_none(tmp_path):
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    def step_a(state: FakeState, cost: RunCost) -> str | None:
        return None  # user quit

    steps = {"step_a": step_a}
    initial = FakeState()

    run_workflow(
        workflow="test_wf",
        state_cls=FakeState,
        initial_state=initial,
        steps=steps,
        thread_id="tid-1",
        store=store,
    )

    # Checkpoint preserved (not deleted)
    record = store.load("tid-1")
    assert record is not None


def test_run_workflow_unknown_step_raises(tmp_path):
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    def step_a(state: FakeState, cost: RunCost) -> str:
        return "nonexistent"

    steps = {"step_a": step_a}
    initial = FakeState()

    with pytest.raises(RuntimeError, match="Unknown step"):
        run_workflow(
            workflow="test_wf",
            state_cls=FakeState,
            initial_state=initial,
            steps=steps,
            thread_id="tid-1",
            store=store,
        )


def test_run_workflow_saves_before_dispatch(tmp_path):
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    save_calls = []
    original_save = store.save

    def tracking_save(*args, **kwargs):
        save_calls.append(args)
        return original_save(*args, **kwargs)

    store.save = tracking_save

    def step_a(state: FakeState, cost: RunCost) -> str:
        return "done"

    steps = {"step_a": step_a}
    initial = FakeState()

    run_workflow(
        workflow="test_wf",
        state_cls=FakeState,
        initial_state=initial,
        steps=steps,
        thread_id="tid-1",
        store=store,
    )

    # At least one save before the step dispatch
    assert len(save_calls) >= 1
    assert save_calls[0][2] == "step_a"  # saved with step_a before dispatching


def test_run_workflow_restores_cost_from_calls(tmp_path):
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    captured_cost = []

    meta = CallMetadata(input_tokens=100, output_tokens=50, latency_ms=500, model_used="test", cost_eur=0.01)
    resumed = FakeState(step="step_a", calls=[meta])
    store.save("tid-1", "test_wf", "step_a", resumed)

    def step_a(state: FakeState, cost: RunCost) -> str:
        captured_cost.append(cost.total_input_tokens)
        return "done"

    steps = {"step_a": step_a}

    run_workflow(
        workflow="test_wf",
        state_cls=FakeState,
        initial_state=FakeState(),
        steps=steps,
        thread_id="tid-1",
        store=store,
    )

    assert captured_cost[0] == 100
