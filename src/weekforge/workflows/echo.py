from weekforge.checkpoint import CheckpointStore
from weekforge.hitl import HitlDecision, hitl_confirm
from weekforge.models.state import State

_WORKFLOW = "echo"
_STEP_CONFIRM = "confirm"


def run_echo(message: str, thread_id: str, store: CheckpointStore) -> HitlDecision:
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
