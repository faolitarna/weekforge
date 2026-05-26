# Claude Code — Project Pointer

Agents: `.dev-agents/agents/<name>/<name>.md` (shared) or `.agents/agents/<name>/<name>.md` (project-specific).
Lookup order: check `.agents/` first, then `.dev-agents/`. Local wins on collision.

When user says "use X agent", read the persona file and adopt it inline.

See AGENTS.md for project-specific rules and agent inventory.

## Agent skills

### Issue tracker

Local markdown in `specs/issues/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default canonical labels (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout. See `docs/agents/domain.md`.
