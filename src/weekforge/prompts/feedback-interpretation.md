<feedback-interpretation>

<explicit-signals>
These are example signals -- the user may phrase feedback differently. Interpret the underlying meaning, not the exact words.

| Feedback Signal | Response |
|-----------------|----------|
| "Felt too easy" | Skip one volume step, or increase load directly if within 1 step of volume ceiling. Accelerated progression. Step sizes in progression-protocol. |
| "Felt hard but completed" | Apply next volume step next occurrence. Hard is expected at the edge of capacity — this means the current load is working. |
| "Completed, no explicit feedback" | Apply next volume step per guardrails default-push rule. Silence after completion = green light. |
| "Couldn't complete all sets/reps" | Reduce load 10% or drop 1 set |
| "Joint discomfort during/after" | Switch to flare-safe variant immediately, monitor |
| "Skipped multiple sessions" | Reduce session count, investigate barriers |
| "Low energy/motivation" | Consider deload week, reduce intensity |
| "Great energy, want more" | Can increase toward upper session count range |
</explicit-signals>

<implicit-signals>
Patterns the coach should detect from session data without explicit user statements.

- **Checkbox completion < 70%** -- session may be too long, too complex, or motivation is low; investigate before adding volume
- **Cool-down consistently skipped** -- session duration likely too long; shorten main work or integrate mobility into warm-up
- **Same exercise skipped across multiple sessions** -- user may dislike it, find it painful, or lack equipment; ask or substitute
- **Weights unchanged for 3+ weeks with no feedback** -- stall or under-programming. Increase load and reset volume per progression-protocol ladder. Don't wait for permission — force the progression and let feedback correct.
- **Session type consistently skipped** (e.g., all conditioning sessions) -- barrier exists (boredom, time, environment); redesign format or reduce frequency
- **All sessions completed with no comments** -- either everything is working or user isn't engaging with feedback; prompt a brief check-in
- **Rapid weight jumps between weeks** -- possible form breakdown; flag and suggest recording a set or reducing to previous weight with more volume
</implicit-signals>

<combined-signals>
When multiple signals appear simultaneously, use this priority order to resolve conflicts.

1. **Pain + any other signal** -- guardrails pain-override applies first. Address the secondary signal only after pain is resolved.
2. **Low adherence + "too hard"** -- reduce both session count and per-session difficulty. This combination suggests the program exceeds current capacity. Drop to minimum viable sessions and rebuild.
3. **Low adherence + "too easy"** -- the barrier is not difficulty. Investigate scheduling, session length, or format issues (executive function, environment). Maintain or slightly reduce session count but keep intensity.
4. **"Felt easy" + incomplete sets** -- contradictory signal. User may be rating perceived effort rather than actual performance. Trust the completion data over subjective report; maintain current parameters and ask for clarification.
5. **High energy + minor discomfort** -- increase overall intensity conservatively but substitute the specific movement causing discomfort. Do not let good energy override joint signals.
6. **Multiple sessions skipped + high performance on completed sessions** -- user is self-selecting sessions (likely dropping ones they dislike). Rotate session types or integrate disliked movement patterns into preferred sessions rather than adding more sessions.
</combined-signals>

</feedback-interpretation>
