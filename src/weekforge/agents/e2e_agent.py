"""Single `e2e_agent` instance — enough to validate the config pipeline end-to-end.

Kept inline rather than factored into a builder helper — one agent doesn't warrant
the abstraction.
"""
from pydantic import BaseModel
from pydantic_ai import Agent

from weekforge.agents.openai_model_factory import build_openai_model
from weekforge.agents.prompt_composer import compose_system_prompt
from weekforge.config.env import settings
from weekforge.config.llm_profiles import resolve_llm_profile


class ProcessorResult(BaseModel):
    """Minimum shape that proves structured-output validation works."""
    summary: str


_BASE_PROMPT = (
    "You are a test processor. Given a list of Notion record identifiers, "
    "return a single-sentence synopsis of what you were shown. Keep it under 40 words."
)

_model, _model_settings = build_openai_model(resolve_llm_profile("reasoning"))  # quality-sensitive: validates structured-output pipeline end-to-end

e2e_agent = Agent(
    model=_model,
    model_settings=_model_settings,
    system_prompt=compose_system_prompt(_BASE_PROMPT, settings.caveman_mode),
    output_type=ProcessorResult,
)
