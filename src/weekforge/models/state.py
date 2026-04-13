from pydantic import BaseModel


class State(BaseModel):
    """
    Base state schema for the minimal graph.
    
    Using Pydantic enforces runtime validation. Any node that attempts to mutate
    the state with an incorrect type will fail immediately with a clear error,
    which conforms to our "Fail fast, fail loud" architectural pattern.
    """
    message: str = ""
