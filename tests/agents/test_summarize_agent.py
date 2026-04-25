import json
from unittest.mock import MagicMock, patch

from weekforge.agents.summarize_agent import SummarizeDeps, summarize_agent
from weekforge.models.user_profile import UserProfile
from weekforge.models.week_summary import ImplicitFeedback, SectionRates, SessionLine, WeekSummary


@patch("weekforge.agents.summarize_agent.summarize_agent.run_sync")
def test_summarize_agent(mock_run):
    mock_run.return_value = MagicMock(data=WeekSummary.model_construct(
        highlights=["Test highlight"],
        trend="flat"
    ))
    deps = SummarizeDeps(
        user_profile=UserProfile.model_construct(markdown="test"),
        implicit_feedback=ImplicitFeedback(
            total_checked=0,
            total_exercises=0,
            per_session=[],
            section_rates=SectionRates(warmup_pct=0.0, main_pct=0.0, cooldown_pct=0.0),
            frequently_skipped=[],
            always_completed=[]
        ),
        plan_adherence=None,
        tier0_summary_json="{}",
        raw_sessions_json="[]",
        planned_plan_markdown=None,
        plan_state_raw=None,
    )
    result = summarize_agent.run_sync("test", deps=deps)
    assert isinstance(result.data, WeekSummary)
    assert result.data.highlights == ["Test highlight"]
    assert result.data.trend == "flat"


def test_tier0_serialization_excludes_llm_fields():
    """tier0_summary_json must not carry LLM-owned fields labeled as ground truth.

    Regression: shipping exercise_log=[] inside tier0_summary_json caused the LLM
    to treat the empty list as do-not-regenerate ground truth, producing empty
    EXERCISE_LOG sections in the rendered week summary.
    """
    tier0 = WeekSummary(
        week_prefix="W05",
        completion="3/4",
        sessions=[SessionLine(
            name="Session 1", status="done",
            exercises_done=5, exercises_total=5,
            pain_status=None, comment="",
        )],
        exercise_log=[],
        pain_status=[],
        implicit_feedback=ImplicitFeedback(
            total_checked=5, total_exercises=6, per_session=[],
            section_rates=SectionRates(warmup_pct=1.0, main_pct=0.8, cooldown_pct=0.5),
            frequently_skipped=[], always_completed=[],
        ),
    )

    serialized = tier0.model_dump_json(
        exclude_none=True,
        include={"week_prefix", "completion", "context", "sessions", "implicit_feedback"},
    )
    payload = json.loads(serialized)

    assert "sessions" in payload
    assert "implicit_feedback" in payload
    assert "week_prefix" in payload
    assert "completion" in payload

    for llm_field in ("exercise_log", "cardio_log", "climbing_log", "plan_adherence", "highlights", "trend", "issues", "wins", "recommendations_next"):
        assert llm_field not in payload, f"{llm_field} leaked into tier0_summary_json"
