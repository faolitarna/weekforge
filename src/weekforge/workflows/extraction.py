import logging
from datetime import UTC, datetime
from pydantic_ai.messages import ModelMessagesTypeAdapter
from rich.console import Console
from rich.panel import Panel

from weekforge.agents.agent_run_with_metadata import run_with_metadata
from weekforge.agents.summarize_agent import summarize_agent, SummarizeDeps
from weekforge.checkpoint import CheckpointStore
from weekforge.hitl import hitl_confirm
from weekforge.models.workflow_state import ExtractionState
from weekforge.models.week_summary import WeekSummary
from weekforge.models.llm_call_cost import RunCost

_console = Console()
_logger = logging.getLogger(__name__)
WORKFLOW = "extraction"
MAX_ITERATIONS = 3

def run_summarize(week_prefix: str, thread_id: str, store: CheckpointStore) -> None:
    record = store.load(thread_id)
    if record is not None and record.workflow == WORKFLOW:
        state = ExtractionState.model_validate_json(record.state_json)
    else:
        state = ExtractionState(week_prefix=week_prefix)

    cost = RunCost()
    for c in state.calls:
        cost.add(c)

    while state.step != "done":
        if state.step == "overwrite_check":
            # Placeholder for 1d
            state.step = "load_context"
            store.save(thread_id, WORKFLOW, state.step, state)

        elif state.step == "load_context":
            # Placeholder for context loading
            state.step = "tier0_extract"
            store.save(thread_id, WORKFLOW, state.step, state)

        elif state.step == "tier0_extract":
            # Placeholder for 1b extract. We need a dummy WeekSummary since we don't have it wired yet.
            # In tests, we will inject a state with tier0_summary.
            if not state.tier0_summary:
                # Provide a minimalistic one for testing the agent flow if not present.
                # Actually, the spec for 1c tests says they will feed a canned tier0 summary.
                raise RuntimeError(
                    f"tier0_summary missing for {state.week_prefix}. (1b extraction wire-up missing?)"
                )
            state.step = "agent"
            store.save(thread_id, WORKFLOW, state.step, state)

        elif state.step == "agent":
            store.save(thread_id, WORKFLOW, state.step, state)
            prev = ModelMessagesTypeAdapter.validate_python(state.messages_json) if state.messages_json else None
            
            # The deps injected
            from weekforge.models.user_profile import UserProfile
            from weekforge.models.week_summary import ImplicitFeedback, SectionRates

            # Dummy profile and feedback if not populated in context
            deps = SummarizeDeps(
                user_profile=UserProfile.model_construct(markdown="Not provided"),
                implicit_feedback=ImplicitFeedback(
                    total_checked=0,
                    total_exercises=0,
                    per_session=[],
                    section_rates=SectionRates(warmup_pct=0.0, main_pct=0.0, cooldown_pct=0.0),
                    frequently_skipped=[],
                    always_completed=[]
                ),
                plan_adherence=None,
                tier0_summary_json=state.tier0_summary.model_dump_json(exclude_none=True),
            )

            prompt = f"Summarize week {state.week_prefix}."
            if state.pending_feedback:
                 prompt += f"\nUser feedback: {state.pending_feedback}"

            result, meta, new_messages = run_with_metadata(
                summarize_agent, prompt, deps=deps, message_history=prev
            )
            state.last_output = result.output
            state.messages_json = ModelMessagesTypeAdapter.dump_python(new_messages, mode="json")
            state.calls.append(meta)
            cost.add(meta)
            state.pending_feedback = None
            state.step = "accept"

        elif state.step == "accept":
            assert state.last_output is not None
            
            highlights_text = "\n".join(f"- {h}" for h in state.last_output.highlights)
            trend_text = state.last_output.trend or "N/A"
            iterations = len(state.calls)
            
            context_str = (
                f"[bold]Highlights:[/bold]\n{highlights_text}\n\n"
                f"[bold]Trend:[/bold] {trend_text}\n\n"
            )
            
            if iterations >= MAX_ITERATIONS:
                context_str += "\n[red bold]Token burn warning: reached max iterations. Please accept.[/red bold]\n"
            
            context_str += f"{cost.summary()}"
            
            _console.print(Panel(context_str, title="Agent Highlights Output", border_style="cyan"))
            
            decision = hitl_confirm(
                context=context_str,
                recommendation="Approve writes summary to Notion. Feedback refines. Quit pauses.",
                checkpoint=store,
                thread_id=thread_id,
                workflow=WORKFLOW,
                step="accept",
                state=state,
            )
            
            if decision.approved:
                state.step = "write"
            elif decision.quit:
                _console.print(
                    f"[yellow]Paused.[/yellow] Resume: "
                    f"[bold cyan]uv run weekforge resume --thread-id {thread_id}[/bold cyan]"
                )
                return
            else:
                state.pending_feedback = decision.feedback
                state.step = "agent"

        elif state.step == "write":
            store.save(thread_id, WORKFLOW, state.step, state)
            assert state.last_output is not None
            from weekforge.tools.week_summary_renderer import render_week_summary
            from weekforge.tools import notion_api_gateway as notion
            from weekforge.config.env import settings
            
            rendered = render_week_summary(state.last_output)
            code_block = f"```text\n{rendered}\n```"
            
            _logger.info("Writing week summary to Notion.")
            records = notion.query(
                database_id=settings.notion_db_training_week_summaries,
                filters=[{"property": "Week", "rich_text": {"equals": state.week_prefix}}]
            )
            
            if records:
                page_id = records[0]["id"]
                notion.update(
                    page_id=page_id,
                    properties={"Summary": {"rich_text": [{"text": {"content": "".join(rendered[:2000])}}]}},
                    content=code_block
                )
                state.written_page_id = page_id
            else:
                _logger.warning("No existing row for week %s found! Creating a new one.", state.week_prefix)
                page_id = notion.create(
                    database_id=settings.notion_db_training_week_summaries,
                    properties={
                        "Week": {"rich_text": [{"text": {"content": state.week_prefix}}]},
                        "Name": {"title": [{"text": {"content": f"Week {state.week_prefix} Summary"}}]}, 
                        "Summary": {"rich_text": [{"text": {"content": "".join(rendered[:2000])}}]},
                    },
                    content=code_block
                )
                state.written_page_id = page_id
                
            state.step = "plan_state_check"
            store.save(thread_id, WORKFLOW, state.step, state)

        elif state.step == "plan_state_check":
            store.save(thread_id, WORKFLOW, state.step, state)
            from weekforge.tools import notion_api_gateway as notion
            from weekforge.config.env import settings
            
            _logger.info("Checking PLAN_STATE.")
            records = notion.query(
                database_id=settings.notion_db_training_week_summaries,
                filters=[{"property": "Week", "rich_text": {"equals": "PLAN_STATE"}}]
            )
            
            if records:
                page_id = records[0]["id"]
                page = notion.fetch(page_id)
                content_blocks = page.get("content", [])
                raw_text = ""
                for block in content_blocks:
                    if block["type"] == "code":
                        raw_text += "".join(t["text"]["content"] for t in block["code"]["rich_text"]) + "\n"
                    elif block["type"] == "paragraph" and block.get("paragraph", {}).get("rich_text"):
                        raw_text += "".join(t["text"]["content"] for t in block["paragraph"]["rich_text"]) + "\n"

                state.plan_state_raw = raw_text
                state.plan_state_page_id = page_id
                state.is_bootstrap = False
            else:
                state.is_bootstrap = True
                
            state.step = "plan_state_update"
            store.save(thread_id, WORKFLOW, state.step, state)
            
        elif state.step == "plan_state_update":
            store.save(thread_id, WORKFLOW, state.step, state)
            from weekforge.agents.plan_state_agent import plan_state_agent, PlanStateDeps
            from weekforge.tools.plan_state import render_plan_state, update_mechanical_fields, parse_plan_state, PlanState
            from weekforge.agents.agent_run_with_metadata import run_with_metadata
            from weekforge.tools import notion_api_gateway as notion
            from weekforge.config.env import settings
            
            assert state.is_bootstrap is not None
            
            if not state.is_bootstrap:
                _logger.info("Running incremental PLAN_STATE update.")
                existing_ps = parse_plan_state(state.plan_state_raw or "")
                existing_ps = update_mechanical_fields(existing_ps, state.last_output)
                
                deps = PlanStateDeps(existing_plan_state=existing_ps, new_week=state.last_output)
                prompt = "Update the plan state logically based on the new week."
                result, meta, _ = run_with_metadata(
                    plan_state_agent, prompt, deps=deps, message_history=None
                )
                updated_ps = result.output
                cost.add(meta)
                
                rendered_ps = render_plan_state(updated_ps, state.week_prefix)
                code_block = f"```text\n{rendered_ps}\n```"
                
                assert state.plan_state_page_id is not None
                notion.update(
                    page_id=state.plan_state_page_id,
                    properties={"Name": {"title": [{"text": {"content": f"Plan State - W01-{state.week_prefix}"}}]}},
                    content=code_block
                )
            else:
                _logger.info("Bootstrapping PLAN_STATE.")
                deps = PlanStateDeps(existing_plan_state=PlanState(), all_weeks=[state.last_output])
                prompt = "Bootstrap plan state from provided weeks."
                result, meta, _ = run_with_metadata(
                    plan_state_agent, prompt, deps=deps, message_history=None
                )
                updated_ps = result.output
                cost.add(meta)
                
                rendered_ps = render_plan_state(updated_ps, state.week_prefix)
                code_block = f"```text\n{rendered_ps}\n```"
                
                notion.create(
                    database_id=settings.notion_db_training_week_summaries,
                    properties={
                        "Week": {"rich_text": [{"text": {"content": "PLAN_STATE"}}]},
                        "Name": {"title": [{"text": {"content": f"Plan State - W01-{state.week_prefix}"}}]},
                        "Summary": {"rich_text": [{"text": {"content": "".join(rendered_ps[:2000])}}]},
                    },
                    content=code_block
                )
                
            state.step = "done"
            store.save(thread_id, WORKFLOW, state.step, state)
        
        else:
            raise RuntimeError(f"Unknown step: {state.step!r}")

    store.delete(thread_id)
