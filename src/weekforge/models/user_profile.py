from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """The profile is a document for the LLM, not a data structure for Python.
    
    All semantic sections (baseline, goals, conditions, preferences, injuries,
    HR zones) are expressed in prose and injected into agent instructions as-is.
    """

    page_id: str = Field(..., min_length=1)
    markdown: str = Field(..., min_length=1)
