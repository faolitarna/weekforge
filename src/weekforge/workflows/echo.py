"""Echo workflow — reference implementation of the plain-Python workflow pattern.

New workflows should copy this shape: load-or-init state from checkpoint, do work,
call hitl_confirm (which saves state before prompting), caller interprets the decision.
"""
from weekforge.checkpoint import CheckpointStore
from weekforge.hitl import HitlDecision, hitl_confirm
from weekforge.models.state import State

_WORKFLOW = "echo"
# Persisted in the checkpoint row — must stay stable across code changes or
# existing paused runs won't resume correctly.
_STEP_CONFIRM = "confirm"


def run_echo(message: str, thread_id: str, store: CheckpointStore) -> HitlDecision:
    """Run or resume the echo workflow for the given thread.

    If a checkpoint exists for thread_id, the `message` argument is ignored and
    state is restored from the saved JSON — this is the resume path. On a fresh
    run, the message is prefixed with "Echoed:" before the HITL pause.

    Returns the HitlDecision from hitl_confirm. The caller (cli.py) interprets
    `.approved=True` as completion and calls store.delete(); `.approved=False`
    leaves the checkpoint intact so the run can be resumed later.
    """
    record = store.load(thread_id)
    if record is not None:
        state = State.model_validate_json(record.state_json)
    else:
        state = State(message=f"Echoed: {message}")

    return hitl_confirm(
        context=f"The echo workflow processed your message.\nResult: '{state.message}'",
        recommendation="Say Yes to complete the workflow.",
        checkpoint=store,
        thread_id=thread_id,
        workflow=_WORKFLOW,
        step=_STEP_CONFIRM,
        state=state,
    )
