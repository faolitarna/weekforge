import re
from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from weekforge.agents.openai_model_factory import build_openai_model
from weekforge.agents.prompt_composer import compose_static_instructions
from weekforge.config.env import settings
from weekforge.config.llm_profiles import resolve_llm_profile
from weekforge.models.user_profile import UserProfile
from weekforge.models.week_plan import WeekPlan
from weekforge.prompts.loader import Prompt
from weekforge.tools.notion_api_gateway import get_page_title
from weekforge.tools.plan_state import PlanState

_PAIN_KEYWORDS = re.compile(
    r"\b(SI|spine|flare|pain|tendon|joint)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class WeekFeedbackRow:
    week_prefix: str
    plan_md: str | None
    summary_text: str | None


@dataclass(frozen=True)
class DraftWeekDeps:
    week_prefix: str
    template_sessions: list[dict]
    feedback_window: list[WeekFeedbackRow]
    plan_state: PlanState | None
    plan_state_raw: str | None
    user_profile: UserProfile
    active_flare: bool
    bootstrap: bool


def derive_active_flare(
    feedback_window: list[WeekFeedbackRow],
    plan_state: PlanState | None,
) -> bool:
    recent_pain = False
    if feedback_window:
        most_recent = feedback_window[-1]  # caller must pass rows in chronological order
        if most_recent.summary_text and _PAIN_KEYWORDS.search(most_recent.summary_text):
            recent_pain = True

    chronic_active_issue = False
    if plan_state and plan_state.active_issues:
        for issue in plan_state.active_issues:
            if _PAIN_KEYWORDS.search(issue):
                chronic_active_issue = True
                break

    return recent_pain or chronic_active_issue


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
    return "## Active User Profile\n\n" + ctx.deps.user_profile.markdown


@draft_week_agent.instructions
def _inject_templates(ctx: RunContext[DraftWeekDeps]) -> str:
    if not ctx.deps.template_sessions:
        return ""
    lines = ["## Template Sessions\n"]
    for t in ctx.deps.template_sessions:
        title = get_page_title(t)
        lines.append(f"### {title}")
        for prop_name, prop_val in t.get("properties", {}).items():
            if prop_val.get("type") == "title":
                continue
            text = _extract_prop_text(prop_val)
            if text:
                lines.append(f"{prop_name}: {text}")
        lines.append("")
    return "\n".join(lines)


def _extract_prop_text(prop: dict) -> str:
    ptype = prop.get("type", "")
    if ptype == "rich_text":
        return "".join(item.get("plain_text", "") for item in prop.get("rich_text", []))
    if ptype == "number":
        val = prop.get("number")
        return str(val) if val is not None else ""
    if ptype == "date":
        d = prop.get("date")
        return d.get("start", "") if d else ""
    return ""


@draft_week_agent.instructions
def _inject_feedback_window(ctx: RunContext[DraftWeekDeps]) -> str:
    if not ctx.deps.feedback_window:
        return ""
    lines = ["## Previous Weeks Feedback\n"]
    for row in ctx.deps.feedback_window:
        lines.append(f"### {row.week_prefix}")
        if row.plan_md:
            lines.append(f"Plan:\n{row.plan_md}")
        if row.summary_text:
            lines.append(f"Summary:\n{row.summary_text}")
        lines.append("")
    return "\n".join(lines)


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
