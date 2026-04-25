CAVEMAN_LITE_DIRECTIVE = """\
Response style — caveman-lite:
- Drop filler (just, really, basically, simply, actually) and hedging (maybe, I think, perhaps).
- No pleasantries (sure, happy to, of course).
- Keep articles, full sentences, proper grammar. Stay professional and polished.
- Apply this style to natural-language text fields only. Preserve any structured
  output schema exactly as specified."""


def compose_system_prompt(base: str, caveman_mode: bool) -> str:
    if not caveman_mode:
        return base
    return base + "\n\n" + CAVEMAN_LITE_DIRECTIVE

def compose_static_instructions(caveman_mode: bool) -> str:
    """Passed to Agent(instructions=...) — static prefix is cache-eligible.
    Dynamic context (user profile, Tier-0 facts) comes from @agent.instructions decorators."""
    from weekforge.prompts.loader import Prompt, load_prompt
    sections = [
        "## Coaching Persona\n\n" + load_prompt(Prompt.COACHING_PERSONA),
        "## Safety Guardrails\n\n" + load_prompt(Prompt.COACHING_GUARDRAILS),
        "## Feedback Interpretation\n\n" + load_prompt(Prompt.FEEDBACK_INTERPRETATION),
        "## Progression Protocol\n\n" + load_prompt(Prompt.PROGRESSION_PROTOCOL),
        "## Task Instructions\n\n" + load_prompt(Prompt.SUMMARIZE_WEEK_TASK),
    ]
    if caveman_mode:
        sections.append(CAVEMAN_LITE_DIRECTIVE)
    return "\n\n---\n\n".join(sections)
