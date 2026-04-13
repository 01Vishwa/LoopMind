# ReportWriterAgent

## Model
Uses the Flash model tier (`NIM_MODEL_FLASH`). Primarily tasked with report consolidation and aggregation formatting which operates stably at this processing constraint.

## Tools
Applies strict logic `.with_structured_output()` aligned to `ReportOutput`. Enforces citation rules directly mapping paragraph deductions directly into `[Q1]`, `[Q2]` referencing points.

## Orchestration Layer
Exclusive to the `DS-STAR+` mode operations. Functions identically to a closing finalizer but spans parallel multi-threads. Synthesizes outputs originating from multiple disjointed DS-STAR concurrent loops and binds them under unified structured components (e.g., body, caveats, key findings, executive summaries). Prevents hallucination limits by restricting general findings to concrete statistics pulled directly from context runs.

## Deployment
Serves as the concluding step in a global `DS-STAR+` tree sequence, returning the conclusive JSON layout back towards API response handlers.
