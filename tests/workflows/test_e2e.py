"""End-to-end workflow tests.

These are unit tests: Notion gateway, the agent runner, and HITL are mocked.
The point is to prove the orchestration contract — step transitions, feedback
loop, resume, and checkpoint lifecycle — without spending real API credits.
"""
from types import SimpleNamespace
from unittest.mock import patch

from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

from weekforge.agents.e2e_agent import ProcessorResult
from weekforge.checkpoint import CheckpointStore
from weekforge.hitl import HitlDecision
from weekforge.models.llm_call_cost import CallMetadata
from weekforge.workflows.e2e import E2eState, run_e2e


def _mem_store() -> CheckpointStore:
    return CheckpointStore(":memory:")


def _fake_result(summary: str = "ok") -> SimpleNamespace:
    return SimpleNamespace(output=ProcessorResult(summary=summary))


def _fake_meta(**overrides: object) -> CallMetadata:
    defaults: dict[str, object] = {
        "input_tokens": 42,
        "output_tokens": 17,
        "latency_ms": 1234,
        "model_used": "gpt-5.4",
    }
    defaults.update(overrides)
    return CallMetadata(**defaults)  # type: ignore[arg-type]


def test_golden_path_query_agent_approve_write() -> None:
    """Fresh run: query → agent → approve → write → done, checkpoint deleted."""
    store = _mem_store()
    records = [{"id": "rec-1"}, {"id": "rec-2"}]

    with (
        patch("weekforge.workflows.e2e.notion.query", return_value=records) as mock_query,
        patch(
            "weekforge.workflows.e2e.run_with_metadata",
            return_value=(_fake_result("synopsis-xyz"), _fake_meta(), []),
        ) as mock_run,
        patch(
            "weekforge.workflows.e2e.hitl_confirm",
            return_value=HitlDecision(approved=True),
        ) as mock_hitl,
        patch("weekforge.workflows.e2e.notion.create", return_value="page-123") as mock_create,
    ):
        run_e2e(database_id="db-1", thread_id="tid-1", store=store)

    mock_query.assert_called_once_with(database_id="db-1")
    mock_run.assert_called_once()
    assert "synopsis-xyz" in mock_hitl.call_args.kwargs["context"]
    mock_create.assert_called_once()
    assert mock_create.call_args.kwargs["content"] == "synopsis-xyz"
    assert store.load("tid-1") is None


def test_feedback_loop_reruns_agent_with_message_history() -> None:
    """Feedback branch: first HITL returns feedback, second approves.

    Agent must be called twice; the second call must receive the message history
    produced by the first call, so the model sees its own prior output.
    """
    store = _mem_store()
    turn1_messages = [
        ModelRequest(parts=[UserPromptPart(content="Records: r")]),
        ModelResponse(parts=[TextPart(content="v1")]),
    ]
    calls: list[dict[str, object]] = []

    def _fake_run(agent: object, prompt: str, message_history: object = None) -> tuple[object, CallMetadata, list[object]]:
        calls.append({"prompt": prompt, "history": message_history})
        if len(calls) == 1:
            return _fake_result("v1"), _fake_meta(input_tokens=10), turn1_messages  # type: ignore[return-value]
        turn2 = [*turn1_messages, ModelRequest(parts=[UserPromptPart(content="fb")])]
        return _fake_result("v2"), _fake_meta(input_tokens=20), turn2  # type: ignore[return-value]

    hitl_returns = iter([
        HitlDecision(approved=False, feedback="make it shorter"),
        HitlDecision(approved=True),
    ])

    with (
        patch("weekforge.workflows.e2e.notion.query", return_value=[{"id": "r"}]),
        patch("weekforge.workflows.e2e.run_with_metadata", side_effect=_fake_run),
        patch(
            "weekforge.workflows.e2e.hitl_confirm",
            side_effect=lambda **kw: next(hitl_returns),
        ),
        patch("weekforge.workflows.e2e.notion.create", return_value="page-123"),
    ):
        run_e2e(database_id="db-1", thread_id="tid-1", store=store)

    assert len(calls) == 2
    assert calls[0]["history"] is None
    # Second call's history must be the dumped version of first_messages — i.e. non-empty.
    second_history = calls[1]["history"]
    assert second_history is not None and len(second_history) >= 1  # type: ignore[arg-type]
    assert "make it shorter" in str(calls[1]["prompt"])


