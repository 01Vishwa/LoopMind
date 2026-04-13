# CoderAgent

## Model
Uses the Pro model tier (`NIM_MODEL_CODER` / `NIM_MODEL_PRO`) due to its strong Python coding capabilities, syntax correctness, and ability to handle large token-window accumulative coding logic.

## Tools
Leverages Langchain's `.with_structured_output()` ensuring generation of complete, raw, self-contained Python scripts unpolluted by markdown or conversational text.

## Orchestration Layer
Follows the `PlannerAgent` within the primary execution cycle. Acts somewhat like an autonomous Jupyter notebook—extending existing scripts, appending new data-handling/analysis chunks depending on the currently focused plan step, and reacting gracefully to previously failed executions by analyzing stack trace context. 

## Deployment
Deployed in the backend engine block. Its output string is immediately digested by the `CodeExecutor` sandbox.
