import pytest

from weekforge.tools.formatting import format_week_prefix


def test_single_digit_week() -> None:
    assert format_week_prefix(7) == "W07"


def test_double_digit_week() -> None:
    assert format_week_prefix(12) == "W12"


def test_boundary_low() -> None:
    assert format_week_prefix(1) == "W01"


def test_boundary_high() -> None:
    assert format_week_prefix(99) == "W99"


def test_zero_raises() -> None:
    with pytest.raises(ValueError, match="week must be in"):
        format_week_prefix(0)


def test_out_of_range_high_raises() -> None:
    with pytest.raises(ValueError, match="week must be in"):
        format_week_prefix(100)
