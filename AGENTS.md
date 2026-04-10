# 🤖 Project Agents

This repository utilizes "development agents" to assist with coding, reviewing, and architecting tasks. Agents define specific **personas** for the AI coding assistant to adopt. For reusable **procedural knowledge** (how to do something, not who to be), see [SKILLS.md](./SKILLS.md).

## Available Agents

The definitions for these agents are located in the `.agents/agents/` directory.

### Specs Developer
- **Path**: `.agents/agents/specs-developer/specs-developer.md`
- **Role**: Specs Developer — System Architect for Agentic Patterns.
- **Usage**: Use this agent to analyze legacy code and generate formal architectural specs based strictly on theoretical agentic patterns (like Google's Agentic Design Patterns), without writing implementation code.
- **How to invoke**: Ask your AI IDE: *"Adopt the `specs-developer` agent from `.agents/agents/specs-developer/specs-developer.md`. Read the legacy code in [folder], cross-reference it with `references/agentic-design-patterns-guide.md`, and generate an SDD Spec."*

## Agents vs Skills

| Concept | What it defines | When loaded | Example |
|---------|----------------|-------------|---------|
| **Agent** | A *persona* — "You are a Senior Specs Developer" | Explicit invocation | `specs-developer` |
| **Skill** | *Procedural knowledge* — "When doing X, follow these rules" | On-demand, when task matches | `specs-management` |

## Guidelines for Adding New Agents

1. Create a `.md` file in the `.agents/agents/` directory.
2. Define the persona, core process, and required output.
3. Document it in this `AGENTS.md` file so everyone on the team knows how to assign it.
