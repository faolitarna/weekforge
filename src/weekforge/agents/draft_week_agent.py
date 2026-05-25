import re
from dataclasses import dataclass

from weekforge.models.user_profile import UserProfile
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
