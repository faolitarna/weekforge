"""Deterministic string formatters shared across CLI, workflows, and Notion layers.

Tier-0: pure functions, no I/O, no LLM calls. Anything that turns a typed value
into a canonical string representation (or back) lives here. Keep functions
narrow and total — raise on invalid input rather than returning fallback strings,
so callers can trust the output format.

Current scope: week identifiers. Extend with date, cadence, zone labels, etc.
as they're needed. If a formatter grows a non-trivial parsing counterpart,
consider splitting into `parsing.py` at that point.
"""


def format_week_prefix(week: int) -> str:
    """Zero-pad to 2 digits with 'W' prefix. 7 -> 'W07', 12 -> 'W12'."""
    if not 1 <= week <= 99:
        raise ValueError(f"week must be in [1, 99], got {week}")
    return f"W{week:02d}"