def test_resume_skips_query_and_agent_when_at_review() -> None:
    """Resume from a `review`-step checkpoint must not re-invoke Notion or the LLM."""
    store = _mem_store()
    saved = E2eState(
        database_id="db-1",
        records=[{"id": "r"}],
        last_output="prior-summary",
        calls=[CallMetadata(input_tokens=10, output_tokens=5, latency_ms=100, model_used="gpt-5.4")],
        step="review",
    )
    store.save("tid-1", "e2e", "review", saved)

    with (
        patch("weekforge.workflows.e2e.notion.query") as mock_query,
        patch("weekforge.workflows.e2e.run_with_metadata") as mock_run,
        patch(
            "weekforge.workflows.e2e.hitl_confirm",
            return_value=HitlDecision(approved=True),
        ) as mock_hitl,
        patch("weekforge.workflows.e2e.notion.create", return_value="page-xyz"),
    ):
        run_e2e(database_id="db-ignored", thread_id="tid-1", store=store)

    mock_query.assert_not_called()
    mock_run.assert_not_called()
    assert "prior-summary" in mock_hitl.call_args.kwargs["context"]
    assert store.load("tid-1") is None


def test_quit_preserves_checkpoint() -> None:
    """Quit branch: checkpoint must remain so the run can be resumed later."""
    store = _mem_store()

    with (
        patch("weekforge.workflows.e2e.notion.query", return_value=[{"id": "r"}]),
        patch(
            "weekforge.workflows.e2e.run_with_metadata",
            return_value=(_fake_result(), _fake_meta(), []),
        ),
        patch(
            "weekforge.workflows.e2e.hitl_confirm",
            return_value=HitlDecision(approved=False, quit=True),
        ) as mock_hitl,
        patch("weekforge.workflows.e2e.notion.create") as mock_create,
    ):
        # hitl stub must emulate the real save-before-prompt contract.
        def _save_and_return(**kwargs: object) -> HitlDecision:
            store.save(
                kwargs["thread_id"],  # type: ignore[arg-type]
                kwargs["workflow"],  # type: ignore[arg-type]
                "review",
                kwargs["state"],  # type: ignore[arg-type]
            )
            return HitlDecision(approved=False, quit=True)

        mock_hitl.side_effect = _save_and_return
        run_e2e(database_id="db-1", thread_id="tid-1", store=store)
        mock_create.assert_not_called()

    assert store.load("tid-1") is not None


def test_run_cost_accumulates_across_feedback_iterations() -> None:
    """Run summary must show the sum of all agent turns, not just the final one."""
    store = _mem_store()
    hitl_returns = iter([
        HitlDecision(approved=False, feedback="again"),
        HitlDecision(approved=True),
    ])

    with (
        patch("weekforge.workflows.e2e.notion.query", return_value=[]),
        patch(
            "weekforge.workflows.e2e.run_with_metadata",
            side_effect=[
                (_fake_result("a"), _fake_meta(input_tokens=10, output_tokens=3), []),
                (_fake_result("b"), _fake_meta(input_tokens=20, output_tokens=5), []),
            ],
        ),
        patch(
            "weekforge.workflows.e2e.hitl_confirm",
            side_effect=lambda **kw: next(hitl_returns),
        ) as mock_hitl,
        patch("weekforge.workflows.e2e.notion.create", return_value="p"),
    ):
        run_e2e(database_id="db-1", thread_id="tid-1", store=store)

    # Second HITL call's context must reflect BOTH turns' tokens.
    last_context = mock_hitl.call_args_list[-1].kwargs["context"]
    assert "30 in" in last_context
    assert "8 out" in last_context
