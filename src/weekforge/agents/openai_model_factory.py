"""Builds a Pydantic AI `Model` + `ModelSettings` pair from an `LLMProfile`.

Endpoint selection: reasoning-effort profiles go through the Responses API
(`/v1/responses`); OpenAI rejects function-tools + reasoning_effort on the
Chat Completions endpoint. Non-reasoning profiles stay on Chat Completions.

Coupled to OpenAI while `llm_profiles.py` is OpenAI-only; generalize when
another provider lands.
"""
from pydantic_ai.models import Model
from pydantic_ai.models.openai import (
    OpenAIChatModel,
    OpenAIChatModelSettings,
    OpenAIResponsesModel,
    OpenAIResponsesModelSettings,
)
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from weekforge.config.env import settings
from weekforge.config.llm_profiles import LLMProfile


def build_openai_model(profile: LLMProfile) -> tuple[Model, ModelSettings]:
    """Construct the correct OpenAI `Model` + `ModelSettings` for a profile."""
    provider = OpenAIProvider(api_key=settings.openai_api_key)

    if profile.reasoning_effort is not None:
        responses_settings: OpenAIResponsesModelSettings = {
            "openai_reasoning_effort": profile.reasoning_effort,
        }
        return OpenAIResponsesModel(profile.model, provider=provider), responses_settings

    chat_settings: OpenAIChatModelSettings = {}
    if profile.temperature is not None:
        chat_settings["temperature"] = profile.temperature
    return OpenAIChatModel(profile.model, provider=provider), chat_settings
