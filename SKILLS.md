# 🧠 Project Skills

Skills are reusable procedural knowledge that any AI agent can load on-demand when working on specific tasks. Unlike agents (which define *who* the AI is), skills define *how* to do something correctly.

## CRITICAL: Invoke Skills BEFORE Writing Code

**ALWAYS** invoke the relevant skill first - skills have the correct imports, patterns, and scripts that prevent common mistakes.

## Available Skills

Project-level skills live in `.agents/skills/`.

### Project Skills

#### Specs Management
- **Path**: `.agents/skills/specs-management/SKILL.md`
- **When loaded**: When creating, editing, reviewing, or tracking spec files in `specs/`.
- **What it provides**: Frontmatter schema, status lifecycle, version bumping rules, change process, decision log protocol, and traceability matrix conventions.

#### Prompt Review
- **Path**: `.agents/skills/prompt-review/SKILL.md`
- **When loaded**: When auditing, refactoring, or authoring LLM prompt files (persona, guardrails, instruction templates) in `src/weekforge/prompts/` or equivalents.
- **What it provides**: Structure templates (XML-wrapped persona/guardrails), separation-of-concerns rules, duplication and conflict detection checklist, common anti-patterns, and Anthropic Claude 4.x best practices as of April 2026.

## Agents vs Skills

| Concept | What it defines | When loaded | Example |
|---------|----------------|-------------|---------|
| **Agent** | A *persona* — "You are a Senior Specs Developer" | Explicit invocation | `specs-developer` |
| **Skill** | *Procedural knowledge* — "When doing X, follow these rules" | On-demand, when task matches | `specs-management` |

## Guidelines for Adding New Skills

1. Create a directory in `.agents/skills/` with a descriptive name.
2. Add a `SKILL.md` file with YAML frontmatter (`name`, `description`) and XML-sectioned content.
3. The `description` field should clearly state *when* the skill should be invoked.
4. Document the skill in this `SKILLS.md` file.
