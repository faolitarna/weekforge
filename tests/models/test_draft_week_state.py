from weekforge.models.workflow_state import DraftWeekState


def test_draft_week_state_defaults():
    state = DraftWeekState(week_prefix="W15")
    assert state.step == "overwrite_check"
    assert state.week_prefix == "W15"
    assert state.messages_json == []
    assert state.calls == []
    assert state.last_output is None
    assert state.pending_feedback is None
    assert state.validation_retry_used is False
    assert state.validation_warning is None
    assert state.written_page_id is None
    assert state.is_bootstrap is None
    assert state.plan_state_raw is None
    assert state.plan_state_page_id is None
    assert state.started_at is not None


def test_draft_week_state_roundtrip():
    state = DraftWeekState(week_prefix="W07")
    json_str = state.model_dump_json()
    restored = DraftWeekState.model_validate_json(json_str)
    assert restored.week_prefix == "W07"
    assert restored.step == "overwrite_check"
    assert restored.started_at == state.started_at
