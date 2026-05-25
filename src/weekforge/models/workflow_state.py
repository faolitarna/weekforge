from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from weekforge.models.llm_call_cost import CallMetadata
from weekforge.models.week_summary import WeekSummary


class SummarizeWeekState(BaseModel):
    week_prefix: str
    overwrite_confirmed: bool = False
    user_profile_markdown: str | None = None
    raw_sessions_json: str | None = None  # str not list — checkpoint persistence requires JSON-serializable state
    tier0_summary: WeekSummary | None = None
    last_output: WeekSummary | None = None
    messages_json: list[dict[str, Any]] = Field(default_factory=list)
    calls: list[CallMetadata] = Field(default_factory=list)
    pending_feedback: str | None = None
    step: str = "overwrite_check"
    written_page_id: str | None = None
    is_bootstrap: bool | None = None
    planned_plan_markdown: str | None = None
    plan_state_raw: str | None = None
    plan_state_page_id: str | None = None
    
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DraftWeekState(BaseModel):
    week_prefix: str
    step: str = "overwrite_check"
    messages_json: list[dict[str, Any]] = Field(default_factory=list)
    calls: list[CallMetadata] = Field(default_factory=list)
    last_output: Any = None
    pending_feedback: str | None = None
    validation_retry_used: bool = False
    validation_warning: str | None = None
    written_page_id: str | None = None
    is_bootstrap: bool | None = None
    plan_state_raw: str | None = None
    plan_state_page_id: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
