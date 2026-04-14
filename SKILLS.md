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

#### Langchain & Langgraph Skills 
- **framework-selection** - Invoke when choosing between LangChain, LangGraph, and Deep Agents
- **langchain-fundamentals** - Invoke for create_agent, @tool decorator, middleware patterns
- **langchain-rag** - Invoke for RAG pipelines, vector stores, embeddings
- **langchain-middleware** - Invoke for structured output with Pydantic
- **langgraph-fundamentals** - Invoke for StateGraph, state schemas, edges, Command, Send, invoke, streaming, error handling
- **langgraph-persistence** - Invoke for checkpointers, thread_id, time travel, memory, subgraph scoping
- **langgraph-human-in-the-loop** - Invoke for interrupts, human review, error handling, approval workflows
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
