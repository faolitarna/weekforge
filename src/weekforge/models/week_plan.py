from typing import Literal

from pydantic import BaseModel, Field

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
    sessions: list[PlannedSession]
    adjustments: list[str] = Field(default_factory=list)
