from unittest.mock import MagicMock

from pydantic_ai.models import Model

from weekforge.agents import run_with_metadata


def _make_mock_agent(input_tokens: int = 50, output_tokens: int = 20) -> MagicMock:
    mock_usage = MagicMock()
    mock_usage.input_tokens = input_tokens
    mock_usage.output_tokens = output_tokens

    mock_result = MagicMock()
    mock_result.usage.return_value = mock_usage
    mock_result.all_messages.return_value = []

    mock_model = MagicMock(spec=Model)
    mock_model.model_name = "gpt-5.4"

    mock_agent = MagicMock()
    mock_agent.run_sync.return_value = mock_result
    mock_agent.model = mock_model

    return mock_agent


def test_run_with_metadata_captures_token_counts() -> None:
    """Why test: run_with_metadata is the sole bridge between Pydantic AI usage
    data and RunCost — a broken mapping would silently zero-out all token tracking."""
    agent = _make_mock_agent(input_tokens=123, output_tokens=45)

    _, meta, _msgs = run_with_metadata(agent, "test prompt")

    assert meta.input_tokens == 123
    assert meta.output_tokens == 45
    assert meta.model_used == "gpt-5.4"


def test_run_with_metadata_latency_is_non_negative() -> None:
    """Why test: latency_ms feeds the user-facing cost summary; a negative value
    would indicate a perf_counter ordering bug."""
    agent = _make_mock_agent()

    _, meta, _msgs = run_with_metadata(agent, "test prompt")

    assert meta.latency_ms >= 0


def test_run_with_metadata_populates_cost_eur_for_known_model() -> None:
    """Why test: cost_eur must be non-zero for known models — a broken import or
    wrong model_name would silently produce 0.0 in every run summary."""
    agent = _make_mock_agent(input_tokens=1_000_000, output_tokens=1_000_000)
    agent.model.model_name = "gpt-5.4-nano"

    _, meta, _msgs = run_with_metadata(agent, "test prompt")

    assert meta.cost_eur > 0.0


def test_run_with_metadata_raises_on_unresolved_model() -> None:
    """Why test: guards against agents constructed without a Model — would otherwise
    produce a cryptic AttributeError when accessing model_name."""
    agent = _make_mock_agent()
    agent.model = "not-a-model-instance"

    try:
        run_with_metadata(agent, "test prompt")
        assert False, "Expected TypeError"
    except TypeError as exc:
        assert "Expected a resolved Model" in str(exc)
