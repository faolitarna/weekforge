from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from weekforge.agents.openai_model_factory import build_openai_model
from weekforge.agents.prompt_composer import compose_static_instructions
from weekforge.config.env import settings
from weekforge.config.llm_profiles import resolve_llm_profile
from weekforge.models.week_plan import WeekPlan
from weekforge.prompts.loader import Prompt


@dataclass(frozen=True)
class DraftWeekDeps:
    week_prefix: str
    template_markdown: str
    feedback_window_markdown: str
    plan_state_raw: str | None
    user_profile_markdown: str
    active_flare: bool
    bootstrap: bool


_model, _model_settings = build_openai_model(resolve_llm_profile("reasoning"))

draft_week_agent = Agent(
    model=_model,
    model_settings=_model_settings,
    instructions=compose_static_instructions(Prompt.DRAFT_WEEK_TASK, settings.caveman_mode),
    deps_type=DraftWeekDeps,
    output_type=WeekPlan,
)


@draft_week_agent.instructions
def _inject_user_profile(ctx: RunContext[DraftWeekDeps]) -> str:
    return "## Active User Profile\n\n" + ctx.deps.user_profile_markdown


@draft_week_agent.instructions
def _inject_templates(ctx: RunContext[DraftWeekDeps]) -> str:
    return ctx.deps.template_markdown


@draft_week_agent.instructions
def _inject_feedback_window(ctx: RunContext[DraftWeekDeps]) -> str:
    return ctx.deps.feedback_window_markdown


@draft_week_agent.instructions
def _inject_plan_state(ctx: RunContext[DraftWeekDeps]) -> str:
    if not ctx.deps.plan_state_raw:
        return ""
    return (
        "## Existing PLAN_STATE (progression context)\n\n"
        + ctx.deps.plan_state_raw
    )


@draft_week_agent.instructions
def _inject_active_flare(ctx: RunContext[DraftWeekDeps]) -> str:
    flag = "YES" if ctx.deps.active_flare else "NO"
    return f"ACTIVE_FLARE: {flag}"


@draft_week_agent.instructions
def _inject_bootstrap_hint(ctx: RunContext[DraftWeekDeps]) -> str:
    if not ctx.deps.bootstrap:
        return ""
    return (
        "## Bootstrap Mode\n\n"
        "Limited historical data available. Use templates and user profile as primary references. "
        "Apply conservative defaults for load and volume."
    )
