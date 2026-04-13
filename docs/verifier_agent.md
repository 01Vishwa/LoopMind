# VerifierAgent

## Model
Uses the Pro model tier (`NIM_MODEL_PRO`) for complex deductive reasoning. The model acts as the quality-control judge.

## Tools
Leverages `.with_structured_output()` to strictly output boolean assessments (`is_sufficient`) and a corresponding string reason.

## Orchestration Layer
Evaluates the execution pipeline's output against the original context and analysis plan. If the code execution satisfies the current step constraint, it passes the data pipeline forwards (to the `FinalizerAgent`). If deficient or error-prone, it flags the cycle as failed and halts progress, prompting a fallback directly to the `RouterAgent`.

## Deployment
Resides deeply within the retry loop of the `DsStarOrchestrator`.
