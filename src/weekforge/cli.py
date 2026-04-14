import uuid
from typing import Any

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

def _get_or_run_graph(graph_app: Any, config: RunnableConfig, initial_state: Any) -> Any | None:
    """Helper to start a new graph or get the current paused state."""
    current_state = graph_app.get_state(config)
    
    if not current_state.next and not current_state.values:
        thread_id = config["configurable"]["thread_id"]
        console.print(f"[dim]Starting new graph run on thread '{thread_id}'...[/dim]")
        for _ in graph_app.stream(initial_state, config=config, stream_mode="values"):
            pass 
        return graph_app.get_state(config)
        
    if not current_state.next and current_state.values:
         console.print(Panel("Graph is already complete for this thread.", style="bold blue"))
         return None
         
    thread_id = config["configurable"]["thread_id"]
    console.print(f"[yellow]Resuming existing run on thread '{thread_id}'...[/yellow]")
    return current_state


def _prompt_hitl_authorization(panel_content: str, prompt_msg: str) -> bool:
    """Helper to show the standard HAL 9000 themed HITL authorization panel."""
    console.print(Panel(panel_content, title="Human Authorization Required", border_style="#FFA500"))
    return Confirm.ask(prompt_msg)

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
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
    
    current_state = _get_or_run_graph(graph_app, config, State(message=message))
    if current_state is None:
        return
        
    # Check if we are paused at our HITL point
    if current_state.tasks and current_state.tasks[0].interrupts:
        current_message = current_state.values.get("message", "No message found")
        
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
        
        if _prompt_hitl_authorization(panel_content, "Do you want to complete the graph?"):
            console.print("[green]Proceeding...[/green]")
            from langgraph.types import Command
            for _ in graph_app.stream(Command(resume=True), config=config, stream_mode="values"):
                pass
            console.print(Panel("Graph Complete!", style="bold green"))
        else:
            console.print(f"[yellow]Run paused. To resume, run:[/yellow]\n[bold cyan]uv run weekforge echo --thread-id {thread_id}[/bold cyan]")

@app.command()
def notion_test(
    database_id: str | None = typer.Option(None, help="Notion Database ID for testing"),
    thread_id: str | None = typer.Option(None, help="Thread ID to resume. If omitted, starts a new run.")
) -> None:
    """
    Start or resume the Notion Tool Layer test graph (Step 0b).
    """
    from rich.table import Table

    from weekforge.config.env import settings
    from weekforge.graph.notion_test import NotionTestState, create_graph
    
    notion_app = create_graph()

    if database_id is None:
        database_id = settings.notion_test_db_id
        
    if not database_id:
        console.print("[bold red]Error:[/bold red] --database-id not provided and NOTION_TEST_DB_ID not set in environment.")
        raise typer.Exit(code=1)

    if thread_id is None:
        thread_id = str(uuid.uuid4())
        
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    
    current_state = _get_or_run_graph(notion_app, config, NotionTestState(database_id=database_id))
    if current_state is None:
         return
    
    tasks = current_state.tasks
    if tasks and tasks[0].interrupts:
        interrupt_payload = tasks[0].interrupts[0].value
        
        table = Table(title="Queried Notion Records")
        table.add_column("Record ID", style="cyan")
        table.add_column("URL", style="magenta")
        table.add_column("Created Time", style="green")

        for rec in interrupt_payload.get("records_sample", []):
            table.add_row(rec.get("id", "Unknown"), rec.get("url", "No URL"), rec.get("created_time", "Unknown"))
            
        console.print(table)
        
        panel_content = (
            f"[bold cyan]Action required:[/bold cyan] {interrupt_payload.get('action')}\n"
            f"Found {interrupt_payload.get('record_count')} records.\n\n"
            f"Do you want to proceed and [green]WRITE[/green] a test record to this database?"
        )
        
        if _prompt_hitl_authorization(panel_content, "Proceed with write?"):
            console.print("[green]Writing to Notion...[/green]")
            from langgraph.types import Command
            for _ in notion_app.stream(Command(resume={"approved": True}), config=config, stream_mode="values"):
                pass
                
            final_state = notion_app.get_state(config)
            created_id = final_state.values.get("created_page_id")
            console.print(Panel(f"Graph Complete! Created Page URL/ID: {created_id}", style="bold green"))
        else:
            from langgraph.types import Command
            notion_app.invoke(Command(resume={"approved": False}), config=config)
            console.print("[yellow]Cancelled test write.[/yellow]")


if __name__ == "__main__":
    app()
