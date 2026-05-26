# Project Agents

Shared repo rules.
Keep agent files short.
Do not repeat this file inside agents.

## Agent locations

- Shared agents: `.dev-agents/agents/<name>/<name>.md`
- Project-specific agents: `.agents/agents/<name>/<name>.md`
- Lookup order: `.agents/` first, then `.dev-agents/`. Local wins on collision.

## Workflow

See `docs/development_workflow.md` for the full skill-based workflow (Matt Pocock PM skills + superpowers implementation).

### Active agents in skill workflow

These agents run after superpowers execution and before final review:

#### `feature-tester`
- Purpose: write focused tests for changed behavior.
- Owns: test plan, unit tests, small justified integration tests, coverage summary.
- Does not own: implementation review or redesign.

#### `documentation-developer`
- Purpose: add minimal code documentation.
- Owns: non-obvious contract docs, local why-comments, comment cleanup.
- Does not own: specs, implementation, tutorials, or review.

### Legacy agents (optional)

These agents support the older spec-driven flow without skills. Still usable when the full skill workflow is overkill.

Legacy flow: `specs-facilitator -> specs-developer -> feature-developer -> feature-tester -> code-reviewer -> documentation-developer -> commit`

#### `specs-facilitator`
- Purpose: clarify one spec draft before formal spec writing.
- Owns: clarification questions, decision capture, open-question tracking, readiness check.

#### `specs-developer`
- Purpose: write one bounded implementation spec.
- Owns: scope, file list, interfaces, data contracts, workflow, tier split, failure modes, acceptance criteria.

#### `feature-developer`
- Purpose: implement one bounded spec step.
- Owns: implementation and local validation.

#### `code-reviewer`
- Purpose: review changed scope before commit.
- Owns: spec compliance, correctness, architectural fit, maintainability, test adequacy.

#### Legacy handoff rules

- Start with a spec draft based on `spec-template.md`.
- If `Open questions` contains meaningful ambiguity, run `specs-facilitator` first.
- When ambiguity is low and decisions are captured, run `specs-developer`.
- Downstream agents treat the finalized spec as source of truth.

## Task complexity tier split 

- Tier 0 = deterministic Python (parsing, validation, CRUD, formatting)
- Tier 1 = fast/cheap LLM for micro-classification (section heading classification)
- Tier 2 = heavy cognitive LLM (planning, summarization, trend synthesis)

## Layer boundaries

- `cli` = entry point
- `workflows` = orchestration + step functions
- `tools` = I/O + deterministic logic (Notion gateway, validators, renderers)
- `models` = structured data (Pydantic models, workflow state)
- `agents` = LLM prompt + output contract
- `prompts` = LLM instruction text (markdown files, never inline in Python)
- `config` = user profile, env settings
- `checkpoint` = SQLite-persisted workflow state for quit-and-resume

## Repo rules

- Plain Python for workflow orchestration.
- If task can be done without LLM, do it in Python.
- LLMs do interpretive work, not parsing, counting, CRUD, formatting, or validation.
- Notion access stays inside tool layer.
- Workflow state must support checkpoint/resume.
- Replay-sensitive writes must be idempotent.
- CLI output stays scannable.

## Modeling rules

- Use structure when code must branch, validate, persist, retry, compare, or resume.
- Keep text as text when it is real content: markdown, prompts, comments, summaries, recommendations, highlights.
- Prefer typed envelopes around free-text payloads.
- If code parses a string later, that string is a protocol. Keep one parser, one renderer, brief format docs, tests.

## Quality rules

- Optimize for readability.
- Keep code small and direct.
- Avoid speculative abstractions.
- Avoid framework ceremony.
- Fail loudly at boundaries.
- No silent swallowing of meaningful errors.

## Working style

- Read only needed context.
- Stay inside requested scope.
- Prefer smallest correct change.
- Reuse good local patterns.
- Avoid unrelated refactors.
- Be explicit about assumptions and gaps.
