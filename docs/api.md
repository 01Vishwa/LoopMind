# REST API Endpoints

The Semantica backend uses FastAPI. All endpoints are prefixed with `/api`. Note that Vite proxies the `/api` route directly to `http://localhost:8000/api` during development.

## Setup & File Management

### `POST /api/upload`
Validates and persists uploaded files safely into the system's temporary context constraint.
- **Payload**: `multipart/form-data` with `files` (array of `UploadFile`).

### `POST /api/process`
Processes the cached files into a normalized in-memory context that provides context to the agents.
- **Payload**: `{"files": ["array", "of", "filenames"]}`

### `DELETE /api/clear`
Wipes the internal global processing and byte contexts for fresh restarts.

## DS-STAR Agent Loop

### `POST /api/agent/run`
Streams the DS-STAR agent events sequentially utilizing Server-Sent Events (SSE). Emits `event` structures outlining `"analyzing"`, `"planning"`, `"coding"`, `"execution_result"`, `"artifact"`, `"verification_result"`, and `"metrics"`.
- **Payload**: `AgentRunRequest` context defining the `session_id`, `max_rounds`, LLM models, and `query`.

## History Management (Supabase)

### `GET /api/agent/runs`
Lists past agent runs for a specific user from Supabase.
- **Parameters**: `user_id` (optional), `limit` (default: 20).

### `GET /api/agent/runs/{run_id}`
Retrieves all telemetry, details, and prompts belonging to a single agent run execution.
