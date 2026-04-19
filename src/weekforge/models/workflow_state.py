from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, Field
from weekforge.models.llm_call_cost import CallMetadata
from weekforge.models.week_summary import WeekSummary

class ExtractionState(BaseModel):
    week_prefix: str
    overwrite_confirmed: bool = False
    tier0_summary: WeekSummary | None = None
    last_output: WeekSummary | None = None
    messages_json: list[dict[str, Any]] = Field(default_factory=list)
    calls: list[CallMetadata] = Field(default_factory=list)
    pending_feedback: str | None = None
    step: str = "overwrite_check"
    written_page_id: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
