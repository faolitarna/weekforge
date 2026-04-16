from pydantic import BaseModel


class State(BaseModel):
    """Echo workflow state. Each workflow defines its own model — no shared state class."""
    message: str = ""
