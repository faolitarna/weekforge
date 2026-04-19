---
name: prompt-review
description: "INVOKE THIS SKILL when reviewing, refactoring, or authoring LLM prompt files (system prompts, persona definitions, guardrails, instruction templates). Covers structure, separation of concerns, conflict detection, and Anthropic Claude 4.x best practices as of April 2026."
---

<overview>
Prompts shipped to Claude (or any LLM) behave like production code: drift, duplication, dead references, and unresolved conflicts degrade output silently. This skill defines how to audit and structure prompt files in `src/weekforge/prompts/` (and equivalents) so the model receives a clean, unambiguous spec.

Scope: persona files, guardrail files, instruction templates, output schemas, few-shot example blocks. Not for one-off ad-hoc prompts inside workflow code.
</overview>

<when-to-use>

| Use This Skill When | Don't Use This Skill When |
|---------------------|--------------------------|
| Auditing an existing prompt for quality | Tweaking a one-off inline prompt string |
| Authoring a new persona or guardrail file | Writing user-facing copy or docs |
| Resolving model behavior drift suspected to come from prompt | Debugging tool-call failures (use tool layer) |
| Splitting a monolithic prompt into modules | Editing user profile data (data, not prompt) |

</when-to-use>

<core-principles>

1. **Separation of concerns** — One file = one role. Persona ≠ guardrails ≠ user data ≠ output schema. Mixing them creates drift and double-weighting.
2. **No duplication across files** — Same rule in two files = model double-weights it AND risks divergence on edits. Single source of truth per rule.
3. **Explicit precedence** — When two rules can conflict, state which wins. Do not leave resolution to the model.
4. **Reusable persona** — Persona describes the coach/agent, not the user. User-specific facts (conditions, history, anchors) live in the user profile, loaded separately.
5. **Dead references = lies** — Any path/file/tool the prompt cites must exist. Stale refs from migrations are misleading and trigger hallucination.
6. **Bounded priority lists** — 3–5 primary directives. More than that, the model flattens weighting and recency dominates.
7. **Consistent markup** — Pick XML or markdown headers. Mixing (XML wrapper + markdown sections outside the wrapper) breaks scoping cues for Claude 4.x.

</core-principles>

<structure-template>

Recommended file split for a coaching/agent system:

```
prompts/
  persona.md          # Identity, style, communication. Reusable across users.
  guardrails.md       # Hard rules, safety, precedence. Overrides persona on conflict.
  output_schema.md    # Output format spec (optional, if structured output).
  examples/           # Few-shot examples (optional).
```

User-specific data (conditions, history, training anchors) lives in `models/user_profile.py` + loader, NOT in prompts.

</structure-template>

<persona-file-format>

Wrap the entire file in a single XML root. Claude 4.x uses XML tags as scoping signals; do not mix XML wrappers with markdown headers outside the wrapper.

```xml
<persona>
  <identity>
    Who the agent is. Specialty area. Reusable across users — no user-specific facts.
  </identity>

  <priorities>
    3–5 ranked, non-overlapping directives. If two priorities conflict, state precedence inline.
  </priorities>

  <style>
    Communication tone, default behaviors, output ordering convention.
    Pick ONE ordering convention (front-load key info OR context→action) and apply consistently.
  </style>

  <secondary-considerations>
    Optional. Lower-weight programming defaults. Demote anything that didn't make the top 5.
  </secondary-considerations>
</persona>
```

</persona-file-format>

<guardrails-file-format>

```xml
<guardrails>
  <precedence>
    Guardrails override persona priorities on conflict. State this explicitly.
  </precedence>

  <constraints>
    Hard rules. Each rule = one bullet. No overlap with persona.
  </constraints>

  <protocols>
    Multi-step responses to specific triggers (e.g. symptom severity, error states).
  </protocols>

  <defaults>
    Numeric defaults the model should assume unless overridden.
  </defaults>
</guardrails>
```

</guardrails-file-format>

<review-checklist>

Run this checklist top-to-bottom on any prompt audit.

**Structure**
- [ ] One concern per file (persona / guardrails / schema / data)
- [ ] Consistent markup — XML wrapper covers all content, OR pure markdown, no mixing
- [ ] Priority list ≤ 5 items
- [ ] Each rule has clear scope (when it applies)

**Duplication**
- [ ] No rule appears verbatim in two files
- [ ] No rule appears as paraphrase in two files (search for synonyms)
- [ ] Internal duplications removed (same concept restated in 2+ priorities)

**Conflict resolution**
- [ ] Every pair of rules that could conflict has explicit precedence
- [ ] Persona ↔ guardrails precedence stated in guardrails
- [ ] Ordering conventions consistent across all sections

**User data leakage**
- [ ] No user names, conditions, history, or anchors hardcoded in persona
- [ ] User-specific facts live in user profile loader output
- [ ] Persona reads as reusable across users with same role

**References**
- [ ] Every file path mentioned exists in current repo
- [ ] Every tool name mentioned is actually wired up
- [ ] No leftover paths from migrated/legacy projects
- [ ] Acronyms defined at first use OR rely on user profile (e.g. HR zones anchored by `lthr`)

**Anthropic Claude 4.x specifics (April 2026)**
- [ ] System prompt uses XML tags for major sections (better than markdown headers for Claude 4.x scoping)
- [ ] Hard rules placed in dedicated guardrails block, not buried in persona prose
- [ ] Few-shot examples (if any) wrapped in `<examples>` and labeled with intent
- [ ] Output schema (if structured) declared explicitly, not inferred
- [ ] No conflicting "always X" + "never X" without precedence

</review-checklist>

<common-anti-patterns>

| Anti-pattern | Why bad | Fix |
|---|---|---|
| User facts hardcoded in persona | Drift when profile updates; not reusable | Move to user profile loader |
| Same rule in persona + guardrails | Double-weighted; divergence on edit | Single source; cross-reference if needed |
| 8+ "top priorities" | Model flattens weighting | Cap at 5; demote rest |
| Dead `.claude/shared/*` paths | Model hallucinates content | Inline or delete |
| `<system-role>` wrapping only intro, markdown headers below | Inconsistent scoping for Claude 4.x | Wrap whole file in one XML root |
| "Default push" + "Safety first" without precedence | Per-call ambiguity | State which wins |
| Mixed ordering ("front-load" + "context→action") | Inconsistent outputs | Pick one |
| Hypertrophy + recomp goals without trade-off rule | Arbitrary per-session choices | State explicit trade-off |

</common-anti-patterns>

<review-output-format>

When reporting a prompt review, structure findings as:

1. **Structural Issues** — markup, file separation, sizing
2. **Duplications** — within-file and cross-file, with line refs
3. **Convolutions / Logical Conflicts** — unresolved precedence, contradictions
4. **Misleading the Model** — dead refs, undefined acronyms, leaky abstractions
5. **Recommendations** — ordered, actionable, each tied to a checklist item

Use `[file.md:line](path#Lline)` markdown links for every reference so the user can jump.

End with: "Want me to draft revised version?" — do not auto-rewrite without confirmation.

</review-output-format>

<change-process>

When refactoring an existing prompt:

1. **Audit first, edit second.** Produce the structured report before touching files.
2. **Get user approval on the report** — prompt rewrites are subjective; align on direction first.
3. **Move user-specific facts to profile loader BEFORE deleting from persona** — avoid losing data.
4. **Verify dead refs by reading the cited paths** — do not assume. Some "dead" refs are real but moved.
5. **Run the model on a sample task before+after** if possible — verify behavior didn't regress.
6. **Update related files in same commit** — persona + guardrails + user profile changes ship together.

</change-process>
