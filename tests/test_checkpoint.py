from pydantic import BaseModel

from weekforge.checkpoint import CheckpointStore


class _State(BaseModel):
    """Minimal fixture — checkpoint store is state-schema-agnostic."""
    message: str = ""


State = _State


def _mem_store() -> CheckpointStore:
    return CheckpointStore(":memory:")


def test_save_and_load_roundtrip() -> None:
    """Why test: Pydantic state survives JSON serialization through the checkpoint layer.

    If model_dump_json / model_validate_json lose data or fail on schema changes,
    resumed workflows would start with corrupted state rather than failing loudly.
    """
    store = _mem_store()
    state = State(message="hello")
    store.save("tid-1", "echo", "confirm", state)

    rec = store.load("tid-1")
    assert rec is not None
    assert rec.thread_id == "tid-1"
    assert rec.workflow == "echo"
    assert rec.step == "confirm"

    restored = State.model_validate_json(rec.state_json)
    assert restored.message == "hello"


def test_load_missing_returns_none() -> None:
    """Why test: Workflows branch on load() returning None to detect a fresh vs. resumed run."""
    store = _mem_store()
    assert store.load("nonexistent") is None


def test_save_overwrites_existing() -> None:
    """Why test: UPSERT semantics — a second save must advance the step label and state.

    Without this, a workflow pausing at step-b after step-a would still resume at
    step-a on the next invocation.
    """
    store = _mem_store()
    store.save("tid-1", "echo", "step-a", State(message="first"))
    store.save("tid-1", "echo", "step-b", State(message="second"))

    rec = store.load("tid-1")
    assert rec is not None
    assert rec.step == "step-b"
    assert State.model_validate_json(rec.state_json).message == "second"


def test_delete_removes_record() -> None:
    """Why test: delete() is the workflow-complete signal — list_active() must not show it."""
    store = _mem_store()
    store.save("tid-1", "echo", "confirm", State(message="x"))
    store.delete("tid-1")
    assert store.load("tid-1") is None


def test_list_active_returns_all_undeleted() -> None:
    """Why test: CLI root command relies on list_active() to show only paused (not finished) runs."""
    store = _mem_store()
    store.save("tid-1", "echo", "confirm", State(message="a"))
    store.save("tid-2", "notion_test", "reviewed", State(message="b"))
    store.save("tid-3", "echo", "confirm", State(message="c"))
    store.delete("tid-2")

    active = store.list_active()
    ids = [r.thread_id for r in active]
    assert "tid-1" in ids
    assert "tid-3" in ids
    assert "tid-2" not in ids


def test_list_active_empty_when_no_checkpoints() -> None:
    """Why test: Root command must show "No active checkpoints" cleanly on a fresh install."""
    store = _mem_store()
    assert store.list_active() == []
