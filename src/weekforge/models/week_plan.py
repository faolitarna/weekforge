from typing import Literal

from pydantic import BaseModel, Field

# Closed set validated by Pydantic — agent cannot emit an arbitrary tag.
# Add new tags here first; the LLM prompt references this vocabulary.
FocusTag = Literal[
    # Movement
    "push", "pull", "squat", "hinge", "core", "carry",
    # Cardio
    "cardio", "z1", "z2", "z3", "uphill", "loaded", "run", "hike", "walk",
    # Skill
    "climbing", "hangboard", "mobility", "recovery",
    # Other
    "template_restructured",
]


class PlannedSession(BaseModel):
    name: str
    duration_min: int
    focus_tags: list[FocusTag]


class WeekPlan(BaseModel):
    week_prefix: str
    sessions: list[PlannedSession]  # empty list allowed here; 8-12 session rule enforced in step 2d
    adjustments: list[str] = Field(default_factory=list)
