# Weekforge

## What This Is

Weekforge is a Python CLI application that orchestrates an LLM-assisted physical training week lifecycle. It follows a layered, sequential pipeline architecture using Pydantic AI for structured LLM calls and Notion as the sole data store, mediating all I/O via a strict Tier-0 tool layer.

## Core Value

Intelligent, reliable, and flow-compatible training week management that operates directly on personal Notion data with zero risk of unauthorized modifications, ensuring crash-safe workflow progression through local SQLite checkpoints and human-in-the-loop approvals.

## Requirements

### Validated

- ✓ [0a Minimal Workflow] — Workflow foundation: state, checkpoint, HITL, Pydantic AI
- ✓ [0b Notion Tools] — Notion tool layer: CRUD contracts + integration
- ✓ [0c LLM Integration] — Pydantic AI agent setup, model config, metadata capture
- ✓ [0d End-to-End] — Full loop: Notion -> Agent -> HITL -> Notion + CLI
- ✓ [1a Context & CLI] — Prompts dir, DB IDs, user-profile Notion DB + loader, `summarize-week` CLI

### Active

- [ ] [1b Tier-0 Extraction] — Pure-Python parsing, role classification, checkbox + delta analysis
- [ ] [1c Summary Agent & Workflow] — `summarize_agent`, workflow, single HITL accept gate with feedback loop
- [ ] [1d Notion Write & PLAN_STATE] — Legacy-format renderer, Notion row update, PLAN_STATE incremental/bootstrap
- [ ] [2 Planning] — `plan_week` with HITL collaborative shaping
- [ ] [3 Generation] — `draft_session` + Deterministic Evaluator loop
- [ ] [4 Terminal Review] — `summarize_plan` — mesocycle analysis

### Out of Scope

- [Direct Data Mutation by LLMs] — Agents never touch Notion directly; strict Tier-0 tools mediate to prevent data corruption.
- [Heavy Workflow Frameworks] — Migrated away from LangGraph; plain Python `while` loops suffice and reduce dependency weight.

## Context

Weekforge is upgrading from a legacy setup (Claude Desktop `config.json` + static markdown files) to a 12-factor compliant, packageable standard Python wheel. The UX is strongly guided by AuDHD-informed principles: scannable output, progressive disclosure, fixed/predictable interfaces without prose walls, and flow-compatible momentum (approve -> auto-resume -> preserve state). Cost overhead is aggressively managed (e.g. `CAVEMAN_MODE` environment toggles for concise token usage).

## Constraints

- **Tech Stack**: Python 3.13+, `uv` package manager, `pydantic-ai`, `typer` + `rich` for CLI interfaces. — Established architectural choice.
- **Persistence**: Single-file SQLite DB for local interactive checkpoints. — Simplifies state recovery across CLI sessions.
- **API integrations**: Exclusively `notion-client` with `tenacity` rate-limit retries. — Ensures data safety protocols are respected.
- **Packaging**: Prompts (`coaching_persona.md`, `coaching_guardrails.md`) must bundle into the distribution via `hatchling` configs. — Tooling requirement for portability.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Migrate from LangGraph to Pydantic AI | Sequential nature of tool didn't need heavy graph framework. Pydantic AI is lighter and models structure output validation natively. | ✓ Good |
| Caveman-lite style directive | Reduce LLM token consumption and generation times while preserving polite grammar via global switch. | ✓ Good |
| Split Step-1 into 1a-1d | Too monolithic; decoupling allows granular iteration, separates deterministic extraction from LLM logic. | ✓ Good |
| User profile as single Notion page | DB overhead was unnecessary for a singleton context read; page parsing enables simpler update vectors mostly handled by user on mobile. | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-19 after initialization*
