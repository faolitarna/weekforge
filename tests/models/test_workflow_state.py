from weekforge.models.workflow_state import State


def test_state_default_message() -> None:
    """Why test: ensure default state meets base initialization requirements."""
    state = State()
    assert state.message == ""


def test_state_assignment() -> None:
    """Why test: ensure Pydantic enforces types on the base schema."""
    state = State(message="test message")
    assert state.message == "test message"
