from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from weekforge.agents.openai_model_factory import build_openai_model
from weekforge.agents.prompt_composer import compose_static_instructions
from weekforge.config.env import settings
from weekforge.config.llm_profiles import resolve_llm_profile
from weekforge.models.user_profile import UserProfile
from weekforge.models.week_summary import WeekSummary, ImplicitFeedback, PlanAdherence

@dataclass
class SummarizeDeps:
    user_profile: UserProfile
    implicit_feedback: ImplicitFeedback
    plan_adherence: PlanAdherence | None
    tier0_summary_json: str           # WeekSummary partial, serialized as JSON for the prompt

_BASE_TASK_INSTRUCTIONS = """\
You are generating a weekly training summary. The user has already provided:
- Their coaching persona and safety guardrails (above).
- Their active user profile (conditions, HR zones, preferences).
- Deterministic facts computed from Notion: per-exercise log, completion rates, delta analysis.

Your job is to fill the narrative fields of the WeekSummary output:
- `context`: external factors mentioned in comments (illness, travel, equipment limits).
- `issues`: what didn't work or needs changing (synthesize from comments + skip patterns).
- `wins`: what worked well (synthesize from completion + positive comments).
- `recommendations_next`: concrete, coach-voiced suggestions for next week.
- `highlights`: 3–5 bullets for quick user review in the accept panel.
- `trend`: one sentence capturing week-over-week direction.

Do NOT recompute or modify deterministic fields (`sessions`, `exercise_log`, `implicit_feedback`,
`plan_adherence`, etc.). Copy them through unchanged from the input.
"""

_model, _model_settings = build_openai_model(resolve_llm_profile("reasoning"))

summarize_agent = Agent(
    model=_model,
    model_settings=_model_settings,
    instructions=compose_static_instructions(settings.caveman_mode) + "\n\n---\n\n" + _BASE_TASK_INSTRUCTIONS,
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
