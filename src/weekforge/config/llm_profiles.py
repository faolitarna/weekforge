from dataclasses import dataclass
from typing import Literal

from weekforge.config.env import settings


@dataclass(frozen=True)
class LLMProfile:
    provider: str
    model: str
    temperature: float | None = None
    reasoning_effort: Literal["low", "medium", "high"] | None = None


LLM_PROFILES: dict[str, LLMProfile] = {
    "gpt-5.4-nano": LLMProfile(
        provider="openai",
        model="gpt-5.4-nano",
        temperature=0.1,
    ),
    "gpt-5.4-mini": LLMProfile(
        provider="openai",
        model="gpt-5.4-mini",
        temperature=0.1,
    ),
    "gpt-5.4-medium": LLMProfile(
        provider="openai",
        model="gpt-5.4",
        reasoning_effort="medium",
    ),
    "gpt-5.4-low": LLMProfile(
        provider="openai",
        model="gpt-5.4",
        reasoning_effort="low",
    ),
}


def resolve_llm_profile(task_class: Literal["fast", "reasoning"]) -> LLMProfile:
    """Resolve task class to LLMProfile via env-configured profile name.

    Raises KeyError if the env-configured name is absent from LLM_PROFILES — no fallback.
    """
    profile_name: str = getattr(settings, f"{task_class}_profile")
    if profile_name not in LLM_PROFILES:
        raise KeyError(
            f"LLM profile {profile_name!r} not found. "
            f"Available: {sorted(LLM_PROFILES)}"
        )
    return LLM_PROFILES[profile_name]
