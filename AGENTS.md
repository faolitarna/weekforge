# Project Agents

Shared repo rules.
Keep agent files short.
Do not repeat this file inside agents.

## Agent locations

- Shared agents: `.agents/agents/<name>/<name>.md`
- Project-specific agents: `.agents-local/agents/<name>/<name>.md`
- Lookup order: `.agents-local/` first, then `.agents/`. Local wins on collision.

## Tier split

- Tier 0 = deterministic Python (parsing, validation, CRUD, formatting)
- Tier 1 = deterministic + tool calls (external I/O, Notion, filesystem)
- Tier 2 = LLM reasoning (interpretation, summarization, recommendation)

## Layer boundaries

- CLI = entry point
- workflows = orchestration
- tools = I/O + deterministic logic
- models = structured data
- agents = LLM prompt + output contract

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

## Agent list

### `specs-facilitator`
- Purpose: clarify one spec draft before formal spec writing.
- Owns: clarification questions, decision capture, open-question tracking, readiness check.
- Edits only: `Status`, `Goal`, `Decisions`, `Open questions`, `Out of scope`.
- Does not own: full spec writing, code, tests, review, docs.

### `specs-developer`
- Purpose: write one bounded implementation spec.
- Owns: scope, file list, interfaces, data contracts, workflow, tier split, failure modes, acceptance criteria.
- Reads existing spec draft and its discussion sections.
- If important ambiguity remains in `Open questions`, stop and hand back to `specs-facilitator`.
- Does not guess.

### `feature-developer`
- Purpose: implement one bounded spec step.
- Owns: implementation and local validation.
- Does not own: spec writing, review, broad documentation.

### `feature-tester`
- Purpose: write focused tests for changed behavior.
- Owns: test plan, unit tests, small justified integration tests, coverage summary.
- Does not own: implementation review or redesign.

### `code-reviewer`
- Purpose: review changed scope before commit.
- Owns: spec compliance, correctness, architectural fit, maintainability, test adequacy.
- Does not own: rewriting code or inventing requirements.

### `documentation-developer`
- Purpose: add minimal code documentation.
- Owns: non-obvious contract docs, local why-comments, comment cleanup.
- Does not own: specs, implementation, tutorials, or review.

## Workflow

Default flow:

`specs-facilitator -> specs-developer -> feature-developer -> feature-tester -> code-reviewer -> documentation-developer -> commit`

## Handoff rules

- Start with a spec draft based on `spec-template.md`.
- If `Open questions` contains meaningful ambiguity, run `specs-facilitator` first.
- When ambiguity is low and decisions are captured, run `specs-developer`.
- `specs-developer` must leave `Open questions` as `None` or explicitly hand the draft back for more discussion.
- Downstream agents treat the finalized spec as source of truth.

## Spec file rule

Use one spec file as the working document.
Do not create a separate discussion artifact.
Discussion happens inside the spec draft.

Recommended top sections in every spec:
- `Status`
- `Goal`
- `Decisions`
- `Open questions`

## Working style

- Read only needed context.
- Stay inside requested scope.
- Prefer smallest correct change.
- Reuse good local patterns.
- Avoid unrelated refactors.
- Be explicit about assumptions and gaps.