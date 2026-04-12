---
id: WF-OBS
title: Observability & Metrics
status: not-started
version: 0.1
last-updated: 2026-04-11
depends-on: [WF-00]
implements-phase: [1, 2, 3]
---

# Observability & Metrics

> **Note:** Basic per-call LLM metadata (model, latency, tokens, cost) and run-level cost accumulation are defined in [WF-00 §4 — Model Configuration Layer](../00-system-overview.md). This spec covers aggregation, persistent storage, analysis, and drift detection of that data.

## TODO: Define this spec

This spec should cover:

- **LLM Call Logging:** Persistent storage and retrieval of per-call metadata captured by the model configuration layer.
- **Run-Level Metrics:** Aggregated cost, total time, retry counts across complete graph runs.
- **Drift Detection:** Monitoring Evaluator rejection rates over time (signals degrading prompt quality).
- **Checkpoint Auditing:** How to inspect or replay a checkpoint for debugging.
