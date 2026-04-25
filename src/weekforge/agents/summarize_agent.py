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

_BASE_TASK_INSTRUCTIONS = """\
You are generating a weekly training summary. The user has already provided:
- Their coaching persona and safety guardrails (above).
- Their active user profile (conditions, HR zones, preferences).
- Deterministic facts computed from Notion: per-session checkbox counts, completion rates.
- Raw session blocks with heading + to_do items and comments.

Your job is to fill:
- `exercise_log`: list of ExerciseLogEntry for every training session exercise. Extract from Raw Session Blocks.
  - `planned_weight/sets/reps`: from block text (e.g. "Goblet Squat 3x8 @20kg" → planned_sets=3, planned_reps="8", planned_weight="20kg").
  - `actual_weight/sets/reps`: from comments when user reports deviation from plan. Leave None if no deviation.
  - `status`: `done` if checked with no deviation, `done_modified` if checked but actuals differ from planned, `skip` if unchecked.
  - `role`: classify by these rules:
    - `warmup`: exercise under a heading containing "warmup" or "warm-up"
    - `cooldown`: exercise under a heading containing "cooldown" or "cool-down"
    - `focus`: overrides section for these 10 named exercises: bar hangs, side planks, reverse lunges, multidirectional lunges, bicep curls, elevator press, single arm OHP, carries, X-Press Lat Walk, face pulls, pull-ups
    - `main`: compound/heavy movements in main section
    - `accessory`: isolation/secondary movements in main section
  - `feedback`: comment excerpt relevant to this exercise + optional progression note (e.g. "+2.5kg from WK1") if PLAN_STATE has prior data.
  - `section`: heading text at time of exercise.
- `cardio_log`: list of CardioEntry for cardio sessions. `kind` from session type, `raw` as compact summary string (e.g. "10.5km/493m elevation|60min|avg 131 BPM").
- `climbing_log`: list of ClimbingEntry for climbing sessions. `kind` from session type, `raw` as compact summary string.
- `plan_adherence`: if Planned Sessions section present, compare planned vs actual sessions and fill counts + patterns. If absent, set to None.
- `context`: external factors mentioned in comments (illness, travel, equipment limits).
- `issues`: what didn't work or needs changing (synthesize from comments + skip patterns). Each item must be `"key:details"` format (e.g. `"knee_load:squats aggravated mid-session"`).
- `wins`: what worked well (synthesize from completion + positive comments). Each item must be `"key:details"` format (e.g. `"overhead_strength:elevator press at 14kg steady"`).
- `recommendations_next`: concrete, coach-voiced suggestions for next week.
- `highlights`: 3–5 bullets for quick user review in the accept panel.
- `trend`: one sentence capturing week-over-week direction.
- `pain_status`: list of JointEntry for each joint with a notable status. Each entry: `name` (joint identifier, e.g. `"si_joint"`), `status` (e.g. `"ok"`, `"stiff"`, `"sore"`), optional `triggers` (what provoked symptoms), optional `what_helped`. Omit entries for joints with no data.

Do NOT recompute or modify `sessions` or `implicit_feedback` — copy them through from Tier-0 unchanged.
All other fields listed above are yours to fill from Raw Session Blocks, comments, Planned Sessions, and PLAN_STATE.
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
