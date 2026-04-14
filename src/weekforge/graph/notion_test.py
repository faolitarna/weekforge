import logging
import os
import sqlite3
from typing import Any, Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field

from weekforge.tools import notion

logger = logging.getLogger(__name__)


class NotionTestState(BaseModel):
    """
    State for the Notion test graph.
    """
    database_id: str
    records: list[dict[str, Any]] = Field(default_factory=list)
    created_page_id: str | None = None


def query_notion(state: NotionTestState) -> dict[str, Any]:
    """Query the test database and retrieve records."""
    logger.info(f"Querying Notion DB: {state.database_id}")
    records = notion.query(database_id=state.database_id)
    return {"records": records}


def hitl_review(state: NotionTestState) -> Command[Literal["write_to_notion", "__end__"]]:
    """
    Pause execution for human review using the recommended `interrupt()` pattern.
    Displays the queried records to the user and asks for permission to create a new one.
    """
    # interrupt() surfaces the payload to the caller and pauses execution
    human_decision = interrupt({
        "action": "verify_and_write",
        "record_count": len(state.records),
        "records_sample": state.records[:3]  # Show up to 3 records
    })

    if human_decision.get("approved"):
        return Command(goto="write_to_notion")
    else:
        return Command(goto="__end__")


def write_to_notion(state: NotionTestState) -> dict[str, Any]:
    """Write a test page back to the database after HITL approval."""
    # NOTE: This inherently couples the test to the test database's specific schema.
    # We use "Title" as the key, which must match the schema exactly.
    properties = {
        "Title": {"title": [{"text": {"content": "Test Item"}}]},
    }
    
    content_md = "# Title\n\n- [x] Tested query\n- [x] Tested creation"
    
    created_id = notion.create(
        database_id=state.database_id,
        properties=properties,
        content=content_md
    )
    
    # We will also test update immediately
    notion.update(
        page_id=created_id,
        content=content_md + "\n\n- [x] Tested update (Idempotent rewrite)"
    )
    
    return {"created_page_id": created_id}


def create_graph() -> Any:
    """Factory to construct and compile the Notion test graph."""
    workflow = StateGraph(NotionTestState)

    workflow.add_node("query_notion", query_notion)
    workflow.add_node("hitl_review", hitl_review)
    workflow.add_node("write_to_notion", write_to_notion)

    workflow.add_edge(START, "query_notion")
    workflow.add_edge("query_notion", "hitl_review")
    workflow.add_edge("write_to_notion", END)

    # Create explicit checkpointer for persistence + HITL safely
    os.makedirs(".langgraph", exist_ok=True)
    db_path = ".langgraph/checkpoints.sqlite"
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    return workflow.compile(checkpointer=checkpointer)
