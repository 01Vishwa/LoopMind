# FinalizerAgent

## Model
Uses the Flash model tier (`NIM_MODEL_FLASH`). Formatting execution output is largely deterministic and requires low reasoning effort, enabling cost-saving and latency reduction.

## Tools
Uses `.with_structured_output()` aligned with `FinalizerOutput` to yield a consistent headline, cleanly constructed markdown summary, and internal confidence score.

## Orchestration Layer
Takes raw terminal outputs, log dumps, and variable states from the last successful sandbox run, and formats them into a clean, human-readable response layout. Enforces no-hallucination policies and applies warnings or caveats securely.

## Deployment
Triggers linearly at the end of the `DsStarOrchestrator` chain upon a `Pass` response from the `VerifierAgent`. Produces the last programmatic payload handed to the REST API frontend mapping logic.
