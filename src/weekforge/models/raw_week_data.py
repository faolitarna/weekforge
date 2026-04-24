from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawBlock:
    block_type: str
    text: str
    checked: bool | None
    raw: dict[str, Any]


@dataclass
class RawSession:
    page_id: str
    name: str
    blocks: list[RawBlock] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    done: bool = False


@dataclass
class RawWeekData:
    week_prefix: str
    sessions: list[RawSession] = field(default_factory=list)
    planned_plan_markdown: str | None = None
