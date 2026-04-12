---
name: specs-management
description: "INVOKE THIS SKILL when creating, editing, or tracking status of spec files in the specs/ directory. Covers step file format, status tracking, and the decision log."
---

<overview>
Weekforge uses Spec-Driven Development (SDD). Specifications are organized into two categories:

- **`specs/steps/`** — Sequential, self-contained implementation guides. Each step has everything needed to implement it.
- **`specs/reference/`** — Background architecture docs. Read once for context, not required during implementation.

Tracking is minimal: a status dashboard (`_index.md`) and an append-only decision log.
</overview>

<when-to-use>

| Use This Skill When | Don't Use This Skill When |
|---------------------|--------------------------|
| Creating or editing a step file in `specs/steps/` | Writing implementation code |
| Updating step status in `_index.md` | Reading specs for context only |
| Editing a reference doc in `specs/reference/` | Making changes that don't affect specs |
| Logging an architectural decision | |

</when-to-use>

<step-file-format>
Step files follow this template:

```markdown
# Step N: Title

## Goal
One sentence — what you're proving works.

## Prerequisites
What must exist before starting (previous step, or nothing for 0a).

## What You're Building
Table of files to create/modify with their purpose.

## Specification
Contracts, types, behaviors — everything needed to implement.

## Acceptance Criteria
Checklist. When all boxes checked, move to the next step.

## Reference
Optional links to reference/ docs for deeper context.
```

Each step must be **self-contained** — reading it alone gives you everything needed to implement. Inline relevant state fields, failure modes, and patterns from reference docs rather than just linking to them.
</step-file-format>

<status-tracking>
Step status is tracked in `specs/_index.md` using three states:

- ⬜ **Not Started** — No implementation work begun
- 🔄 **In Progress** — Currently being implemented
- ✅ **Done** — All acceptance criteria met

When a step's status changes, update its row in `_index.md`.
</status-tracking>

<change-process>
When implementation reveals a spec is wrong, impossible, or sub-optimal:

1. **Stop coding.** Update the spec first.
2. Record the reason in `specs/decision-log.md`.
3. Then continue implementation with the updated spec.
</change-process>

<decision-log-protocol>
Record an entry in `specs/decision-log.md` when:
- A technical decision resolves an ambiguity in a spec
- Implementation deviates from a spec
- A new architectural constraint is introduced

Required columns: `Date`, `ID` (DEC-NNN), `Decision`, `Context`, `Spec Impact`.

Do NOT hide architectural decisions in PR descriptions or commit messages — they belong in the decision log.
</decision-log-protocol>
