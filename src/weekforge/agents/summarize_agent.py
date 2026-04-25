import json
import logging
from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from weekforge.agents.openai_model_factory import build_openai_model
from weekforge.agents.prompt_composer import compose_static_instructions
from weekforge.config.env import settings
from weekforge.config.llm_profiles import resolve_llm_profile
from weekforge.models.user_profile import UserProfile
from weekforge.models.week_summary import ImplicitFeedback, PlanAdherence, WeekSummary

_logger = logging.getLogger(__name__)


@dataclass
class SummarizeDeps:
    user_profile: UserProfile
    implicit_feedback: ImplicitFeedback
    plan_adherence: PlanAdherence | None
    tier0_summary_json: str
    raw_sessions_json: str = "[]"
    planned_plan_markdown: str | None = None
    plan_state_raw: str | None = None

_model, _model_settings = build_openai_model(resolve_llm_profile("reasoning"))

summarize_agent = Agent(
    model=_model,
    model_settings=_model_settings,
    instructions=compose_static_instructions(settings.caveman_mode),
    deps_type=SummarizeDeps,
    output_type=WeekSummary,
)

@summarize_agent.instructions
def _inject_user_profile(ctx: RunContext[SummarizeDeps]) -> str:
    return "## Active User Profile\n\n" + ctx.deps.user_profile.markdown

@summarize_agent.instructions
def _inject_tier0_facts(ctx: RunContext[SummarizeDeps]) -> str:
    return (
        "## Deterministic Tier-0 Facts (treat as ground truth — do not regenerate)\n\n"
        f"### Tier-0 partial summary\n```json\n{ctx.deps.tier0_summary_json}\n```\n"
    )


_HEADING_TYPES = {"heading_1", "heading_2", "heading_3"}


@summarize_agent.instructions
def _inject_raw_sessions(ctx: RunContext[SummarizeDeps]) -> str:
    try:
        sessions = json.loads(ctx.deps.raw_sessions_json)
    except json.JSONDecodeError:
        _logger.warning("Failed to parse raw_sessions_json — injecting empty section")
        return ""
    if not sessions:
        return ""
    lines = ["## Raw Session Blocks (source for exercise_log, cardio_log, climbing_log)\n"]
    for session in sessions:
        lines.append(f"### {session['name']}")
        comments = session.get("comments", [])
        lines.append(f"Comments: {', '.join(comments) if comments else 'none'}\n")
        for block in session.get("blocks", []):
            bt = block["block_type"]
            if bt in _HEADING_TYPES:  # only heading + to_do — other types add noise without extraction value
                lines.append(block["text"])
            elif bt == "to_do":
                check = "x" if block.get("checked") else " "
                lines.append(f"- [{check}] {block['text']}")
        lines.append("")
    return "\n".join(lines)


@summarize_agent.instructions
def _inject_planned_sessions(ctx: RunContext[SummarizeDeps]) -> str:
    if not ctx.deps.planned_plan_markdown:
        return ""
    return (
        "## Planned Sessions (source for plan_adherence — fill if present)\n\n"
        + ctx.deps.planned_plan_markdown
    )


@summarize_agent.instructions
def _inject_plan_state(ctx: RunContext[SummarizeDeps]) -> str:
    if not ctx.deps.plan_state_raw:
        return ""
    return (
        "## Existing PLAN_STATE (progression context — do not modify PLAN_STATE fields)\n\n"
        + ctx.deps.plan_state_raw
    )
