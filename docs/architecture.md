# System Architecture

LoopMind is developed utilizing a scalable, modern architecture combining a reactive User Interface with a highly async-focused Python backend, aimed at processing complex inference loops securely.

## High-Level System Design

The application is structured into three primary tiers:

1. **Presentation Layer (Frontend)**
   Built on React 19 and Vite. Designed to respond instantaneously to reactive datasets and real-time streaming states. Components communicate exclusively via clean HTTP/REST and consume SSE connections dynamically.

2. **Application Layer (FastAPI Backend)**
   The backend logic, written in Python 3.10+, routes tasks and heavily utilizes asynchronous I/O to ensure the high-latency LLM inference calls do not block the active process loop. FastAPI guarantees schema rigor via Pydantic.

3. **Data & Observability Layer (Supabase)**
   Used to persist complex relational telemetry data (agent cycles, inference times, generated context). Supabase ensures stateless backend environments can rapidly spin up and tear down.

## Component Interaction

- **Client → Backend Router**: Standard REST API calls execute initial configuration (file uploads, initial validations).
- **Backend Router → Orchestrator**: User prompts initiate a workflow inside the `DsStarOrchestrator`.
- **Orchestrator → Agents**: The orchestrator triggers individual LangChain-backed agent classes (`PlannerAgent`, `CoderAgent`), parsing specific prompt configurations and injecting available system metadata.
- **Agent → LLM**: Queries are evaluated via LangChain connected exclusively to NVIDIA NIM endpoints.
- **Orchestrator → Frontend**: While waiting for execution loops and code interpretation, the orchestrator emits strict Server-Sent Events (SSE) detailing its phase (e.g., `planning`, `executing`), including serialized string fragments and parsed tool messages.

## Data Flow Lifecycle

> [!NOTE]
> Ensuring a strict context barrier between untrusted dataset ingestion and secure LLM inference is critical. LoopMind implements a highly constrained sandbox protocol.

1. **Multi-Modal Ingestion**: Clients upload data (CSV, TXT, images) to `/api/upload`.
2. **Context Normalization**: The backend digests inputs via `FileAnalyzerAgent` and constructs an isolated memory context layout (`_processing_context`).
3. **Execution Request**: The user submits a natural-language query sent via SSE connection to `/api/agent/run`.
4. **Agent Loop**: The `DsStarOrchestrator` runs its loop:
   - Evaluates intention (`Planner`).
   - Generates executable scripts (`Coder`).
   - Executes via Docker Sandbox (`CodeExecutor`).
   - Evaluates final runtime state securely (`Verifier`).
5. **Persistence**: Execution statistics, token approximations, and prompt summaries are shipped asynchronously to Supabase.

## Scalability Considerations

- **Stateless Backend Design**: The FastAPI server holds zero critical memory states across active queries (outside of temporary uploaded contexts), making it instantly horizontally scalable.
- **Docker Sandbox Limitation**: The built-in `CodeExecutor` securely sandboxes runtime execution to limit untrusted generated-code side-effects. Scaling this requires mapping Docker deployment constraints properly to host nodes.
- **Supabase Scaling**: Metrics rely heavily on normalized relational insertions. Supabase scaling guarantees robust caching for historical agent review (`/api/agent/runs`).
- **SSE Stream Handling**: Server-Sent Events are bound by long-lived connections. Horizontal scaling requires proper load balancers capable of sustained connections without aggressive proxy-timeouts.
