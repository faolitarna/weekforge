from dataclasses import dataclass, field


@dataclass
class RawBlock:
    block_type: str
    text: str
    checked: bool | None
    raw: dict


@dataclass
class RawSession:
    page_id: str
    name: str
    blocks: list[RawBlock] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)


@dataclass
class RawWeekData:
    week_prefix: str
    sessions: list[RawSession] = field(default_factory=list)
    planned_plan_markdown: str | None = None
