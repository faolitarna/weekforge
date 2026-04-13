from weekforge.models.state import State


def test_state_default_message() -> None:
    """
    Why test: State schema validation.
    Ensure the default state meets our base initialization requirements.
    """
    state = State()
    assert state.message == ""


def test_state_assignment() -> None:
    """
    Why test: State schema validation.
    Ensure Pydantic is enforcing types on the base schema.
    """
    state = State(message="test message")
    assert state.message == "test message"
