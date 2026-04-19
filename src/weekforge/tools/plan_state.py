import re
from pydantic import BaseModel, Field
from weekforge.models.week_summary import WeekSummary

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

def parse_plan_state(text: str) -> PlanState:
    state = PlanState()
    current_section = None
    
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("MESOCYCLE:"):
            # MESOCYCLE:{name}|{total_weeks}wk
            m = re.match(r"MESOCYCLE:(.*?)\|(\d+)wk", line)
            if m:
                state.mesocycle_name = m.group(1)
                state.total_weeks = int(m.group(2))
            continue
            
        if line.startswith("WEEKS_COMPLETED:"):
            # WEEKS_COMPLETED:{N}|AVG_COMPLETION:{avg}%
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
            # map current_section to field
            field_name = current_section
            if hasattr(state, field_name):
                getattr(state, field_name).append(val)
                
    return state

def update_mechanical_fields(state: PlanState, week: WeekSummary) -> PlanState:
    # 1. Update weeks completed
    state.weeks_completed += 1
    
    # 2. Update avg_completion
    # completion string is usually "X/Y"
    try:
        done, total = map(int, week.completion.split("/"))
        week_pct = (done / total * 100) if total > 0 else 0.0
        # Cumulative average
        if state.weeks_completed == 1:
            state.avg_completion = week_pct
        else:
            old_sum = state.avg_completion * (state.weeks_completed - 1)
            state.avg_completion = (old_sum + week_pct) / state.weeks_completed
    except Exception:
        pass
        
    # 3. Adherence list append (we assume the first item is 'weekly:W01%->W02%...|avg:%')
    found_weekly = False
    for i, adv in enumerate(state.adherence):
        if adv.startswith("weekly:"):
            parts = adv.split("|")
            chain = parts[0]
            try:
                done, total = map(int, week.completion.split("/"))
                new_pct = f"{int(done/total*100)}%" if total>0 else "0%"
                chain += f"->{new_pct}"
                state.adherence[i] = f"{chain}|avg:{int(state.avg_completion)}%"
            except Exception:
                pass
            found_weekly = True
            break
            
    if not found_weekly:
        try:
            done, total = map(int, week.completion.split("/"))
            new_pct = f"{int(done/total*100)}%" if total>0 else "0%"
            state.adherence.insert(0, f"weekly:{new_pct}|avg:{int(state.avg_completion)}%")
        except Exception:
            pass
            
    # For MAIN_LIFTS we append mechanical weights based on exercise_log
    # This is a bit heuristical; we match main lift names
    main_exercises = {e.name: e for e in week.exercise_log if e.role == "main"}
    for i, ml in enumerate(state.main_lifts):
        try:
            # - {exercise}:{W01_weight}->{current}|peak:{max}kg|trend:{up/plateau/down}
            ex_part, rest = ml.split(":", 1)
            if ex_part in main_exercises:
                ex = main_exercises[ex_part]
                w = ex.actual_weight or ex.planned_weight or "BW"
                # insert ->w into the chain
                chain_part, meta_part = rest.split("|", 1)
                chain_part += f"->{w}"
                state.main_lifts[i] = f"{ex_part}:{chain_part}|{meta_part}"
        except Exception:
            pass
            
    return state

def render_plan_state(state: PlanState, current_week: str) -> str:
    lines = []
    lines.append(f"PLAN_STATE:W01-{current_week}")
    lines.append(f"MESOCYCLE:{state.mesocycle_name}|{state.total_weeks}wk")
    lines.append(f"WEEKS_COMPLETED:{state.weeks_completed}|AVG_COMPLETION:{state.avg_completion:.1f}%")
    lines.append("")
    
    sections = [
        ("MAIN_LIFTS", state.main_lifts),
        ("PUSH_PULL_GAP", state.push_pull_gap),
        ("ACCESSORY_TRACKER", state.accessory_tracker),
        ("FOCUS_EXERCISE_LOG", state.focus_exercise_log),
        ("HANGBOARD", state.hangboard),
        ("CARDIO", state.cardio),
        ("CLIMBING", state.climbing),
        ("INJURY_TIMELINE", state.injury_timeline),
        ("MOBILITY_POSTURE", state.mobility_posture),
        ("ADHERENCE", state.adherence),
        ("SESSION_PREFERENCES", state.session_preferences),
        ("DELOAD_HISTORY", state.deload_history),
        ("RESOLVED", state.resolved),
        ("ACTIVE_ISSUES", state.active_issues),
    ]
    
    for title, items in sections:
        if items: # Only output if not empty, following legacy loose text rules (or maybe output header anyway, but usually better to output the header to preserve structure if possible. I'll output headers if not empty)
            lines.append(f"{title}:")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")
            
    return "\n".join(lines).strip()
