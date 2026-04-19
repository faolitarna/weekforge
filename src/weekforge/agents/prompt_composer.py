CAVEMAN_LITE_DIRECTIVE = """\
Response style — caveman-lite:
- Drop filler (just, really, basically, simply, actually) and hedging (maybe, I think, perhaps).
- No pleasantries (sure, happy to, of course).
- Keep articles, full sentences, proper grammar. Stay professional and polished.
- Apply this style to natural-language text fields only. Preserve any structured
  output schema exactly as specified."""


def compose_system_prompt(base: str, caveman_mode: bool) -> str:
    """Pure composer: returns base unchanged when flag is False."""
    if not caveman_mode:
        return base
    return base + "\n\n" + CAVEMAN_LITE_DIRECTIVE

def compose_static_instructions(caveman_mode: bool) -> str:
    """Concatenate coaching persona + guardrails + (optional) caveman directive.
    Passed to Agent(instructions=...) — static, known at construction time,
    eligible for prompt-cache prefix."""
    from weekforge.prompts.loader import load_prompt, Prompt
    sections = [
        "## Coaching Persona\n\n" + load_prompt(Prompt.COACHING_PERSONA),
        "## Safety Guardrails\n\n" + load_prompt(Prompt.COACHING_GUARDRAILS),
    ]
    if caveman_mode:
        sections.append(CAVEMAN_LITE_DIRECTIVE)
    return "\n\n---\n\n".join(sections)
