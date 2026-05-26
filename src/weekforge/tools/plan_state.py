from __future__ import annotations

import re

from pydantic import BaseModel, Field

from weekforge.models.week_summary import WeekSummary

_PAIN_KEYWORDS = re.compile(r"\b(SI|spine|flare|pain|tendon|joint)\b", re.IGNORECASE)

_SECTION_ORDER = [
    "main_lifts", "push_pull_gap", "accessory_tracker", "focus_exercise_log",
    "hangboard", "cardio", "climbing", "injury_timeline", "mobility_posture",
    "adherence", "session_preferences", "deload_history", "resolved", "active_issues",
]


class PlanState(BaseModel):
    mesocycle_name: str = "Unknown"
    total_weeks: int = 0
    weeks_completed: int = 0
    avg_completion: float = 0.0

    main_lifts: list[str] = Field(default_factory=list)
    push_pull_gap: list[str] = Field(default_factory=list)
    accessory_tracker: list[str] = Field(default_factory=list)
    focus_exercise_log: list[str] = Field(default_factory=list)
    hangboard: list[str] = Field(default_factory=list)
    cardio: list[str] = Field(default_factory=list)
    climbing: list[str] = Field(default_factory=list)
    injury_timeline: list[str] = Field(default_factory=list)
    mobility_posture: list[str] = Field(default_factory=list)
    adherence: list[str] = Field(default_factory=list)
    session_preferences: list[str] = Field(default_factory=list)
    deload_history: list[str] = Field(default_factory=list)
    resolved: list[str] = Field(default_factory=list)
    active_issues: list[str] = Field(default_factory=list)

    # -- classmethods: parse / render --

    @classmethod
    def from_text(cls, text: str) -> PlanState:
        state = cls()
        current_section: str | None = None

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            if line.startswith("MESOCYCLE:"):
                m = re.match(r"MESOCYCLE:(.*?)\|(\d+)wk", line)
                if m:
                    state.mesocycle_name = m.group(1)
                    state.total_weeks = int(m.group(2))
                continue

            if line.startswith("WEEKS_COMPLETED:"):
                m = re.match(r"WEEKS_COMPLETED:(\d+)\|AVG_COMPLETION:([\d\.]+)%", line)
                if m:
                    state.weeks_completed = int(m.group(1))
                    state.avg_completion = float(m.group(2))
                continue

            if line.endswith(":") and " " not in line:
                current_section = line[:-1].lower()
                continue

            if current_section and line.startswith("- "):
                val = line[2:]
                if hasattr(state, current_section):
                    getattr(state, current_section).append(val)

        return state

    def to_text(self, current_week: str) -> str:
        lines = [
            f"PLAN_STATE:W01-{current_week}",
            f"MESOCYCLE:{self.mesocycle_name}|{self.total_weeks}wk",
            f"WEEKS_COMPLETED:{self.weeks_completed}|AVG_COMPLETION:{self.avg_completion:.1f}%",
            "",
        ]

        for field_name in _SECTION_ORDER:
            items = getattr(self, field_name)
            if items:
                lines.append(f"{field_name.upper()}:")
                for item in items:
                    lines.append(f"- {item}")
                lines.append("")

        return "\n".join(lines).strip()

    # -- mechanical updates --

    def apply_mechanical_update(self, week: WeekSummary) -> None:
        self._update_completion(week)
        self._append_adherence(week)
        self._append_main_lift_weights(week)

    def _update_completion(self, week: WeekSummary) -> None:
        self.weeks_completed += 1
        done, total = map(int, week.completion.split("/"))
        week_pct = (done / total * 100) if total > 0 else 0.0
        if self.weeks_completed == 1:
            self.avg_completion = week_pct
        else:
            old_sum = self.avg_completion * (self.weeks_completed - 1)
            self.avg_completion = (old_sum + week_pct) / self.weeks_completed

    def _append_adherence(self, week: WeekSummary) -> None:
        done, total = map(int, week.completion.split("/"))
        new_pct = f"{int(done / total * 100)}%" if total > 0 else "0%"
        for i, entry in enumerate(self.adherence):
            if entry.startswith("weekly:"):
                chain = entry.split("|")[0]
                self.adherence[i] = f"{chain}->{new_pct}|avg:{int(self.avg_completion)}%"
                return
        self.adherence.insert(0, f"weekly:{new_pct}|avg:{int(self.avg_completion)}%")

    def _append_main_lift_weights(self, week: WeekSummary) -> None:
        main_exercises = {e.name: e for e in week.exercise_log if e.role == "main"}
        for i, entry in enumerate(self.main_lifts):
            ex_part, rest = entry.split(":", 1)
            if ex_part in main_exercises:
                ex = main_exercises[ex_part]
                w = ex.actual_weight or ex.planned_weight or "BW"
                chain_part, meta_part = rest.split("|", 1)
                self.main_lifts[i] = f"{ex_part}:{chain_part}->{w}|{meta_part}"

    # -- queries --

    def has_active_pain(self) -> bool:
        return any(_PAIN_KEYWORDS.search(issue) for issue in self.active_issues)
