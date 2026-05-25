<draft-week-task>
You are generating a high-level weekly training plan. You receive:
- Template sessions (reference structure for this week position in the mesocycle).
- Previous 3 weeks feedback (plan + summary per week, when available).
- PLAN_STATE (cumulative mesocycle tracker: progression baselines, injury timeline, deload history).
- User profile (conditions, goals, HR zones, session preferences).
- ACTIVE_FLARE flag (YES/NO — triggers conservative programming).

Your job: produce a `WeekPlan` with 8–12 planned sessions, each with a descriptive name, duration in minutes, and focus tags from the controlled vocabulary.

## Session Planning Rules

1. **Balance distribution** across: hinge, squat, pull, push, core, conditioning, skill work.
2. **Pull:push ratio ~2:1.** Count pull-dominant vs push-dominant sessions. If ratio drifts below 1.5:1, add pull sessions or convert balanced sessions to pull-dominant.
3. **Conditioning volume ≥2 sessions per week.** Sessions tagged with cardio/z2/z3/uphill/loaded/run/hike count. If fewer than 2, add conditioning or blend into existing sessions.
4. **Session durations from data, not defaults.** Use previous week actuals and user-profile SESSION_PREFERENCES as baseline. Gym sessions: 80+ min baseline. Conditioning: scale to mesocycle position. Only standalone sessions (hangboard, mobility, recovery) use shorter durations.
5. **Account for cumulative feedback.** Reduce intensity if pain reported, increase if completion is high and feedback positive. Reference PLAN_STATE for multi-week trends.
6. **ACTIVE_FLARE = YES**: apply symptom protocol. Substitute or reduce load on affected movements. Do not program through active pain.

## Focus Tags (use only these)

Movement: `push`, `pull`, `squat`, `hinge`, `core`, `carry`
Cardio: `cardio`, `z1`, `z2`, `z3`, `uphill`, `loaded`, `run`, `hike`, `walk`
Skill: `climbing`, `hangboard`, `mobility`, `recovery`
Other: `template_restructured`

Each session gets 1–4 focus tags describing its primary training focus. Tags drive Tier-0 validation in the next step (pull:push ratio, conditioning count).

## Adjustments

List specific changes from the previous weeks' feedback and PLAN_STATE trends. Each adjustment: what changed and why. Examples:
- "Reduced squat volume — SI flare reported W14"
- "Added third Z2 session — mountaineering prep on track, pushing conditioning"
- "Swapped barbell rows for cable rows — grip fatigue pattern across W12-W14"

If bootstrap mode (no feedback history): state "First week — using template baseline, conservative defaults."

## Output

Return a `WeekPlan` with:
- `week_prefix`: the week being planned (e.g., "W15")
- `sessions`: list of `PlannedSession` objects (8–12 items)
- `adjustments`: list of human-readable reasoning bullets (at least 1)
</draft-week-task>
