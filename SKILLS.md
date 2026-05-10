# Project Skills

Skills are reusable procedural knowledge loaded on-demand when task matches.

Shared in `.dev-agents/skills/`, project-specific in `.agents/skills/`.
Lookup order: `.agents/` first, then `.dev-agents/`. Local wins on collision.

## When to invoke skills

When task matches a skill description, load it before writing code.

## Available Skills

### Specs Management
- **Path**: `.agents/skills/specs-management/SKILL.md` (weekforge override — uses `specs/` paths)
- **Shared fallback**: `.dev-agents/skills/specs-management/SKILL.md` (generic, uses `{SPECS_DIR}`)
- **When loaded**: When creating, editing, reviewing, or tracking spec files in `specs/`.
- **What it provides**: Step file format, status tracking, change process, decision log protocol.

### Prompt Review
- **Path**: `.dev-agents/skills/prompt-review/SKILL.md` (shared)
- **When loaded**: When auditing, refactoring, or authoring LLM prompt files (persona, guardrails, instruction templates).
- **What it provides**: XML-wrapped persona/guardrails structure, separation-of-concerns rules, duplication and conflict detection checklist, Anthropic Claude 4.x best practices.

## Agents vs Skills

| Concept | What it defines | When loaded | Example |
|---------|----------------|-------------|---------|
| **Agent** | A *persona* — "You are a specs developer" | Explicit invocation | `specs-developer` |
| **Skill** | *Procedural knowledge* — "When doing X, follow these rules" | On-demand, when task matches | `specs-management` |

## Adding new skills

Shared: create `skills/<name>/SKILL.md` in `~/Projects/dev-agents`, commit there.
Project-specific: create `.agents/skills/<name>/SKILL.md` here, tracked in this repo.
