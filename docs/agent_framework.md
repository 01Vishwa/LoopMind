# DS-STAR Agent Framework

The structural advantage of LoopMind relies entirely on its specialized agent methodology. We call this the **DS-STAR (Data Science - Self-Taught Agent with Reasoning)** Orchestrator. 

It handles complex multi-step logical operations through an iterative **Plan → Code → Execute → Verify → Route** cycle.

## Execution Lifecycle

The DS-STAR loop is managed by `DsStarOrchestrator`. It initiates concurrent streams mapping agent progress to frontend consumers while handling asynchronous wait/retry logic behind the scenes using `tenacity`.

```text
[User Prompt] -> Planner -> Coder -> Docker Sandbox -> Verifier -> [Pass] -> Output
                                                                -> [Fail] -> Router -> Planner (Retry)
```

## Agent Responsibilities

### 1. FileAnalyzerAgent
- **Purpose**: Consumes and interprets incoming unstructured datastores.
- **Core Function**: Extracts schematic structures, summaries, and logical relationships to append context to the planner.
- **Output**: Meaningful system context definitions.

### 2. PlannerAgent
- **Purpose**: Defines an exhaustive multi-step implementation approach.
- **Core Function**: Evaluates user prompts alongside the environment contexts to describe exact sequential computations, libraries, and logic structures required.
- **Output**: A declarative JSON/structured plan.

### 3. CoderAgent
- **Purpose**: Translates the logical plan into functional code.
- **Core Function**: Contextualizes the generated plan with specific framework capabilities (e.g., Pandas syntax, UI bounds) and generates syntactically valid Python.
- **Output**: Raw, executable `.py` strings.

### 4. CodeExecutor (Sandbox)
- **Purpose**: Environment runtime evaluation.
- **Core Function**: Dispatches the Coder's generated python into a secure, resource-constrained isolated Docker container. Limits external networking requests and halts infinite loops.
- **Output**: Extracts `stdout`, `stderr`, and specifically captures generated artifacts (e.g., Base64 encoded charts `.png` or tables `.csv`).

### 5. VerifierAgent
- **Purpose**: Assesses the generated logic map against reality.
- **Core Function**: Analyzes the original user-intent, the code produced, and the exact sandbox execution `stdout`/`stderr`. Determines if outputs answer the constraints safely.
- **Output**: Boolean `is_sufficient` state + reasoning string.

### 6. RouterAgent
- **Purpose**: Error-handling and contextual routing.
- **Core Function**: Triggered only upon a negative result from the Verifier. Evaluates the discrepancy (e.g., syntax error, logic fault, missed criteria) and re-evaluates the prompt state to send back towards the Planner.
- **Output**: Specialized error remediation directives.

## Failure Handling (Retry & Routing)

LoopMind agents handle inherent LLM unpredictability via overlapping strategies:
1. **Tenacity Execution Retries**: Local connectivity, parsing, or strict formatting failures implement immediate exponential backoff retries without triggering full loop restarts.
2. **Deterministic Routing**: If the sandbox breaks (tracebacks), the Verifier halts it, triggering the Router. The Router implements programmatic `max_rounds` constraints (default: 3) to prevent endless hallucination loops. Upgrades or refines instructions to the Planner to shift strategies.
