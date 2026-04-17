# Prompt Style — Caveman-Lite Directive

## Goal

Reduce output-token cost on every Pydantic AI agent call in Weekforge without degrading the polish of user-facing messages. This is achieved by optionally appending a terse-style instruction ("caveman-lite") to every agent's system prompt, toggled globally via a single environment variable.

## Motivation

The coach workflow (phase 1 onward — [step-1-extraction.md](../steps/step-1-extraction.md), [step-2-planning.md](../steps/step-2-planning.md), [step-3-generation.md](../steps/step-3-generation.md), [step-4-terminal-review.md](../steps/step-4-terminal-review.md)) returns natural-language prose directly to the user: week summaries, training plans, session drafts, terminal-review narratives. Output tokens are the dominant cost: OpenAI's current `gpt-5.4` profile prices output at ~6× input (see pricing table in [step-0c §Euro Cost Estimation](../steps/step-0c-llm-integration.md#euro-cost-estimation-part-4)).

Empirically, default LLM output contains a consistent fraction of filler ("just", "basically", "I think"), hedging ("maybe", "perhaps"), and pleasantries ("sure", "happy to") — tokens that add length without semantic value. Stripping these while preserving grammar and full sentences keeps the prose user-ready. Fragment-style compression (caveman-full / -ultra) is rejected here because coach output is user-facing and must stay polished — lite is the correct register.

## Design Decisions

### DD-1 · Directive applied at system-prompt level, not per-call wrapper

**What.** The directive is baked into each agent's `system_prompt` at construction time. No wrapper layer around user-turn prompts.

**Why.** Pydantic AI agents already carry a system prompt; the model weights it higher than user content, so compliance is stronger. Single injection point means zero overhead per call and no per-workflow integration work.

