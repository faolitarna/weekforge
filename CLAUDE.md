# Claude Code — Project Pointer

Agents: `.agents/agents/<name>/<name>.md` (shared) or `.agents-local/agents/<name>/<name>.md` (project-specific).
Lookup order: check `.agents-local/` first, then `.agents/`. Local wins on collision.

Skills: `.agents/skills/<name>/SKILL.md` (shared) or `.agents-local/skills/<name>/SKILL.md` (project-specific).
Same lookup order: local first, shared second.

When user says "use X agent", read the persona file and adopt it inline.

See AGENTS.md for project-specific rules and agent inventory.
