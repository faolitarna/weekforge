import logging
from typing import Any, Literal

from pydantic_ai.messages import ModelMessagesTypeAdapter
from rich.console import Console
from rich.panel import Panel

from weekforge.agents.agent_run_with_metadata import run_with_metadata
from weekforge.agents.summarize_agent import SummarizeDeps, summarize_agent
from weekforge.checkpoint import CheckpointStore
from weekforge.hitl import hitl_confirm
from weekforge.models.llm_call_cost import RunCost
from weekforge.models.week_summary import WeekSummary
from weekforge.models.workflow_state import SummarizeWeekState

_console = Console()
_logger = logging.getLogger(__name__)
WORKFLOW = "summarize_week"
MAX_ITERATIONS = 3


def _get_text_prop(page: dict[str, Any], prop_name: str) -> str:
    items = page.get("properties", {}).get(prop_name, {}).get("rich_text", [])
    return "".join(item.get("plain_text", "") for item in items)


def run_summarize(week_prefix: str, thread_id: str, store: CheckpointStore) -> None:
    record = store.load(thread_id)
    if record is not None and record.workflow in (WORKFLOW, "extraction"):
        state = SummarizeWeekState.model_validate_json(record.state_json)
    else:
        state = SummarizeWeekState(week_prefix=week_prefix)

    cost = RunCost()
    for c in state.calls:
        cost.add(c)

    while state.step != "done":
        if state.step == "overwrite_check":
            # Placeholder for 1d
            state.step = "load_context"
            store.save(thread_id, WORKFLOW, state.step, state)

        elif state.step == "load_context":
            from weekforge.config.env import settings
            from weekforge.config.user_profile_loader import load_user_profile
            from weekforge.tools import notion_api_gateway as notion
            from weekforge.tools.notion_api_gateway import _client as notion_client
            from weekforge.tools.raw_session_collector import assemble_raw_week

            _logger.info("Loading context for %s", state.week_prefix)

            # Load user profile
            profile = load_user_profile()
            state.user_profile_markdown = profile.markdown

            # Fetch session pages for this week from Notion
            week_num_str = str(int(state.week_prefix[1:]))
            all_session_pages = notion.query(database_id=settings.notion_db_training_sessions)
            session_pages = [p for p in all_session_pages if _get_text_prop(p, "Week") == week_num_str]
            if not session_pages:
                raise RuntimeError(
                    f"No session pages found for {state.week_prefix} in training_sessions DB."
                )

            # Read Plan property from training_week_summaries
            all_summary_pages = notion.query(database_id=settings.notion_db_training_week_summaries)
            plan_records = [p for p in all_summary_pages if _get_text_prop(p, "Week") == state.week_prefix]
            if plan_records:
                plan_text = _get_text_prop(plan_records[0], "Plan")
                state.planned_plan_markdown = plan_text or None
            else:
                state.planned_plan_markdown = None

            # Assemble raw week data
            raw_week = assemble_raw_week(
                week_prefix=state.week_prefix,
                session_pages=session_pages,
                notion_client=notion_client,
                planned_plan_markdown=state.planned_plan_markdown,
            )
            # Serialize sessions for checkpoint persistence (exclude bulky raw block dicts)
            import json
            state.raw_sessions_json = json.dumps([
                {"name": s.name, "page_id": s.page_id, "done": s.done,
                 "blocks": [{"block_type": b.block_type, "text": b.text, "checked": b.checked} for b in s.blocks],
                 "comments": s.comments}
                for s in raw_week.sessions
            ])

            _console.print(f"[green]Loaded {len(raw_week.sessions)} sessions for {state.week_prefix}[/green]")
            state.step = "tier0_extract"
            store.save(thread_id, WORKFLOW, state.step, state)

        elif state.step == "tier0_extract":
            import json

            from weekforge.models.raw_week_data import RawBlock, RawSession
            from weekforge.models.week_summary import SessionLine
            from weekforge.tools.raw_session_collector import compute_checkbox_analysis

            _logger.info("Building tier0 summary for %s", state.week_prefix)

            # Reconstruct sessions from checkpoint-safe JSON
            raw_sessions_data = json.loads(state.raw_sessions_json or "[]")
            sessions = [
                RawSession(
                    page_id=s["page_id"], name=s["name"],
                    blocks=[RawBlock(block_type=b["block_type"], text=b["text"], checked=b["checked"], raw={}) for b in s["blocks"]],
                    comments=s["comments"],
                )
                for s in raw_sessions_data
            ]

            # Compute checkbox analysis (mechanical Tier-0)
            implicit_fb = compute_checkbox_analysis(sessions)

            # Build skeleton session lines
            session_lines = []
            for s_data in raw_sessions_data:
                blocks = s_data["blocks"]
                total = sum(1 for b in blocks if b["block_type"] == "to_do")
                checked = sum(1 for b in blocks if b["block_type"] == "to_do" and b["checked"])
                session_done = s_data.get("done", False)
                status: Literal["done", "skip", "partial"] = "done" if session_done else ("partial" if checked > 0 else "skip")
                raw_comments = s_data.get("comments", [])
                comment_text = " | ".join(raw_comments) if raw_comments else ""
                session_lines.append(SessionLine(
                    name=s_data["name"],
                    status=status,
                    exercises_done=checked,
                    exercises_total=total,
                    pain_status=None,
                    comment=comment_text,
                ))

            done_count = sum(1 for s in raw_sessions_data if s.get("done", False))
            total_count = len(session_lines)
            state.tier0_summary = WeekSummary(
                week_prefix=state.week_prefix,
                completion=f"{done_count}/{total_count}",
                sessions=session_lines,
                exercise_log=[],
                pain_status=[],
                implicit_feedback=implicit_fb,
            )
            _console.print(f"[green]Tier-0 summary: {state.tier0_summary.completion}[/green]")
            state.step = "plan_state_check"
            store.save(thread_id, WORKFLOW, state.step, state)

        elif state.step == "agent":
            _console.print("[dim]agent: calling summarize_agent…[/dim]")
            store.save(thread_id, WORKFLOW, state.step, state)
            prev = ModelMessagesTypeAdapter.validate_python(state.messages_json) if state.messages_json else None

            from weekforge.models.user_profile import UserProfile

            # Use real profile if loaded, fallback for tests
            profile_md = state.user_profile_markdown or "Not provided"
            profile = UserProfile.model_construct(page_id="state", markdown=profile_md)

            assert state.tier0_summary is not None
            deps = SummarizeDeps(
                user_profile=profile,
                implicit_feedback=state.tier0_summary.implicit_feedback,
                plan_adherence=state.tier0_summary.plan_adherence,
                tier0_summary_json=state.tier0_summary.model_dump_json(
                    exclude_none=True,
                    include={"week_prefix", "completion", "context", "sessions", "implicit_feedback"},
                ),
                raw_sessions_json=state.raw_sessions_json or "[]",
                planned_plan_markdown=state.planned_plan_markdown,
                plan_state_raw=state.plan_state_raw,
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
            from weekforge.config.env import settings
            from weekforge.tools import notion_api_gateway as notion
            from weekforge.tools.week_summary_renderer import render_week_summary
            
            rendered = render_week_summary(state.last_output)
            code_block = f"```text\n{rendered}\n```"
            
            _logger.info("Writing week summary to Notion.")
            all_summary_pages = notion.query(database_id=settings.notion_db_training_week_summaries)
            records = [p for p in all_summary_pages if _get_text_prop(p, "Week") == state.week_prefix]

            if records:
                page_id = records[0]["id"]
                notion.update(
                    page_id=page_id,
                    content=code_block
                )
                state.written_page_id = page_id
            else:
                _logger.warning("No existing row for week %s found! Creating a new one.", state.week_prefix)
                title_prop = notion.get_title_property_name(settings.notion_db_training_week_summaries)
                page_id = notion.create(
                    database_id=settings.notion_db_training_week_summaries,
                    properties={
                        "Week": {"rich_text": [{"text": {"content": state.week_prefix}}]},
                        title_prop: {"title": [{"text": {"content": f"Week {state.week_prefix} Summary"}}]},
                    },
                    content=code_block
                )
                state.written_page_id = page_id
                
            state.step = "plan_state_update"
            store.save(thread_id, WORKFLOW, state.step, state)

        elif state.step == "plan_state_check":
            store.save(thread_id, WORKFLOW, state.step, state)
            from weekforge.config.env import settings
            from weekforge.tools import notion_api_gateway as notion

            _console.print("[dim]plan_state_check: querying training_week_summaries…[/dim]")
            all_summary_pages = notion.query(database_id=settings.notion_db_training_week_summaries)
            records = [p for p in all_summary_pages if _get_text_prop(p, "Week") == "PLAN_STATE"]

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
                _console.print(f"[dim]plan_state_check: found PLAN_STATE ({len(raw_text)} chars)[/dim]")
            else:
                state.is_bootstrap = True
                _console.print("[dim]plan_state_check: no PLAN_STATE found (bootstrap)[/dim]")

            state.step = "agent"
            store.save(thread_id, WORKFLOW, state.step, state)
            
        elif state.step == "plan_state_update":
            store.save(thread_id, WORKFLOW, state.step, state)
            from weekforge.agents.plan_state_agent import (
                PlanStateDeps,
                plan_state_agent,
            )
            from weekforge.config.env import settings
            from weekforge.tools import notion_api_gateway as notion
            from weekforge.tools.plan_state import (
                PlanState,
                parse_plan_state,
                render_plan_state,
                update_mechanical_fields,
            )
            
            assert state.is_bootstrap is not None
            
            assert state.last_output is not None
            if not state.is_bootstrap:
                _logger.info("Running incremental PLAN_STATE update.")
                existing_ps = parse_plan_state(state.plan_state_raw or "")
                existing_ps = update_mechanical_fields(existing_ps, state.last_output)

                plan_deps = PlanStateDeps(existing_plan_state=existing_ps, new_week=state.last_output)
                prompt = "Update the plan state logically based on the new week."
                result, meta, _ = run_with_metadata(
                    plan_state_agent, prompt, deps=plan_deps, message_history=None
                )
                updated_ps = result.output
                cost.add(meta)
                
                rendered_ps = render_plan_state(updated_ps, state.week_prefix)
                code_block = f"```text\n{rendered_ps}\n```"
                
                assert state.plan_state_page_id is not None
                title_prop = notion.get_title_property_name(settings.notion_db_training_week_summaries)
                notion.update(
                    page_id=state.plan_state_page_id,
                    properties={title_prop: {"title": [{"text": {"content": f"Plan State - W01-{state.week_prefix}"}}]}},
                    content=code_block
                )
            else:
                _logger.info("Bootstrapping PLAN_STATE.")
                plan_deps = PlanStateDeps(existing_plan_state=PlanState(), all_weeks=[state.last_output])
                prompt = "Bootstrap plan state from provided weeks."
                result, meta, _ = run_with_metadata(
                    plan_state_agent, prompt, deps=plan_deps, message_history=None
                )
                updated_ps = result.output
                cost.add(meta)
                
                rendered_ps = render_plan_state(updated_ps, state.week_prefix)
                code_block = f"```text\n{rendered_ps}\n```"
                
                title_prop = notion.get_title_property_name(settings.notion_db_training_week_summaries)
                ps_page_id = notion.create(
                    database_id=settings.notion_db_training_week_summaries,
                    properties={
                        "Week": {"rich_text": [{"text": {"content": "PLAN_STATE"}}]},
                        title_prop: {"title": [{"text": {"content": f"Plan State - W01-{state.week_prefix}"}}]},
                    },
                    content=code_block
                )
                _logger.info("Created PLAN_STATE page: %s", ps_page_id)
                
            state.step = "done"
            store.save(thread_id, WORKFLOW, state.step, state)
        
        else:
            raise RuntimeError(f"Unknown step: {state.step!r}")

    store.delete(thread_id)
    _console.print(Panel(cost.summary(), title=f"Run complete — {state.week_prefix}", border_style="green"))
