from weekforge.agents.prompt_composer import (
    compose_static_instructions,
    compose_system_prompt,
)
from weekforge.prompts.loader import Prompt, load_prompt


def test_compose_flag_false_returns_base_unchanged() -> None:
    """Why test: baseline contract — CAVEMAN_MODE=false must be a no-op."""
    assert compose_system_prompt("base prompt", False) == "base prompt"


def test_compose_flag_true_appends_directive() -> None:
    """Why test: verifies exact separator and directive text — wrong separator
    breaks the visual block separation when models echo the prompt."""
    caveman_text = load_prompt(Prompt.CAVEMAN_LITE_DIRECTIVE)
    result = compose_system_prompt("base prompt", True)
    assert result == "base prompt" + "\n\n" + caveman_text


def test_compose_flag_true_contains_base() -> None:
    """Why test: guards against composer returning only the directive (dropping base)."""
    result = compose_system_prompt("my base", True)
    assert result.startswith("my base")


def test_static_instructions_include_feedback_interpretation() -> None:
    result = compose_static_instructions(Prompt.SUMMARIZE_WEEK_TASK, caveman_mode=False)
    assert "Feedback Interpretation" in result
    assert "explicit-signals" in result


def test_static_instructions_include_all_sections() -> None:
    result = compose_static_instructions(Prompt.SUMMARIZE_WEEK_TASK, caveman_mode=False)
    assert "Coaching Persona" in result
    assert "Safety Guardrails" in result
    assert "Feedback Interpretation" in result
    assert "Progression Protocol" in result
    assert "summarize-task" in result or "Task Instructions" in result


def test_static_instructions_differ_by_task() -> None:
    summarize = compose_static_instructions(Prompt.SUMMARIZE_WEEK_TASK, caveman_mode=False)
    plan_state = compose_static_instructions(Prompt.UPDATE_PLAN_STATE_TASK, caveman_mode=False)
    assert "summarize-task" in summarize or "exercise_log" in summarize
    assert "update-plan-state-task" in plan_state or "PLAN_STATE" in plan_state
    assert summarize != plan_state


def test_static_instructions_share_coaching_prefix() -> None:
    """Both agents must share identical coaching prefix for OpenAI prompt cache hits."""
    summarize = compose_static_instructions(Prompt.SUMMARIZE_WEEK_TASK, caveman_mode=False)
    plan_state = compose_static_instructions(Prompt.UPDATE_PLAN_STATE_TASK, caveman_mode=False)
    sep = "\n\n---\n\n## Task Instructions"
    summarize_prefix = summarize.split(sep)[0]
    plan_state_prefix = plan_state.split(sep)[0]
    assert summarize_prefix == plan_state_prefix
