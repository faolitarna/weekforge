import logging

import pytest

from weekforge.models.pricing import USD_TO_EUR, estimate_cost_eur


def test_known_model_returns_expected_eur() -> None:
    """Why test: estimate_cost_eur is the sole token→cost bridge; a formula error
    would silently produce wrong EUR totals in every run summary."""
    # gpt-5.4-nano: input=0.20/Mtok, output=1.25/Mtok
    # 1_000_000 in + 1_000_000 out = (0.20 + 1.25) USD = 1.45 USD → 1.45 * 0.92 EUR
    expected = round(1.45 * USD_TO_EUR, 6)
    result = estimate_cost_eur("gpt-5.4-nano", 1_000_000, 1_000_000)
    assert result == pytest.approx(expected)


def test_reasoning_model_returns_expected_eur() -> None:
    # gpt-5.4: input=2.50/Mtok, output=15.00/Mtok
    # 500_000 in + 200_000 out = (1.25 + 3.00) USD = 4.25 USD → * 0.92
    expected = round(4.25 * USD_TO_EUR, 6)
    result = estimate_cost_eur("gpt-5.4", 500_000, 200_000)
    assert result == pytest.approx(expected)


def test_unknown_model_returns_zero_with_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Why test: unknown model must not crash; 0.0 fallback is the defined contract."""
    with caplog.at_level(logging.WARNING, logger="weekforge.models.pricing"):
        result = estimate_cost_eur("unknown-model-xyz", 1000, 500)
    assert result == 0.0
    assert "unknown-model-xyz" in caplog.text


def test_zero_tokens_returns_zero() -> None:
    result = estimate_cost_eur("gpt-5.4-nano", 0, 0)
    assert result == 0.0
