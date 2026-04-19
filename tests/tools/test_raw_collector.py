import pytest
from unittest.mock import MagicMock

from weekforge.tools.raw_session_collector import (
    collect_blocks,
    compute_checkbox_analysis,
    assemble_raw_week,
)
from weekforge.models.raw_week_data import RawBlock, RawSession


def _make_to_do_block(text: str, checked: bool) -> dict:
    return {
        "type": "to_do",
        "to_do": {
            "rich_text": [{"plain_text": text}],
            "checked": checked,
        },
    }


def _make_heading_block(level: int, text: str) -> dict:
    block_type = f"heading_{level}"
    return {
        "type": block_type,
        block_type: {"rich_text": [{"plain_text": text}]},
    }


def _notion_client_returning(blocks: list[dict]) -> MagicMock:
    client = MagicMock()
    client.blocks.children.list.return_value = {"results": blocks, "has_more": False}
    client.comments.list.return_value = {"results": []}
    return client


# ---------------------------------------------------------------------------
# collect_blocks
# ---------------------------------------------------------------------------


def test_collect_blocks_extracts_text():
    block = _make_to_do_block("Squat 5x5", True)
    client = _notion_client_returning([block])
    result = collect_blocks("page-1", client)
    assert len(result) == 1
    assert result[0].text == "Squat 5x5"
    assert result[0].block_type == "to_do"


def test_collect_blocks_checked_state():
    blocks = [_make_to_do_block("Press", True), _make_to_do_block("Row", False)]
    client = _notion_client_returning(blocks)
    result = collect_blocks("page-1", client)
    assert result[0].checked is True
    assert result[1].checked is False


def test_collect_blocks_no_keyerror_on_missing_fields():
    malformed = {"type": "to_do", "to_do": {}}  # no rich_text, no checked
    client = _notion_client_returning([malformed])
    result = collect_blocks("page-1", client)
    assert result[0].text == ""
    assert result[0].checked is False


# ---------------------------------------------------------------------------
# compute_checkbox_analysis
# ---------------------------------------------------------------------------


def _sessions_with_blocks(session_defs: list[tuple[str, list[RawBlock]]]) -> list[RawSession]:
    return [RawSession(page_id=f"p{i}", name=name, blocks=blocks) for i, (name, blocks) in enumerate(session_defs)]


def _todo(text: str, checked: bool) -> RawBlock:
    return RawBlock(block_type="to_do", text=text, checked=checked, raw={})


def _heading(level: int, text: str) -> RawBlock:
    return RawBlock(block_type=f"heading_{level}", text=text, checked=None, raw={})


def test_compute_checkbox_analysis_counts():
    sessions = _sessions_with_blocks([
        ("Mon", [_todo("A", True), _todo("B", False), _todo("C", True)]),
        ("Wed", [_todo("A", False), _todo("B", True)]),
        ("Fri", [_todo("C", True)]),
    ])
    result = compute_checkbox_analysis(sessions)
    assert result.total_checked == 4
    assert result.total_exercises == 6
    assert ("Mon", 2, 3) in result.per_session
    assert ("Wed", 1, 2) in result.per_session
    assert ("Fri", 1, 1) in result.per_session


def test_compute_checkbox_analysis_section_rates():
    sessions = _sessions_with_blocks([
        ("Mon", [
            _heading(2, "Warmup"),
            _todo("Jog", True),
            _todo("Stretch", False),
            _heading(2, "Main"),
            _todo("Squat", True),
            _todo("Press", True),
        ]),
    ])
    result = compute_checkbox_analysis(sessions)
    # warmup: 1/2 = 0.5, main: 2/2 = 1.0
    assert result.section_rates.warmup_pct == pytest.approx(0.5)
    assert result.section_rates.main_pct == pytest.approx(1.0)
    assert result.section_rates.cooldown_pct == pytest.approx(0.0)


def test_compute_checkbox_analysis_frequently_skipped():
    # "Squat" unchecked 2/3 times → skip_rate = 0.667 > 0.5
    sessions = _sessions_with_blocks([
        ("Mon", [_todo("Squat", False)]),
        ("Wed", [_todo("Squat", False)]),
        ("Fri", [_todo("Squat", True)]),
    ])
    result = compute_checkbox_analysis(sessions)
    names = [p.exercise for p in result.frequently_skipped]
    assert "Squat" in names


def test_compute_checkbox_analysis_always_completed():
    sessions = _sessions_with_blocks([
        ("Mon", [_todo("Deadlift", True)]),
        ("Wed", [_todo("Deadlift", True)]),
    ])
    result = compute_checkbox_analysis(sessions)
    assert "Deadlift" in result.always_completed


# ---------------------------------------------------------------------------
# assemble_raw_week
# ---------------------------------------------------------------------------


def test_assemble_raw_week_empty_raises():
    client = MagicMock()
    with pytest.raises(ValueError, match="2026-W16"):
        assemble_raw_week("2026-W16", [], client, None)
