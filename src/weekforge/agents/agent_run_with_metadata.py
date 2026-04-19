"""Generic runner that executes an `Agent` and captures token + latency metadata.

Each agent call produces a `CallMetadata`; workflows accumulate them into a
`RunCost` for display at completion. Optionally forwards `message_history` so
callers can drive multi-turn feedback loops; the updated message list is
returned alongside the result for persistence across HITL pauses.
"""
import time
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models import Model

from weekforge.models.llm_call_cost import CallMetadata
from weekforge.models.pricing import estimate_cost_eur


def run_with_metadata(
    agent: Agent[Any, Any],
    prompt: str,
    deps: Any | None = None,
    message_history: list[ModelMessage] | None = None,
) -> tuple[Any, CallMetadata, list[ModelMessage]]:
    """Run an agent synchronously; capture metadata and full message history.

    `message_history` lets callers continue a prior conversation (feedback loop).
    Returns the raw `AgentRunResult`, `CallMetadata` for cost accumulation, and
    the full message list post-call (from `result.all_messages()`) for the next
    turn or for persisting across HITL pauses.
    Calls `agent.run_sync()` — blocks the event loop if called from an async context.
    """
    t0 = time.perf_counter()
    result = agent.run_sync(prompt, deps=deps, message_history=message_history)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    usage = result.usage()
    model = agent.model
    if not isinstance(model, Model):
        raise TypeError(f"Expected a resolved Model on agent, got {type(model)}")
    in_tokens = usage.input_tokens or 0
    out_tokens = usage.output_tokens or 0
    meta = CallMetadata(
        input_tokens=in_tokens,
        output_tokens=out_tokens,
        latency_ms=latency_ms,
        model_used=model.model_name,
        cost_eur=estimate_cost_eur(model.model_name, in_tokens, out_tokens),
    )
    return result, meta, result.all_messages()
