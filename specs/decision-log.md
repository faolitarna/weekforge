# Architectural Decision Log

This log records technical decisions that resolve ambiguity, deviate from the initial spec, or introduce new constraints.

| Date | ID | Decision | Context | Spec Impact |
|---|---|---|---|---|
| 2026-04-10 | DEC-001 | Decompose Monolithic Spec | The `Migration-Spec.md` was too large (399 lines) to review and track effectively, leading to SDD failures. | Triggered the creation of the multi-file spec suite and this decision log. |
| 2026-04-11 | DEC-002 | Consolidate Phase 0 contracts into WF-00 | Phase 0 infrastructure contracts (Notion Tool Layer, Model Config, CLI, Secrets, Tooling Standards) were scattered across conceptual descriptions with no implementation-level detail. Cross-cutting stubs (WF-OBS, WF-TEST, WF-PROMPT) were incorrectly tagged as Phase 0. | WF-00 bumped to v1.1 with six new sections (§3-§8). Cross-cutting stubs re-phased to post-Phase 0. Dashboard reorganized by phase. WF-04 Phase 0 section slimmed to reference WF-00. |
| 2026-04-14 | DEC-003 | Extract data_source_id for Notion DB Queries | Notion SDK 3.0.0 (API v2025-09-03) dropped `databases.query` and formally decoupled Databases (views) from Data Sources (records). | The `query(database_id)` contract in step-0b remains stable, but the `notion.py` tool implementation internally refactored to fetch the database, extract `data_source_id`, and query it via `data_sources`. |
