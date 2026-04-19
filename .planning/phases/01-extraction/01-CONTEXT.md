# Phase 01: Context

## Decisions

- **Extraction Pipeline Control Flow**: Synchronous Loop
  - Rationale: Simpler to implement. We will test the actual delay in reality before optimizing.
  - Details: Implement a progress bar in the CLI during the synchronous fetch.
- **Pydantic AI Output Format**: Loose Strings
  - Rationale: The legacy outputs are highly creative and variable (as shown by past summary data). Wrapping everything in strict enums would be too rigid. Let the LLM output free text for maximum flexibility.
- **HITL Feedback UI**: Just highlights
  - Rationale: Follows communication rules from szymi-blueprint to prevent terminal flooding. Details are hidden until the final write to Notion.

## Deferred Ideas

- Refactor Extraction Pipeline Control Flow to use asynchronous/concurrent fetching (e.g. `asyncio.gather`) if the synchronous delay proves to be too slow in practice.

## Canonical Refs

- `.planning/phases/01-extraction/01-SPEC.md`
- `.planning/ROADMAP.md`
