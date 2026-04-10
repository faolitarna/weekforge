---
id: WF-00
title: System Overview & Architecture
status: draft
version: 1.0
last-updated: 2026-04-10
depends-on: []
implements-phase: [0]
---

# System Overview & Architecture

## 1. System Overview & Legacy Context

The Weekforge project is currently empty. The `source-material` folder contains legacy declarative text-based recipes that were used manually with Claude Code. The overarching goal is to fundamentally upgrade the system into a robust, deterministic, and highly reliable graph-based application using **LangGraph**, without expanding the current feature scope unnecessarily.

This migration will introduce advanced Agentic Patterns, optimize token usage via Python tooling, construct a rich local CLI environment, and employ model-agnostic routing to balance cost and cognitive power natively.

**Agentic Complexity Level: 2 — Strategic Problem-Solver** (per Agentic Design Patterns Guide §2). Weekforge uses **Context Engineering** as a systematic discipline — strategically curating the model's context through PLAN_STATE, 3-week feedback windows, and summary-first loading to prevent cognitive overload and ensure efficient performance. It implements automated feedback loops (Evaluator-Optimizer) for self-improvement of output quality. It does **not** reach Level 3 (Collaborative Multi-Agent) — there is a single reasoning agent, not multiple specialized agents. This is intentional: multi-agent coordination adds complexity without benefit for a single-user, single-domain workflow.

## 2. Global System Architecture & Intelligence Routing

### Intelligence Tiering & Task Abstraction

The backend will utilize an abstraction layer to rapidly test and swap between different LLM providers. Intelligence is tiered:

- **Tier 0 (Pure Python, Zero LLM):** All database querying, data formatting, structural validation, and deterministic logic. Tool nodes, the Deterministic Evaluator (§3 Evaluator-Optimizer, Stage 1), and state management live here. This tier is where cost savings come from — every operation that *can* be Python *must* be Python.
- **Tier 1 (Cheap/Fast Models):** Routing, classification, and lightweight decisions where deterministic rules aren't sufficient.
- **Tier 2 (Heavy Cognitive Models):** `plan_week`, `draft_session`, `summarize_week` — macro-planning, session generation, and feedback synthesis. Tasks requiring genuine reasoning about historical feedback vs templates.

### Generic Notion Tool Layer

All Notion interactions are encapsulated in a **reusable tool layer** — generic Python primitives that feature-specific nodes compose. This layer is Tier-0 (no LLM involvement). The LLM never touches Notion directly; it receives structured data from tools and returns structured outputs that tools write.

**Generic operations** the tool layer must support:

- **Query** — Filter a database by properties, return structured results (not raw API responses)
- **Fetch** — Retrieve a specific page's properties and block content
- **Create** — Write a new page with typed properties and markdown content
- **Update** — Mutate specific properties or replace page content on an existing page

**Design principles:**

- Tool inputs and outputs are **typed data structures**, not free text — this is what makes Tier-0 deterministic
- Notion API specifics (pagination, rate limiting, property type mapping) are hidden inside the tool layer, never leaked to the graph
- Specific tool nodes (e.g., "fetch templates by week prefix", "load 3-week feedback window") will be defined in individual feature specs, composing these generic primitives

### Execution Environment & CLI Experience

Weekforge will be designed as an **On-Demand Local CLI Tool** (run only when the user needs it). To handle LangGraph's persistent state and Human-In-The-Loop checkpoints, the CLI will use rich terminal libraries to present a premium, scannable interface.

The CLI design is grounded in the user's cognitive profile (`references/szymi-blueprint.md`). Each principle maps to a specific AuDHD/cognitive need:

**Zero-decision entry.** A single command (`weekforge`) with no arguments should resume wherever the graph left off. The user never needs to remember which step they're on or which command to run next — the checkpoint handles routing. This maps to: *"Most effective tools require zero working memory"* (szymi-blueprint §5).

**Progressive disclosure.** Show summary first, expand details on request. Feedback loading displays `3 weeks loaded | flare: NO | trend: progressing` — not a wall of exercise data. The user can request expansion when they want depth. This maps to: *"Progressive disclosure — essential first, depth on request"* (szymi-blueprint §6).

**Scannable output.** Fixed, predictable section headers every time. Session drafts always have the same visual structure. Key decisions highlighted with clear visual markers. No walls of prose. This maps to: *"Chunked, scannable blocks. Predictable formatting, checkboxes, timeboxes, fixed section headers"* (szymi-blueprint §6, Claude.md).

**Clear decision points.** Every HITL pause presents exactly: (1) what you're looking at, (2) what your options are, (3) the recommended action. Not a context dump that requires the user to figure out what to do. This maps to: *"Clear decision points flagged explicitly"* (szymi-blueprint §6).

**Flow-compatible momentum.** The approve → auto-continue → next draft loop preserves flow state. No unnecessary pauses between sessions during the generation phase. Once the user is in the "generate sessions" flow, the system keeps the momentum going. This maps to: *"Deep intense bursts of flow, not steady daily output"* (szymi-blueprint §5).

**Dopamine milestones.** Session progress visualization (`3/8 ████░░░░`), completion celebrations, and clear visual feedback on what's done. Small wins surfaced throughout the workflow. This maps to: *"Provide dopamine milestones"* (szymi-blueprint §5).

**Refinement over generation.** The system always proposes first, then the user refines. Never ask "what do you want?" — instead present a draft and ask "what would you change?" This maps to: *"Refinement over generation — present a draft, let him refine"* (szymi-blueprint §6).

### User Configuration & Variable Storage

To support varied configurations, **user profiles and guardrails will be stored directly in Notion**. A `ConfigLoader` node fetches this data at runtime to hydrate the pipeline.
