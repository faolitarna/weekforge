---
name: specs-management
description: "INVOKE THIS SKILL when creating, editing, reviewing, or tracking status of spec files in the specs/ directory. Covers frontmatter schema, status lifecycle, versioning, change process, and traceability."
---

<overview>
Weekforge uses Spec-Driven Development (SDD) to ensure specifications remain the active source of truth throughout the project lifecycle. Every spec file follows a standard format with YAML frontmatter, a defined status lifecycle, and traceable connections to implementation code.
</overview>

<when-to-use>

| Use This Skill When | Don't Use This Skill When |
|---------------------|--------------------------|
| Creating a new spec file in `specs/` | Writing implementation code |
| Updating an existing spec's content or status | Reading specs for context only |
| Reviewing whether a spec is complete | Working on non-spec documentation |
| Logging an architectural decision | Making changes that don't affect specs |
| Updating the traceability matrix after implementation | |

</when-to-use>

<frontmatter-schema>
All spec files must include this YAML frontmatter:

```yaml
---
id: WF-XX            # Unique identifier (e.g., WF-00, WF-LA1, WF-OBS)
title: Human Title   # Human-readable title of the spec
status: draft        # One of: not-started | draft | in-review | approved | implemented | deprecated
version: 1.0         # Semantic version (major.minor)
last-updated: YYYY-MM-DD
depends-on: []       # Array of spec IDs this spec relies on
implements-phase: [] # Array of migration phases (0-4) that use this spec
---
```

**Exceptions:** The following files do NOT use this frontmatter: `_index.md`, `decision-log.md`, `traceability-matrix.md`.
</frontmatter-schema>

<status-lifecycle>
Status transitions follow this state machine:

```
not-started → draft → in-review → approved → implemented → deprecated
                ↑          |            |
                |          |            |
                └──────────┘            |
                (feedback)              |
                ↑                       |
                └───────────────────────┘
                (discovery divergence)
```

- **not-started**: Placeholder stub exists but has no real content.
- **draft**: Content is being actively written or revised.
- **in-review**: Submitted for stakeholder review, awaiting approval.
- **approved**: Stakeholder has approved. Ready for implementation.
- **implemented**: Code exists that matches this spec. Traceability matrix updated.
- **deprecated**: Replaced by a newer spec or no longer relevant.
</status-lifecycle>

<version-bumping>
- **Minor bump** (`1.1` → `1.2`): Additions, clarifications, field type changes, typo fixes. Does NOT require re-approval.
- **Major bump** (`1.0` → `2.0`): Structural changes that invalidate previous implementations or alter guarantees. REQUIRES re-approval (status goes back to `in-review`).
</version-bumping>

<change-process>
When implementation reveals the spec is wrong, impossible, or sub-optimal:

1. **Stop coding.** Update the spec first.
2. If structural or guarantee-altering → set status to `in-review`, do a major version bump.
3. If minor (clarification, field type, typo) → just bump the minor version.
4. Record the reason in `specs/decision-log.md`.
</change-process>

<decision-log-protocol>
Record an entry in `specs/decision-log.md` when:
- A technical decision resolves an ambiguity in the spec
- Implementation deviates from the spec
- A new architectural constraint is introduced

Required columns: `Date`, `ID` (DEC-NNN), `Decision`, `Context`, `Spec Impact`.

Do NOT hide architectural decisions in PR descriptions or commit messages — they belong in the decision log.
</decision-log-protocol>

<traceability-rules>
After implementing a spec requirement, update `specs/traceability-matrix.md` with:

| Column | Description |
|--------|-------------|
| Spec Requirement | What the spec requires |
| Source | Spec ID + section (e.g., `WF-00 §2`) |
| Implementation | File path + function/class (e.g., `src/tools/notion.py:query_database()`) |
| Test | Test file path (e.g., `tests/tools/test_notion.py::test_query`) |
| Status | ⬜ Not Started / 🔄 In Progress / ✅ Done |
</traceability-rules>

<index-dashboard>
`specs/_index.md` is the central dashboard. When adding or changing a spec:

1. Add/update its row in the status table.
2. Add/update its node in the dependency graph.
3. Use status emojis: ⬜ Not Started | 📝 Draft | 🔄 In Review | ✅ Approved | 🚀 Implemented | 🗑️ Deprecated
</index-dashboard>
