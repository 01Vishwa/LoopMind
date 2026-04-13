# CodeExecutor

## Model
LLM-free execution sandbox component. It is a strict runtime environment built on top of the Python ecosystem. 

## Tools
Relies on Docker sandboxing for isolating generated code (using containerization features to limit CPU/Memory via `--network none` when enabled). Alternatively uses a subprocess sandbox with a sanitized environment. Included tools consist of standard PyData ecosystems (Pandas, Scikit-learn, Matplotlib).

## Orchestration Layer
Executes after the `CoderAgent` successfully yields a script. Injects target outputs into a local runtime block and evaluates logic, extracting `stdout`, `stderr`, and capturing graphical assets resulting from Matplotlib renders. Its output determines whether the pipeline jumps to the Verifier or Router.

## Deployment
Executes generated code in a `python:3.11-slim` container (when `DOCKER_SANDBOX_ENABLED=true`) or via a managed async Python subprocess locally.
