# 🤖 Project Agents

This repository utilizes "development agents" to assist with coding, reviewing, and architecting tasks. Agents define specific **personas** for the AI coding assistant to adopt. For reusable **procedural knowledge** (how to do something, not who to be), see [SKILLS.md](./SKILLS.md).

## Available Agents

The definitions for these agents are located in the `.agents/agents/` directory.

### Specs Developer
- **Path**: `.agents/agents/specs-developer/specs-developer.md`
- **Role**: Specs Developer — System Architect for Agentic Patterns.
- **Usage**: Use this agent to analyze legacy code and generate formal architectural specs based strictly on theoretical agentic patterns (like Google's Agentic Design Patterns), without writing implementation code.
- **How to invoke**: *"Adopt the `specs-developer` agent. Read the legacy code in [folder], cross-reference it with `references/agentic-design-patterns-guide.md`, and generate an SDD Spec."*

### Feature Developer
- **Path**: `.agents/agents/feature-developer/feature-developer.md`
- **Role**: Senior Python Engineer — LangGraph, Notion API, training domain specialist.
- **Usage**: Use this agent to implement step specs. Reads the spec, builds bottom-up (models → tools → graph → CLI), narrates every design decision, and self-verifies against acceptance criteria.
- **How to invoke**: *"Adopt the `feature-developer` agent. Implement step [step-XX] from `specs/steps/step-XX-name.md`."*

### Feature Tester
- **Path**: `.agents/agents/feature-tester/feature-tester.md`
- **Role**: QA Engineer — pytest specialist, pragmatic test strategist.
- **Usage**: Use this agent to review an implementation and write focused, high-value tests. Always reasons about whether each test justifies its existence in a personal project. Keeps the test suite small and sharp.
- **How to invoke**: *"Adopt the `feature-tester` agent. Review the implementation of step [step-XX] and write tests."*

### Code Reviewer
- **Path**: `.agents/agents/code-reviewer/code-reviewer.md`
- **Role**: Senior Engineer — pre-commit quality gate for solo trunk-based development.
- **Usage**: Use this agent before committing. Reviews for spec compliance, architectural consistency, type safety, and testing adequacy. Provides a structured report with blockers/warnings/suggestions and a commit message.
- **How to invoke**: *"Adopt the `code-reviewer` agent. Review the implementation of step [step-XX] before commit."*

### Documentation Developer
- **Path**: `.agents/agents/documentation-developer/documentation-developer.md`
- **Role**: Senior Technical Writer + Domain Expert — explains code intent for learning.
- **Usage**: Use this agent to add inline documentation to code. Documents intent and decisions, not fundamentals. Keeps documentation concise and action-oriented.
- **How to invoke**: *"Adopt the `documentation-developer` agent. Document the implementation of step [step-XX]."*

## Recommended Workflow

The five agents form a natural development cycle for a solo developer:

```
specs-developer → feature-developer → feature-tester → code-reviewer → documentation-developer → commit
```

| Phase | Agent | Output |
|-------|-------|--------|
| 1. Specify | `specs-developer` | Step spec with acceptance criteria |
| 2. Build | `feature-developer` | Implementation + accompanying tests |
| 3. Test | `feature-tester` | Focused test suite + coverage assessment |
| 4. Review | `code-reviewer` | Structured review report + commit message |
| 5. Document | `documentation-developer` | Inline docstrings explaining intent |

**Git strategy**: Trunk-based development (direct commits to `main`). The code-reviewer agent replaces PR reviews. The documentation-developer agent adds inline docs before commit. Atomic commits with conventional format: `feat(step-0b): implement Notion tool layer`.

## Agents vs Skills

| Concept | What it defines | When loaded | Example |
|---------|----------------|-------------|---------|
| **Agent** | A *persona* — "You are a Senior Specs Developer" | Explicit invocation | `specs-developer` |
| **Skill** | *Procedural knowledge* — "When doing X, follow these rules" | On-demand, when task matches | `specs-management` |

## Guidelines for Adding New Agents

1. Create a `.md` file in the `.agents/agents/` directory.
2. Define the persona, core process, and required output.
3. Document it in this `AGENTS.md` file so everyone on the team knows how to assign it.
