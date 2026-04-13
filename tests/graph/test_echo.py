from weekforge.graph.echo import echo_node
from weekforge.models.state import State


def test_echo_node_logic() -> None:
    """
    Why test: Tier-0 Logic.
    Ensure the deterministic echo node correctly transforms the incoming state.
    We test the functional node directly rather than the full graph compiled execution.
    """
    state = State(message="hello world")
    result = echo_node(state)
    assert result == {"message": "Echoed: hello world"}
