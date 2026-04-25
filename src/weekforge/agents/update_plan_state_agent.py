import json
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent, RunContext

from weekforge.agents.openai_model_factory import build_openai_model
from weekforge.agents.prompt_composer import compose_static_instructions
from weekforge.config.env import settings
from weekforge.config.llm_profiles import resolve_llm_profile
from weekforge.models.week_summary import WeekSummary
from weekforge.prompts.loader import Prompt
from weekforge.tools.plan_state import PlanState


@dataclass
class PlanStateDeps:
    existing_plan_state: PlanState
    new_week: WeekSummary | None = None
    all_weeks: list[WeekSummary] | None = None


def _filter_week_for_plan_state(week: WeekSummary) -> dict[str, Any]:
    """Strip noise from WeekSummary before injecting into plan_state context.
    Keep: completion, sessions, signal exercises, pain, cardio, climbing, issues, wins, context.
    Drop: bodyweight warmups without feedback, implicit_feedback, recommendations, highlights, trend.
    """
    signal_exercises = [
        e.model_dump(exclude_none=True) for e in week.exercise_log
        if e.planned_weight or e.actual_weight or e.feedback or e.status == "done_modified"
    ]
    return {
        "week_prefix": week.week_prefix,
        "completion": week.completion,
        "sessions": [s.model_dump(exclude_none=True) for s in week.sessions],
        "exercise_log": signal_exercises,
        "pain_status": [p.model_dump(exclude_none=True) for p in week.pain_status],
        "cardio_log": [c.model_dump(exclude_none=True) for c in (week.cardio_log or [])],
        "climbing_log": [c.model_dump(exclude_none=True) for c in (week.climbing_log or [])],
        "issues": week.issues,
        "wins": week.wins,
        "context": week.context,
    }


_model, _model_settings = build_openai_model(resolve_llm_profile("reasoning"))

update_plan_state_agent = Agent(
    model=_model,
    model_settings=_model_settings,
    instructions=compose_static_instructions(Prompt.UPDATE_PLAN_STATE_TASK, settings.caveman_mode),
    deps_type=PlanStateDeps,
    output_type=PlanState,
)


@update_plan_state_agent.instructions
def _inject_current_and_new(ctx: RunContext[PlanStateDeps]) -> str:
    if ctx.deps.all_weeks:
        weeks_parts = []
        for w in ctx.deps.all_weeks:
            filtered = json.dumps(_filter_week_for_plan_state(w), default=str)
            weeks_parts.append(f"Week {w.week_prefix}:\n```json\n{filtered}\n```")
        return "## Bootstrap Context (All Weeks data)\n" + "\n\n".join(weeks_parts)

    assert ctx.deps.new_week is not None
    filtered = json.dumps(_filter_week_for_plan_state(ctx.deps.new_week), default=str)
    return (
        "## Existing PLAN_STATE\n```json\n" + ctx.deps.existing_plan_state.model_dump_json() + "\n```\n\n"
        "## New week to merge\n```json\n" + filtered + "\n```\n"
    )
