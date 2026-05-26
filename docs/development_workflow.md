# Development Workflow

How features, refactors, and bug fixes move from idea to shipped code. Uses two skill sets: Matt Pocock's engineering skills for project management, and superpowers for implementation.

## Skill Inventory

### Project Management (Matt Pocock)

| Skill | When to use |
|-------|-------------|
| `/grill-me` | Stress-test a rough plan or design. Walks each branch of the decision tree, one question at a time. |
| `/grill-with-docs` | Same grilling, but challenges the plan against `CONTEXT.md` vocabulary and existing ADRs. Updates docs as decisions crystallize. |
| `/improve-codebase-architecture` | Find refactoring targets. Surfaces "deepening opportunities" — shallow modules that should be deep. |
| `/diagnose` | Hard bugs and performance regressions. Disciplined loop: reproduce → minimize → hypothesize → instrument → fix → regression test. |
| `/to-prd` | Formalize what you're building into a PRD (problem, solution, user stories, implementation decisions, testing decisions). |
| `/to-issues` | Break a PRD into independently-implementable vertical slice issues (tracer bullets). Labels each AFK or HITL. |
| `/triage` | Move issues through state machine: `needs-triage` → `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix`. |
| `/setup-matt-pocock-skills` | One-time setup: configure issue tracker location, triage labels, domain doc layout. |

### Implementation (Superpowers)

| Skill | When to use |
|-------|-------------|
| `/brainstorming` | Structured ideation before committing to an approach. |
| `/writing-plans` | Turn one issue into a step-by-step implementation plan. Bite-sized tasks (2-5 min each) with exact file paths, code, and test commands. |
| `/subagent-driven-development` | Execute a plan automatically. Fresh subagent per task, two-stage review (spec compliance then code quality). |
| `/executing-plans` | Alternative to subagent-driven: execute plan inline in current session. Better for tightly coupled tasks. |
| `/test-driven-development` | Red-green-refactor discipline. Used automatically by implementation subagents. |
| `/systematic-debugging` | Structured debugging when you hit a bug during implementation. |
| `/using-git-worktrees` | Create isolated git worktree so work doesn't interfere with main branch. |
| `/requesting-code-review` | Dispatch a reviewer subagent with structured review template. |
| `/receiving-code-review` | Process and address review feedback. |
| `/finishing-a-development-branch` | Final verification, cleanup, merge preparation. |
| `/verification-before-completion` | Checklist verification before declaring "done." |

## Flows

### New Feature

```
/grill-with-docs        ← stress-test the idea, update CONTEXT.md and ADRs
/to-prd                 ← formalize into PRD with user stories
/to-issues              ← break into vertical slice issues
/triage                 ← label each issue (ready-for-agent, etc.)

Per issue:
  /writing-plans                    ← step-by-step implementation plan
  /subagent-driven-development      ← execute plan with reviews
  feature-tester agent              ← test coverage for changed behavior
  documentation-developer agent     ← non-obvious constraint docs
  /requesting-code-review           ← final review
  /finishing-a-development-branch   ← merge
```

### Architecture Improvement

```
/improve-codebase-architecture  ← find deepening opportunities
/grill-me                       ← stress-test proposed refactors
/to-prd                         ← formalize chosen refactors
/to-issues                      ← break into issues
Per issue: same as above
```

### Bug Fix

```
/diagnose       ← reproduce, minimize, find root cause
/to-issues      ← create fix issue (often just one)
/writing-plans  ← plan the fix
/subagent-driven-development    ← implement with reviews
feature-tester agent            ← test coverage
documentation-developer agent   ← docs if needed
```

### Quick Change (no formal spec needed)

For small, well-understood changes that don't need a PRD or issues:

```
/writing-plans                    ← plan directly from conversation
/subagent-driven-development      ← execute
```

## Custom Agents

After superpowers execution and before final review, run two project-specific agents from `.dev-agents/`:

| Agent | Purpose | Invoke with |
|-------|---------|-------------|
| `feature-tester` | Write focused tests for changed behavior. Owns test plan, unit tests, small integration tests. | "use feature-tester agent" |
| `documentation-developer` | Add minimal code documentation. Owns non-obvious contract docs, inline why-comments, comment cleanup. | "use documentation-developer agent" |

These are persona agents (scoped ownership), not process skills. They stay as agents — skills are for multi-step workflows and decision trees, agents are for "adopt this role and apply judgment."

## Issue Tracker

Issues live as local markdown files in `specs/issues/`. Feature specs and PRDs live in `specs/<feature-slug>/`. See `docs/agents/issue-tracker.md` for conventions.

## Where Things Live

| Artifact | Location |
|----------|----------|
| Step specs | `specs/steps/step-*.md` |
| Feature specs and PRDs | `specs/<feature-slug>/` |
| Issues | `specs/issues/` |
| Implementation plans | `docs/superpowers/plans/` |
| Architecture reviews | `docs/superpowers/reviews/` |
| Decision log | `specs/decision-log.md` |
| Domain glossary | `CONTEXT.md` |
| ADRs | `docs/adr/` |
