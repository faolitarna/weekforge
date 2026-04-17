from weekforge.agents.prompt_composer import (
    CAVEMAN_LITE_DIRECTIVE,
    compose_system_prompt,
)


def test_compose_flag_false_returns_base_unchanged() -> None:
    """Why test: baseline contract — CAVEMAN_MODE=false must be a no-op."""
    assert compose_system_prompt("base prompt", False) == "base prompt"


def test_compose_flag_true_appends_directive() -> None:
    """Why test: verifies exact separator and directive text — wrong separator
    breaks the visual block separation when models echo the prompt."""
    result = compose_system_prompt("base prompt", True)
    assert result == "base prompt" + "\n\n" + CAVEMAN_LITE_DIRECTIVE


def test_compose_flag_true_contains_base() -> None:
    """Why test: guards against composer returning only the directive (dropping base)."""
    result = compose_system_prompt("my base", True)
    assert result.startswith("my base")
