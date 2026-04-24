from unittest.mock import MagicMock, patch

from weekforge.agents.summarize_agent import SummarizeDeps, summarize_agent
from weekforge.models.user_profile import UserProfile
from weekforge.models.week_summary import ImplicitFeedback, SectionRates, WeekSummary


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
