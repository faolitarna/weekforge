import typer
from rich.console import Console
from rich.panel import Panel

from weekforge.checkpoint import CheckpointStore

console = Console()


def run_summarize_week(week: int, store: CheckpointStore) -> None:
    """Load coaching context (persona, guardrails, user profile) for a given week.

    Aborts early if a summary for the week already exists and the user declines
    to overwrite. Raises NotImplementedError once context is loaded — the summary
    generation body is not yet wired up.
    """
    from weekforge.config.env import settings
    from weekforge.config.user_profile_loader import load_user_profile
    from weekforge.prompts.loader import Prompt, load_prompt
    from weekforge.tools.formatting import format_week_prefix
    from weekforge.tools.notion_api_gateway import query

    week_prefix = format_week_prefix(week)

    # `Week` must be a rich_text column. If it's a title column, this filter
    # silently matches zero rows and the overwrite guard never fires.
    existing = query(
        settings.notion_db_training_week_summaries,
        filters=[{"property": "Week", "rich_text": {"equals": week_prefix}}],
    )
    if existing:
        if not typer.confirm(
            f"Summary for {week_prefix} already exists. Overwrite?", default=False
        ):
            console.print(
                f"[dim]Aborted. Existing summary page: {existing[0]['id']}[/dim]"
            )
            return

    persona = load_prompt(Prompt.COACHING_PERSONA)
    guardrails = load_prompt(Prompt.COACHING_GUARDRAILS)
    profile = load_user_profile()

    console.print(
        Panel(
            f"[bold green]Context ready[/bold green]\n"
            f"Week: {week_prefix}\n"
            f"Profile: loaded ({len(profile.markdown)} chars)\n"
            f"Persona: {len(persona)} chars | Guardrails: {len(guardrails)} chars",
            title="Summarize Context",
            border_style="green",
        )
    )
    raise NotImplementedError("Summary generation body not yet wired up.")
