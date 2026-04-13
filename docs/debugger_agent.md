# DebuggerAgent

## Model
Uses the Pro model tier (`NIM_MODEL_PRO`). Debugging requires precise traceback interpretation, high fidelity code logic analysis, and targeted script surgery.

## Tools
Uses `.with_structured_output()` mapped to Pydantic (`DebuggerOutput`) to enforce structural integrity during code replacement routines. Outputs corrected code, error type, and a fix summary.

## Orchestration Layer
Operates as a rapid sub-loop interceptor. When `CodeExecutor` throws a fatal traceback (e.g., `SyntaxError`, `IndexError`), the `DebuggerAgent` intercepts it, isolating the specific failing segment. Rather than regenerating the script completely (which risks breaking stable logic), it performs a surgical rewrite of the faulty lines and re-injects it immediately to the executor.

## Deployment
Executed within the orchestration loop engine block, functioning directly alongside the `CodeExecutor`.
