from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from weekforge.agents.openai_model_factory import build_openai_model
from weekforge.agents.prompt_composer import compose_static_instructions
from weekforge.config.env import settings
from weekforge.config.llm_profiles import resolve_llm_profile
from weekforge.models.week_summary import WeekSummary
from weekforge.tools.plan_state import PlanState

@dataclass
class PlanStateDeps:
    existing_plan_state: PlanState
    new_week: WeekSummary | None = None
    all_weeks: list[WeekSummary] | None = None # For bootstrap mode

_PLAN_STATE_TASK = """\
You are an expert training coach merging new weekly data into a cumulative `PLAN_STATE`.
Your objective is to update logical and interpretive fields (trends, issues, preferences) based on the context.

If this is an incremental update (`new_week` provided):
- Move any `active_issues` that are resolved this week into `resolved`.
- Evaluate `main_lifts` and adjust the `trend:` tag to one of (up/plateau/down) by interpreting the recent trajectory.
- Add any new severe observations from `new_week.issues` into `active_issues`.

If this is a bootstrap (`all_weeks` provided):
- Compile the entire list of weeks chronologically.
- Rebuild progressions and establish active/resolved issues.

Return the fully parsed `PlanState` schema matching the latest reality.
"""

_model, _model_settings = build_openai_model(resolve_llm_profile("reasoning"))

plan_state_agent = Agent(
    model=_model,
    model_settings=_model_settings,
    instructions=compose_static_instructions(settings.caveman_mode) + "\n\n" + _PLAN_STATE_TASK,
    deps_type=PlanStateDeps,
    output_type=PlanState,
)

@plan_state_agent.instructions
def _inject_current_and_new(ctx: RunContext[PlanStateDeps]) -> str:
    if ctx.deps.all_weeks:
        weeks_json = "\n\n".join(f"Week {w.week_prefix}:\n```json\n{w.model_dump_json(exclude_none=True)}\n```" for w in ctx.deps.all_weeks)
        return (
            "## Bootstrap Context (All Weeks data)\n" + weeks_json
        )
    else:
        assert ctx.deps.new_week is not None
        return (
            "## Existing PLAN_STATE\n```json\n" + ctx.deps.existing_plan_state.model_dump_json() + "\n```\n\n"
            "## New week to merge\n```json\n" + ctx.deps.new_week.model_dump_json(exclude_none=True) + "\n```\n"
        )
