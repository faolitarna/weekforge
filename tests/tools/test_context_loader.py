from unittest.mock import patch

import pytest

from weekforge.models.user_profile import UserProfile
from weekforge.tools.context_loader import (
    FeedbackRow,
    WeekDraftContext,
    WeekSummarizeContext,
    _extract_prop_text,
    _format_feedback_window,
    _format_raw_sessions,
    _format_template_pages,
    derive_active_flare,
    load_week_draft_context,
    load_week_summarize_context,
)
from weekforge.tools.plan_state import PlanState


# --- _extract_prop_text ---


class TestExtractPropText:
    def test_rich_text(self):
        prop = {"type": "rich_text", "rich_text": [{"plain_text": "hello"}, {"plain_text": " world"}]}
        assert _extract_prop_text(prop) == "hello world"

    def test_rich_text_empty(self):
        assert _extract_prop_text({"type": "rich_text", "rich_text": []}) == ""

    def test_number(self):
        assert _extract_prop_text({"type": "number", "number": 42}) == "42"

    def test_number_none(self):
        assert _extract_prop_text({"type": "number", "number": None}) == ""

    def test_date(self):
        assert _extract_prop_text({"type": "date", "date": {"start": "2024-06-03"}}) == "2024-06-03"

    def test_date_none(self):
        assert _extract_prop_text({"type": "date", "date": None}) == ""

    def test_unknown_type(self):
        assert _extract_prop_text({"type": "checkbox", "checkbox": True}) == ""


# --- _format_template_pages ---


class TestFormatTemplatePages:
    def test_empty_returns_empty(self):
        assert _format_template_pages([]) == ""

    @patch("weekforge.tools.context_loader.notion")
    def test_formats_templates(self, mock_notion):
        mock_notion.get_page_title.side_effect = lambda p: next(
            v["title"][0]["plain_text"] for v in p["properties"].values() if v.get("type") == "title"
        )
        templates = [
            {
                "id": "t1",
                "properties": {
                    "Title": {"type": "title", "title": [{"plain_text": "W15: Push"}]},
                    "Desc": {"type": "rich_text", "rich_text": [{"plain_text": "Push day"}]},
                    "Duration": {"type": "number", "number": 85},
                },
            },
        ]
        result = _format_template_pages(templates)
        assert "## Template Sessions" in result
        assert "### W15: Push" in result
        assert "Desc: Push day" in result
        assert "Duration: 85" in result
        assert "Title:" not in result


# --- _format_feedback_window ---


class TestFormatFeedbackWindow:
    def test_empty_returns_empty(self):
        assert _format_feedback_window([]) == ""

    def test_renders_rows(self):
        rows = [
            FeedbackRow(week_prefix="W13", plan_md="Plan W13", summary_text="Summary W13"),
            FeedbackRow(week_prefix="W14", plan_md=None, summary_text="Summary W14"),
        ]
        result = _format_feedback_window(rows)
        assert "## Previous Weeks Feedback" in result
        assert "### W13" in result
        assert "Plan:\nPlan W13" in result
        assert "### W14" in result
        assert "Summary W14" in result

    def test_skips_none_fields(self):
        rows = [FeedbackRow(week_prefix="W14", plan_md=None, summary_text=None)]
        result = _format_feedback_window(rows)
        assert "### W14" in result
        assert "Plan:" not in result
        assert "Summary:" not in result


# --- _format_raw_sessions ---


class TestFormatRawSessions:
    def test_empty_returns_empty(self):
        assert _format_raw_sessions([]) == ""

    def test_formats_sessions(self):
        sessions = [
            {
                "name": "Upper A",
                "blocks": [
                    {"block_type": "heading_2", "text": "Warmup", "checked": None},
                    {"block_type": "to_do", "text": "Bar Hangs", "checked": True},
                    {"block_type": "paragraph", "text": "Note", "checked": None},
                    {"block_type": "to_do", "text": "Planks", "checked": False},
                ],
                "comments": ["felt good"],
            }
        ]
        result = _format_raw_sessions(sessions)
        assert "### Upper A" in result
        assert "Warmup" in result
        assert "- [x] Bar Hangs" in result
        assert "- [ ] Planks" in result
        assert "Note" not in result
        assert "felt good" in result

    def test_no_comments_shows_none(self):
        sessions = [{"name": "S", "blocks": [], "comments": []}]
        result = _format_raw_sessions(sessions)
        assert "Comments: none" in result


# --- load_week_draft_context ---


@patch("weekforge.tools.context_loader.load_user_profile")
@patch("weekforge.tools.context_loader.summaries_db")
@patch("weekforge.tools.context_loader.notion")
def test_load_week_draft_context_happy_path(mock_notion, mock_db, mock_profile):
    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_notion.get_page_title.side_effect = lambda p: next(
        v["title"][0]["plain_text"] for v in p["properties"].values() if v.get("type") == "title"
    )

    mock_db.find_summary_row.return_value = None
    mock_db.find_plan_state_row.return_value = ("PLAN_STATE:W01-W14", "ps-id")

    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    ctx = load_week_draft_context("W15")

    assert isinstance(ctx, WeekDraftContext)
    assert "Push" in ctx.template_markdown
    assert ctx.plan_state_raw == "PLAN_STATE:W01-W14"
    assert ctx.plan_state_page_id == "ps-id"
    assert ctx.user_profile_markdown == "# Profile"
    assert ctx.is_bootstrap is True  # no feedback rows


