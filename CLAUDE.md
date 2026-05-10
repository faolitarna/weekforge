# Claude Code — Project Pointer

Agents: `.dev-agents/agents/<name>/<name>.md` (shared) or `.agents/agents/<name>/<name>.md` (project-specific).
Lookup order: check `.agents/` first, then `.dev-agents/`. Local wins on collision.

Skills: `.dev-agents/skills/<name>/SKILL.md` (shared) or `.agents/skills/<name>/SKILL.md` (project-specific).
Same lookup order: local first, shared second.

When user says "use X agent", read the persona file and adopt it inline.

See AGENTS.md for project-specific rules and agent inventory.
