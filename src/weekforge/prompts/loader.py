import functools
import importlib.resources
from enum import StrEnum


class Prompt(StrEnum):
    COACHING_PERSONA = "coaching_persona.md"
    COACHING_GUARDRAILS = "coaching_guardrails.md"
    FEEDBACK_INTERPRETATION = "feedback-interpretation.md"
    SUMMARIZE_WEEK_TASK = "summarize-week-task.md"
    UPDATE_PLAN_STATE_TASK = "update-plan-state-task.md"
    PROGRESSION_PROTOCOL = "progression-protocol.md"
    CAVEMAN_LITE_DIRECTIVE = "caveman-lite-directive.md"
    DRAFT_WEEK_TASK = "draft-week-task.md"


@functools.cache
def load_prompt(prompt: Prompt) -> str:
    return (
        importlib.resources.files("weekforge.prompts")
        .joinpath(prompt.value)
        .read_text(encoding="utf-8")
    )
