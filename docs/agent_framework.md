# DS-STAR Agent Framework

The backbone of Semantica is the DS-STAR (Data Science - Self-Taught Agent with Reasoning) Orchestrator. It implements an iterative Plan → Code → Execute → Verify → Route cycle.

## Loop Lifecycle

The `DsStarOrchestrator` (`backend/core/ds_star_orchestrator.py`) handles all state and SSE streaming of agent steps to the frontend. Wait and retry policies back each of these agents through `tenacity`.

### 1. FileAnalyzerAgent
- **Purpose**: Consumes incoming datasets or extracted texts.
- **Action**: Constructs meaningful context definitions or summaries of the data for the planner to interpret.

### 2. PlannerAgent
- **Purpose**: Creates an initial multi-step execution plan based on the user's query and the data descriptions.
- **Action**: Defines what sequential computations, charting, or algorithms are required.

### 3. CoderAgent
- **Purpose**: The primary code author.
- **Action**: Reads the plan, user input, and context, and generates syntactically valid Python code meant to answer or process the user request.

### 4. CodeExecutor
- **Purpose**: Provides an isolated runtime environment to run the code securely.
- **Action**: Extracts `stdout`, `stderr`, and specifically captures generated artifacts like `.png` charts or `.csv` files as Base64 encoded outputs.

### 5. VerifierAgent
- **Purpose**: Checks the executed code against the original user query and execution outputs.
- **Action**: Determines if the generated results securely and accurately answer the prompt (`is_sufficient`).

### 6. RouterAgent
- **Purpose**: Handles insufficiency.
- **Action**: If the Verifier evaluates the result as inadequate, the Router evaluates why and chooses whether to fix a specific plan step, add a step, or change direction before pushing back up to the Coder.

## Metrics & Observability
Metrics (`models/metrics_schema.py`) log execution time of specific phases (planner, coder, verifier) and the number of loop iterations required prior to successful verification or hard stop limits (`max_rounds`).