**Rejected alternative.** Per-call prompt prefixing (duplicates the directive across every call's input tokens, fragments the concern across workflow code).

### DD-2 · Single global env flag `CAVEMAN_MODE`

**What.** One boolean env var flips the directive on for every agent in the process.

**Why.** The cost/polish tradeoff is a deployment-level decision, not an agent-level one. A single flag is trivial to A/B test (run once with it on, once with it off, compare `RunCost.summary()`). No per-agent bureaucracy as the coach workflow adds more agents.

**Rejected alternative A.** A field on `LLMProfile` (couples style to model-inference config — orthogonal concerns; would force every profile to declare a style).

**Rejected alternative B.** A per-agent flag in each `Agent(...)` call (every future coach agent author must remember to set it; one miss defeats the global toggle).

### DD-3 · Inline Python-string rules

**What.** The directive text is a ~6-line string literal in the Weekforge codebase. No external file read.

**Why.** The directive is stable and short; there is no hot-reload requirement, no non-code-edit tuning workflow, no need to share rules across projects. Hardcoding keeps the contract visible in diffs.

**Rejected alternative A.** Reading the user's locally installed caveman skill file (e.g. `~/.claude/plugins/cache/caveman/.../SKILL.md`). Path is user-specific; breaks for other contributors and CI; couples runtime to an unrelated plugin's lifecycle.

**Rejected alternative B.** A YAML / TOML file shipped in the repo. Adds parser surface and build-config work for no reuse benefit at this scale.

### DD-4 · Lite level only

**What.** Only the caveman-lite register (retains articles and full sentences) is exposed. Full and ultra are not implemented.

**Why.** Coach output is user-facing; fragment-style text would feel abrupt and unprofessional. No current or planned caller needs a different register.

**Rejected alternative.** A level enum (`normal | lite | full | ultra`). YAGNI — introduced only when a concrete non-lite caller emerges.

### DD-5 · Directive explicitly preserves structured-output schema

**What.** The directive text contains an explicit sentence instructing the model to preserve any structured output schema (field names, types, required-ness) and apply the style only to natural-language text fields.

**Why.** Every Weekforge agent uses `output_type=BaseModel`. Without explicit guardrails, a model told to be terse might rename fields, omit optional ones, or compress field names. The Pydantic validator would then reject the response and the run would fail.

**Applies to.** String contents of natural-language fields only. Schema remains byte-identical to the non-caveman case.

## Caveman-Lite Directive Text

The following text is the verbatim, authoritative directive. Implementation MUST use this string (modulo trailing-whitespace normalization). Any future edit to this text is a spec-level change and must land here first.

```
Response style — caveman-lite:
- Drop filler (just, really, basically, simply, actually) and hedging (maybe, I think, perhaps).
- No pleasantries (sure, happy to, of course).
- Keep articles, full sentences, proper grammar. Stay professional and polished.
- Apply this style to natural-language text fields only. Preserve any structured
  output schema exactly as specified.
```

Rationale per bullet:

| Bullet | Why |
|--------|-----|
| Drop filler / hedging | Highest-volume removable-token category in observed LLM output. Lists exact tokens so the model has a concrete target. |
| No pleasantries | Conversational openers add tokens to every response; never semantically load-bearing. |
| Keep articles, full sentences | Distinguishes lite from full/ultra; guarantees output reads as polished prose. |
| Schema preservation | Protects structured-output contract from over-eager compression (see DD-5). |

Source inspiration: the caveman skill's "lite" level row, adapted for OpenAI structured-output context.

## Agent Construction Contract

Language-agnostic rules every agent-construction site must satisfy:

1. An agent's effective system prompt is derived by a pure function `compose(base, flag) -> final`.
2. When `flag` is false, `final == base` — zero behavioral change versus the pre-directive baseline. This preserves compatibility with all existing step-0c tests and integrations.
3. When `flag` is true, `final == base + "\n\n" + directive`. The blank-line separator keeps the two blocks visually distinct if the model echoes the prompt during debugging.
4. No agent may bypass the composer. Every `Agent(..., system_prompt=...)` call in [src/weekforge/agents/](../../src/weekforge/agents/) routes its base prompt through the composer.
5. Composition happens at module import (agent-instance construction), not per-call. See Failure Modes for the runtime-toggle consequence.

## Configuration Contract

- **Env var.** `CAVEMAN_MODE`. Boolean (accepts `true`/`false`, `1`/`0`, case-insensitive — Pydantic Settings default).
- **Default.** `false`. Disabled behavior is the reference baseline.
- **Settings surface.** Exposed as `settings.caveman_mode: bool` on the existing Pydantic `Settings` class ([src/weekforge/config/env.py](../../src/weekforge/config/env.py)).
- **Template.** `.env.template` documents the flag with a single-line comment describing the cost/polish tradeoff.

## Structured-Output Invariant

Enabling `CAVEMAN_MODE` MUST NOT alter the JSON schema emitted by any agent:

- Field names unchanged.
- Field types unchanged.
- Required / optional status unchanged.
- Field ordering, where meaningful, unchanged.

Only the string *content* of natural-language fields is affected. This is enforced by DD-5's explicit directive and re-enforced by Pydantic validation: any schema-violating response fails fast via the existing `run_with_metadata` error path.

## Failure Modes

| Failure | Mitigation |
|---------|------------|
| Model ignores the directive and still emits filler | Accepted. The style is a soft preference; token savings are best-effort, not a hard guarantee. No retry loop, no verification, no cost regression alerting. |
| Model corrupts the structured-output schema | Caught by Pydantic validation inside `run_with_metadata` — same failure path as any other bad agent response. No new handling required. |
| User sets `CAVEMAN_MODE=true` on a process that has an in-flight resumed checkpoint | No-op for that process: agent instances are built at module import; env-var reads are snapshotted into `settings` at startup. The new value applies on next process start. Documented explicitly so resume-mid-run does not silently do two different things. |
| Future agent author forgets to route `system_prompt` through the composer | Detectable by a simple grep for `system_prompt=` in [src/weekforge/agents/](../../src/weekforge/agents/). The code-reviewer agent ([AGENTS.md](../../AGENTS.md)) enforces this as part of standard review. |

## Acceptance Criteria

- [ ] This document exists at [specs/reference/prompt-style.md](./prompt-style.md).
- [ ] The directive text appears verbatim in the "Caveman-Lite Directive Text" section.
- [ ] `CAVEMAN_MODE` documented with default `false`.
- [ ] Structured-output invariant stated.
- [ ] Each design decision includes WHY + rejected alternatives.
- [ ] [specs/_index.md](../_index.md) lists this document under Reference Docs.
- [ ] [step-0c-llm-integration.md](../steps/step-0c-llm-integration.md) Part 2 cross-references this document in its agent-definition section and adds a matching acceptance-criteria bullet.
- [ ] [decision-log.md](../decision-log.md) contains an entry dated 2026-04-17 recording DD-2, DD-3, DD-4 choices.

## Out of Scope

Recorded to prevent scope creep. None of the following is a goal of this spec:

- Non-lite registers (`full`, `ultra`).
- Per-agent or per-profile opt-out.
- Input-prompt compression (rewriting user prompts before they reach the model).
- Dynamic runtime switching of the flag mid-process.
- Coupling the directive to `LLMProfile` or `resolve_llm_profile(...)`.
- Automated verification that the model honored the directive.
