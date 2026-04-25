from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["main", "accessory", "focus", "warmup", "cooldown"]
Status = Literal["done", "done_modified", "skip"]


class ExerciseLogEntry(BaseModel):
    name: str
    planned_weight: str | None
    planned_sets: int | None
    planned_reps: str | None
    actual_weight: str | None = None
    actual_sets: int | None = None
    actual_reps: str | None = None
    role: Role
    status: Status
    feedback: str | None = None
    section: str | None = None
    session_name: str | None = None


class SessionLine(BaseModel):
    name: str
    status: Literal["done", "skip", "partial"]
    exercises_done: int
    exercises_total: int
    pain_status: str | None
    comment: str


class CardioEntry(BaseModel):
    kind: Literal["z1_run", "z2_run", "z3_tempo", "hike", "trail_run", "other"]
    raw: str


class ClimbingEntry(BaseModel):
    kind: str
    raw: str


class JointEntry(BaseModel):
    name: str
    status: str
    triggers: str | None = None
    what_helped: str | None = None


class SectionRates(BaseModel):
    warmup_pct: float
    main_pct: float
    cooldown_pct: float


class SkippedPattern(BaseModel):
    exercise: str
    skip_rate: float


class SessionCheckCount(BaseModel):
    session_name: str
    checked: int
    total: int


class ImplicitFeedback(BaseModel):
    total_checked: int
    total_exercises: int
    per_session: list[SessionCheckCount]
    section_rates: SectionRates
    frequently_skipped: list[SkippedPattern]
    always_completed: list[str]


class ModificationPattern(BaseModel):
    exercise: str
    planned: str
    actual: str


class SkipPattern(BaseModel):
    exercise: str
    reason: str


class PlanAdherence(BaseModel):
    planned_total: int
    completed: int
    modified: int
    skipped: int
    modification_patterns: list[ModificationPattern]
    skip_patterns: list[SkipPattern]


class WeekSummary(BaseModel):
    week_prefix: str
    completion: str
    context: str | None = None
    sessions: list[SessionLine]
    exercise_log: list[ExerciseLogEntry]
    cardio_log: list[CardioEntry] = Field(default_factory=list)
    climbing_log: list[ClimbingEntry] = Field(default_factory=list)
    pain_status: list[JointEntry]
    issues: list[str] = Field(default_factory=list)
    wins: list[str] = Field(default_factory=list)
    recommendations_next: list[str] = Field(default_factory=list)
    plan_adherence: PlanAdherence | None = None
    implicit_feedback: ImplicitFeedback
    highlights: list[str] = Field(default_factory=list)
    trend: str = ""
