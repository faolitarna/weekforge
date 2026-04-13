import os
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from weekforge.models.state import State


def echo_node(state: State) -> dict[str, str]:
    """
    A trivial node that echoes the message back.
    
    Nodes in LangGraph are just functions that take the current state
    and return an update. Returning a dict is standard — LangGraph
    merges this (or replaces, based on reducers) into the state.
    """
    # We simply return the message to prove it was received and processed
    return {"message": f"Echoed: {state.message}"}

# Build the graph
workflow = StateGraph(State)

# Add our single node
workflow.add_node("echo_logic", echo_node)

# Set up edges
workflow.add_edge(START, "echo_logic")
workflow.add_edge("echo_logic", END)

# Create explicit checkpointer for persistence + HITL
os.makedirs(".langgraph", exist_ok=True)
db_path = ".langgraph/checkpoints.sqlite"
conn = sqlite3.connect(db_path, check_same_thread=False)
checkpointer = SqliteSaver(conn)

# Compile the graph
# We add an interrupt *before* END so that we can demonstrate HITL 
# explicitly pausing before the completion. Wait, step 0a mentions:
# "One interrupt_before for HITL" - we'll interrupt before our node
# because we want to see it pause and resume, or maybe *after* our node?
# Usually, HITL confirms an action. The prompt schema says:
# A["Entry"] --> B["Echo Node"] --> C{"HITL: Confirm"} --> D["Complete"].
# This means we should have a dummy "complete" node or just interrupt before END.
# Since we can't easily interrupt before END directly using node names unless we have one,
# let's add a `complete` node.

def complete_node(state: State) -> dict[str, str]:
    """Node that runs after HITL confirmation."""
    return {}

workflow.add_node("complete", complete_node)
workflow.add_edge("echo_logic", "complete")
workflow.add_edge("complete", END)

# Compile and interrupt before the complete node (the HITL point)
app = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["complete"]
)
