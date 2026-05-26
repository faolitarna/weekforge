import logging
from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from weekforge.agents.openai_model_factory import build_openai_model
from weekforge.agents.prompt_composer import compose_static_instructions
from weekforge.config.env import settings
from weekforge.config.llm_profiles import resolve_llm_profile
from weekforge.models.user_profile import UserProfile
from weekforge.models.week_summary import ImplicitFeedback, PlanAdherence, WeekSummary
from weekforge.prompts.loader import Prompt

_logger = logging.getLogger(__name__)


@dataclass
class SummarizeDeps:
    user_profile: UserProfile
    implicit_feedback: ImplicitFeedback
    plan_adherence: PlanAdherence | None
    tier0_summary_json: str
    raw_sessions_markdown: str = ""
    planned_plan_markdown: str | None = None
    plan_state_raw: str | None = None

_model, _model_settings = build_openai_model(resolve_llm_profile("fast"))

summarize_week_agent = Agent(
    model=_model,
    model_settings=_model_settings,
    instructions=compose_static_instructions(Prompt.SUMMARIZE_WEEK_TASK, settings.caveman_mode),
    deps_type=SummarizeDeps,
    output_type=WeekSummary,
)

@summarize_week_agent.instructions
def _inject_user_profile(ctx: RunContext[SummarizeDeps]) -> str:
    return "## Active User Profile\n\n" + ctx.deps.user_profile.markdown

@summarize_week_agent.instructions
def _inject_tier0_facts(ctx: RunContext[SummarizeDeps]) -> str:
    return (
        "## Deterministic Tier-0 Facts (treat as ground truth — do not regenerate)\n\n"
        f"### Tier-0 partial summary\n```json\n{ctx.deps.tier0_summary_json}\n```\n"
    )


@summarize_week_agent.instructions
def _inject_raw_sessions(ctx: RunContext[SummarizeDeps]) -> str:
    return ctx.deps.raw_sessions_markdown


@summarize_week_agent.instructions
def _inject_planned_sessions(ctx: RunContext[SummarizeDeps]) -> str:
    if not ctx.deps.planned_plan_markdown:
        return ""
    return (
        "## Planned Sessions (source for plan_adherence — fill if present)\n\n"
        + ctx.deps.planned_plan_markdown
    )


@summarize_week_agent.instructions
def _inject_plan_state(ctx: RunContext[SummarizeDeps]) -> str:
    if not ctx.deps.plan_state_raw:
        return ""
    return (
        "## Existing PLAN_STATE (progression context — do not modify PLAN_STATE fields)\n\n"
        + ctx.deps.plan_state_raw
    )
