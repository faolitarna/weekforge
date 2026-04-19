# Claude Code — Project Pointer

This project uses a custom agent/skill convention (Antigravity-style) rather than `.claude/agents/`.

**Before starting work, read [AGENTS.md](./AGENTS.md)** for the available development personas and how to invoke them.

When the user asks you to "use the X agent" or "adopt the X agent", locate the persona definition in `.agents/agents/<name>/<name>.md` and follow its process. These are not registered Claude Code subagents — they are persona prompts you adopt inline.

For procedural knowledge (how to do something), see [SKILLS.md](./SKILLS.md) and `.agents/skills/`.
