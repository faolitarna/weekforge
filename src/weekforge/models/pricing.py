"""Per-model pricing table and EUR cost estimator."""
import logging

logger = logging.getLogger(__name__)

# (input_usd_per_mtok, output_usd_per_mtok)
PRICING: dict[str, tuple[float, float]] = {
    "gpt-5.4":      (2.50, 15.00),
    "gpt-5.4-mini": (0.75,  4.50),
    "gpt-5.4-nano": (0.20,  1.25),
}
USD_TO_EUR: float = 0.92


def estimate_cost_eur(model: str, input_tokens: int, output_tokens: int) -> float:
    """Unknown model returns 0.0 + warning; pricing drift must not crash runs."""
    if model not in PRICING:
        logger.warning("No pricing data for model %r; cost_eur will be 0.0", model)
        return 0.0
    in_rate, out_rate = PRICING[model]
    usd = (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000
    return round(usd * USD_TO_EUR, 6)
