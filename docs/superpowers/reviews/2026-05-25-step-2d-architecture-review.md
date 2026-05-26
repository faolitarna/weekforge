# Code Review: Step 2d — Validation & Notion Write

> Reviewed: 2026-05-25 | Range: `ad47977..021e95e` | Result: **Ready to merge with fixes**

## Strengths

1. **Clean validator design.** `week_plan_validator.py` is a pure function with no dependencies beyond the `WeekPlan` model. Zero side effects, trivially testable. The comment explaining why "walk" is excluded is exactly the right kind of domain documentation.

2. **Thorough test coverage.** 252 lines of validator tests cover: dual-tagged sessions, zero-push plans, conditioning tag enumeration, the walk exclusion, per-session counting (not per-tag), and the `push_count >= 2` threshold. The workflow tests cover the retry guard state machine end-to-end.

3. **Truncation math is correct.** `rendered[: 2000 - len("[truncated]")] + "[truncated]"` guarantees exactly 2000 chars. Tested explicitly.

4. **Idempotent write.** `upsert_plan` semantics + the overwrite-confirm gate from 2a make repeated runs safe.

5. **Well-structured retry guard.** `validation_retry_used` flag is simple, testable, and prevents unbounded automatic re-prompting.

6. **delete-thread CLI command.** Good operational utility for cleaning up stale checkpoints.

## Issues

### Important (Should Fix)

**1. Infinite accept-validate loop when validation fails twice and user approves**

- **File:** `src/weekforge/workflows/draft_week.py:176-177` and `draft_week.py:247-249`
- **What's wrong:** When validation fails the second time, `_step_validate` returns `"accept"`. The accept gate's `approved_step` is hardcoded to `"validate"`. If the user approves (to override the validation warning), they go back to `validate`, which will fail again (plan unchanged, `validation_retry_used` still True), returning to `"accept"` — creating an infinite accept→validate→accept cycle.
- **Why it matters:** The spec explicitly says "user override only path forward" — the intent is that after seeing the warning, the user can force-write despite failing validation. The current code makes that impossible without quitting.
- **How to fix:** In `_step_validate`, if `validation_warning` is already set (meaning we've been through this before and the user approved despite the warning), skip validation and go directly to `"write"`.

**2. Spec deviation: `push_count >= 2` threshold vs spec's `push_count == 0 → satisfied`**

- **File:** `src/weekforge/tools/week_plan_validator.py:33`
- **What's wrong:** The spec says `If push_count == 0 → satisfied`. Implementation uses `push_count >= 2` — plans with exactly 1 push session skip the ratio check entirely.
- **Assessment:** *Justified improvement* over spec. 1 push session isn't enough data for ratio to matter. Tests explicitly validate this. Should be noted as intentional deviation.

### Minor (Nice to Have)

**3. Truncation could cut mid-line (cosmetic)**

- **File:** `src/weekforge/workflows/draft_week.py:192`
- **What's wrong:** Truncation slices at byte offset which could cut mid-word. Minor UX issue. Plans rarely hit 2000 chars in practice.
- **Possible improvement:** Truncate at last newline before limit.

## Architecture Assessment

The architecture is sound:

- **Separation of concerns:** Validator = pure domain logic, step functions = orchestration, `summaries_db` = Notion API facade, runner = checkpoint lifecycle.
- **Step registry pattern** makes workflow debuggable — each step independently unit-testable.
- **Retry guard** uses simple boolean flag (appropriate for "max 1 retry" semantics).
- **Domain heuristics** (`push_count >= 2`, pure-pull exemption) are better than raw spec thresholds.

## Recommendations

1. **Fix the accept-validate infinite loop** (Important)
2. **Document `push_count >= 2` deviation** in spec or decision log
3. **Consider line-boundary truncation** (low priority)

## Assessment

**Ready to merge: With fixes**

The one functional issue — infinite loop when user tries to override persistent validation failure — needs a fix before merge. Everything else is solid.
