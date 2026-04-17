from weekforge.models.llm_call_cost import CallMetadata, RunCost


def _meta(input_t: int = 100, output_t: int = 50, latency: int = 250) -> CallMetadata:
    return CallMetadata(
        input_tokens=input_t,
        output_tokens=output_t,
        latency_ms=latency,
        model_used="gpt-5.4",
    )


def test_run_cost_accumulates_across_calls() -> None:
    """Why test: RunCost is the single source of truth for what the CLI displays
    at run completion — a broken accumulator would silently under-report cost."""
    cost = RunCost()
    cost.add(_meta(input_t=100, output_t=50, latency=200))
    cost.add(_meta(input_t=80, output_t=30, latency=150))

    assert cost.total_input_tokens == 180
    assert cost.total_output_tokens == 80
    assert cost.total_latency_ms == 350
    assert cost.call_count == 2
    assert cost.total_cost_eur == 0.0  # _meta() uses default cost_eur=0.0


def test_run_cost_summary_contains_totals() -> None:
    """Why test: summary is user-facing; drift in format would break AuDHD-informed
    predictability of the run-completion panel."""
    cost = RunCost()
    cost.add(_meta(input_t=123, output_t=456, latency=1500))

    summary = cost.summary()

    assert "123" in summary
    assert "456" in summary
    assert "1.50s" in summary  # 1500ms -> 1.50s
    assert "Calls:" in summary
    assert "Cost:" in summary


def test_run_cost_zero_calls_summary_is_well_formed() -> None:
    """Why test: an empty run (agent skipped, or pre-first-call render) must not crash."""
    summary = RunCost().summary()

    assert "0" in summary
    assert "0.00s" in summary