@patch("weekforge.tools.context_loader.load_user_profile")
@patch("weekforge.tools.context_loader.summaries_db")
@patch("weekforge.tools.context_loader.notion")
def test_load_week_draft_context_no_templates_raises(mock_notion, mock_db, mock_profile):
    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W14: Old"}]}}},
    ]
    mock_notion.get_page_title.side_effect = lambda p: next(
        v["title"][0]["plain_text"] for v in p["properties"].values() if v.get("type") == "title"
    )

    with pytest.raises(RuntimeError, match="No template.*W15"):
        load_week_draft_context("W15")


@patch("weekforge.tools.context_loader.load_user_profile")
@patch("weekforge.tools.context_loader.summaries_db")
@patch("weekforge.tools.context_loader.notion")
def test_load_week_draft_context_bootstrap(mock_notion, mock_db, mock_profile):
    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_notion.get_page_title.side_effect = lambda p: next(
        v["title"][0]["plain_text"] for v in p["properties"].values() if v.get("type") == "title"
    )
    mock_db.find_summary_row.return_value = None
    mock_db.find_plan_state_row.return_value = (None, None)
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    ctx = load_week_draft_context("W15")

    assert ctx.is_bootstrap is True
    assert ctx.plan_state_raw is None


@patch("weekforge.tools.context_loader.load_user_profile")
@patch("weekforge.tools.context_loader.summaries_db")
@patch("weekforge.tools.context_loader.notion")
def test_load_week_draft_context_feedback_window_ordering(mock_notion, mock_db, mock_profile):
    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_notion.get_page_title.side_effect = lambda p: next(
        v["title"][0]["plain_text"] for v in p["properties"].values() if v.get("type") == "title"
    )

    def find_row(prefix):
        if prefix in ("W14", "W13", "W12"):
            return {"id": f"s{prefix}"}
        return None

    mock_db.find_summary_row.side_effect = find_row
    mock_db.read_plan_property.return_value = "plan"
    mock_db.read_summary_body.return_value = "body"
    mock_db.find_plan_state_row.return_value = ("PS", "ps-id")
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    ctx = load_week_draft_context("W15")

    # find_summary_row called for W14, W13, W12 (descending scan)
    calls = [c.args[0] for c in mock_db.find_summary_row.call_args_list]
    assert calls == ["W14", "W13", "W12"]
    assert ctx.is_bootstrap is False
    assert "W12" in ctx.feedback_window_markdown
    assert "W14" in ctx.feedback_window_markdown


@patch("weekforge.tools.context_loader.load_user_profile")
@patch("weekforge.tools.context_loader.summaries_db")
@patch("weekforge.tools.context_loader.notion")
def test_load_week_draft_context_week_1_no_scan(mock_notion, mock_db, mock_profile):
    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W01: Day 1"}]}}},
    ]
    mock_notion.get_page_title.side_effect = lambda p: next(
        v["title"][0]["plain_text"] for v in p["properties"].values() if v.get("type") == "title"
    )
    mock_db.find_plan_state_row.return_value = (None, None)
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    ctx = load_week_draft_context("W01")

    assert ctx.is_bootstrap is True
    mock_db.find_summary_row.assert_not_called()


@patch("weekforge.tools.context_loader.load_user_profile")
@patch("weekforge.tools.context_loader.summaries_db")
@patch("weekforge.tools.context_loader.notion")
def test_load_week_draft_context_active_flare(mock_notion, mock_db, mock_profile):
    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_notion.get_page_title.side_effect = lambda p: next(
        v["title"][0]["plain_text"] for v in p["properties"].values() if v.get("type") == "title"
    )
    mock_db.find_summary_row.return_value = {"id": "s14"}
    mock_db.read_plan_property.return_value = None
    mock_db.read_summary_body.return_value = "SI joint pain this week"
    mock_db.find_plan_state_row.return_value = ("PS\nACTIVE_ISSUES:\n- SI joint", "ps-id")
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    ctx = load_week_draft_context("W15")

    assert ctx.active_flare is True


# --- load_week_summarize_context ---


@patch("weekforge.tools.context_loader.load_user_profile")
@patch("weekforge.tools.context_loader.summaries_db")
@patch("weekforge.tools.context_loader.notion")
@patch("weekforge.tools.context_loader.assemble_raw_week")
def test_load_week_summarize_context_happy_path(mock_assemble, mock_notion, mock_db, mock_profile):
    from weekforge.models.raw_week_data import RawBlock, RawSession, RawWeekData

    mock_notion.query.return_value = [
        {"id": "p1", "properties": {"Week": {"type": "rich_text", "rich_text": [{"plain_text": "1"}]}}},
    ]
    mock_notion.get_text_prop.side_effect = lambda p, prop: "1" if prop == "Week" else ""
    mock_db.find_summary_row.return_value = None
    mock_db.find_plan_state_row.return_value = (None, None)
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    raw_session = RawSession(
        page_id="p1", name="Upper A", done=True,
        blocks=[
            RawBlock(block_type="to_do", text="Bench Press", checked=True, raw={}),
            RawBlock(block_type="to_do", text="Rows", checked=False, raw={}),
        ],
        comments=["felt good"],
    )
    mock_assemble.return_value = RawWeekData(
        week_prefix="W01", sessions=[raw_session], planned_plan_markdown=None,
    )

    ctx = load_week_summarize_context("W01")

    assert isinstance(ctx, WeekSummarizeContext)
    assert ctx.tier0_summary.completion == "1/1"
    assert ctx.tier0_summary.implicit_feedback.total_checked == 1
    assert ctx.tier0_summary.implicit_feedback.total_exercises == 2
    assert "Bench Press" in ctx.raw_sessions_markdown
    assert "Rows" in ctx.raw_sessions_markdown
    assert ctx.is_bootstrap is True
    assert ctx.user_profile_markdown == "# Profile"
