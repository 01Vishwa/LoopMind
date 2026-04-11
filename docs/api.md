# REST API Endpoints

The LoopMind backend leverages FastAPI. All HTTP interactions are prefixed with `/api`.
*(Note: Vite locally proxies frontend `/api` requests directly to `http://localhost:8000/api`)*

---

## 1. Context & File Management

### `POST /api/upload`
Validates and safely persists uploaded context documents into the system's temporary constraint memory. Expects `multipart/form-data`.
- **Request Body**: `files` (Array of `UploadFile`)
- **Response**:
  ```json
  {
    "message": "Files uploaded successfully.",
    "files": ["data.csv", "report.txt"]
  }
  ```

### `POST /api/process`
Instructs the File Analyzer logic to parse in-memory document structures, building normalized context boundaries.
- **Request Body**:
  ```json
  {
    "files": ["data.csv", "report.txt"]
  }
  ```
- **Response**: Context processing metadata.

### `DELETE /api/clear`
Nullifies global cache states, resetting data constraints safely.

---

## 2. DS-STAR Agent Loop

### `POST /api/agent/run`
The primary interaction endpoint. Streams the DS-STAR agent lifecycle sequentially utilizing **Server-Sent Events (SSE)**.

- **Request Payload**: 
  ```json
  {
    "session_id": "uuid-v4-string",
    "query": "Generate a plot of the uploaded customer metrics.",
    "max_rounds": 3
  }
  ```
- **Response Stream (`text/event-stream`)**:
  Emits parsed line events updating real-time statuses.
  ```text
  data: {"event": "status", "data": "analyzing"}
  data: {"event": "status", "data": "planning"}
  data: {"event": "status", "data": "coding"}
  data: {"event": "execution_result", "data": {"stdout": "Success", "stderr": ""}}
  data: {"event": "artifact", "data": {"type": "image/png", "content": "base64..."}}
  data: {"event": "verification_result", "data": {"passed": true}}
  data: {"event": "metrics", "data": {"time": 1.2, "loops": 1}}
  ```

---

## 3. History & Telemetry (Supabase)

### `GET /api/agent/runs`
Retrieves paginated analytics representing agent telemetry histories.
- **Query Parameters**:
  - `user_id` (string, optional)
  - `limit` (integer, default: 20)
- **Response**: Array of execution summarizations.

### `GET /api/agent/runs/{run_id}`
Retrieves deep diagnostic telemetry detailing execution contexts, explicit prompt definitions, and loop timelines for a unique run.
- **Response**: Detailed JSON encapsulating full `CodeExecutor` histories and `Planner` logic maps.
