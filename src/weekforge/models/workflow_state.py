from pydantic import BaseModel


class State(BaseModel):
    """Echo workflow state. Each workflow defines its own state model — no shared class."""
    message: str = ""
