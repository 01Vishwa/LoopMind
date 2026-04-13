# RouterAgent

## Model
Functions using the standard reasoning model (`NIM_MODEL_DEFAULT`), equipped to handle pathing logic based on execution telemetry.

## Tools
Uses `.with_structured_output()` mapped to Pydantic (`RouterOutput`), defining specific architectural actions: `ADD_STEP`, `FIX_STEP`, or `REMOVE_STEPS`.

## Orchestration Layer
Acts as the fallback recovery system within the DS-STAR architecture. Triggered only if the `VerifierAgent` rejects an execution outcome or if there's a fatal traceback. Evaluates why the failure occurred and rewires the `PlannerAgent` logic state, shifting strategy to prune failing step branches or amend specific sub-tasks to try again.

## Deployment
Maintained as the loop-reset engine block within the orchestration backend.
