from weekforge.prompts.loader import Prompt, load_prompt


def compose_system_prompt(base: str, caveman_mode: bool) -> str:
    if not caveman_mode:
        return base
    return base + "\n\n" + load_prompt(Prompt.CAVEMAN_LITE_DIRECTIVE)


def compose_static_instructions(task: Prompt, caveman_mode: bool) -> str:
    """Passed to Agent(instructions=...) — static prefix is cache-eligible.
    Shared coaching context (persona, guardrails, feedback, progression) is identical
    across agents for OpenAI prompt cache hits. Only the task section diverges.
    Dynamic context (user profile, Tier-0 facts) comes from @agent.instructions decorators."""
    sections = [
        "## Coaching Persona\n\n" + load_prompt(Prompt.COACHING_PERSONA),
        "## Safety Guardrails\n\n" + load_prompt(Prompt.COACHING_GUARDRAILS),
        "## Feedback Interpretation\n\n" + load_prompt(Prompt.FEEDBACK_INTERPRETATION),
        "## Progression Protocol\n\n" + load_prompt(Prompt.PROGRESSION_PROTOCOL),
        "## Task Instructions\n\n" + load_prompt(task),
    ]
    if caveman_mode:
        sections.append(load_prompt(Prompt.CAVEMAN_LITE_DIRECTIVE))
    return "\n\n---\n\n".join(sections)
