import uuid

import typer
from langchain_core.runnables import RunnableConfig
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from weekforge.graph.echo import app as graph_app
from weekforge.models.state import State

app = typer.Typer(
    help="Weekforge - LangGraph-based training week lifecycle manager."
)
console = Console()

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Weekforge CLI - Show available commands if no subcommand is given.
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())

@app.command()
def echo(
    message: str = typer.Option("Testing LangGraph", help="Message to echo"),
    thread_id: str | None = typer.Option(None, help="Thread ID to resume. If omitted, starts a new run.")
) -> None:
    """
    Start or resume the echo graph.
    
    This command demonstrates the HITL (Human-in-the-Loop) pattern:
    1. It checks if the graph is currently paused.
    2. If not, it starts the graph until it hits an interrupt.
    3. It presents a Rich panel for the user to confirm.
    4. Upon confirmation, it resumes the graph.
    """
    if thread_id is None:
        thread_id = str(uuid.uuid4())
        
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    
    # Check current state from the checkpointer
    current_state = graph_app.get_state(config)
    assert current_state is not None
    
    if not current_state.next and not current_state.values:
        # No history, start fresh
        console.print(f"[dim]Starting new graph run on thread '{thread_id}'...[/dim]")
        
        # State uses Pydantic
        initial_state = State(message=message)
        
        # Run until the interrupt
        for chunk in graph_app.stream(initial_state, config=config, stream_mode="values"):
            pass 
        
        # Refresh state
        current_state = graph_app.get_state(config)

    elif not current_state.next and current_state.values:
         # It's already complete!
         console.print(Panel("Graph is already complete for this thread.", style="bold blue"))
         return
    else:
        console.print(f"[yellow]Resuming existing run on thread '{thread_id}'...[/yellow]")
        
    
    # Check if we are paused at our HITL point
    if "complete" in current_state.next:
        # Extract the echoed message from the state
        current_message = current_state.values.get("message", "No message found")
        
        # Display the HITL interface as per spec
        panel_content = (
            f"[bold cyan]Context:[/bold cyan]\n"
            f"The graph successfully ran the echo node.\n"
            f"Current state message: '{current_message}'\n\n"
            f"[bold cyan]Options:[/bold cyan]\n"
            f"- [green]Yes[/green]: Advance the graph to Terminal/Complete state.\n"
            f"- [red]No[/red]: Keep it paused (you can kill the terminal and resume later).\n\n"
            f"[bold cyan]Recommendation:[/bold cyan]\n"
            f"Say Yes to verify the checkpoint resume logic."
        )
        
        console.print(Panel(panel_content, title="Human-in-the-Loop Required", border_style="#FFA500"))
        
        if Confirm.ask("Do you want to complete the graph?"):
            console.print("[green]Proceeding...[/green]")
            # Resume the graph with no new input
            for chunk in graph_app.stream(input=None, config=config, stream_mode="values"):
                pass
            console.print(Panel("Graph Complete!", style="bold green"))
        else:
            console.print(f"[yellow]Run paused. To resume, run:[/yellow]\n[bold cyan]uv run weekforge echo --thread-id {thread_id}[/bold cyan]")

if __name__ == "__main__":
    app()
