import functools
import importlib.resources
from enum import StrEnum


class Prompt(StrEnum):
    COACHING_PERSONA = "coaching_persona.md"
    COACHING_GUARDRAILS = "coaching_guardrails.md"


@functools.cache
def load_prompt(prompt: Prompt) -> str:
    return (
        importlib.resources.files("weekforge.prompts")
        .joinpath(prompt.value)
        .read_text(encoding="utf-8")
    )
