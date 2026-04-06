# System Architecture

Semantica is designed around a modular, modern stack consisting of a React + Vite frontend and a FastAPI (Python) backend. The platform provides an intelligent document processing pipeline driven by a complex AI agent loop.

## High-Level Overview

### 1. Frontend (Vite + React)
The frontend is a single-page application (SPA) built with React 19.
- **Styling**: Tailwind CSS and simple CSS files.
- **Routing/State**: Component-level state with custom hooks (e.g., `useAgentRun`).
- **Communication**: Uses standard `fetch` API for REST operations (upload, process) and Server-Sent Events (SSE) for streaming real-time agent output.

### 2. Backend (FastAPI)
The central intelligence of the platform lives in a FastAPI application (`backend/main.py`).
- **Core Orchestrator**: Manages AI workflows asynchronously (DS-STAR protocol).
- **LLM Integration**: LangChain integration strictly coupled to NVIDIA NIM endpoints.
- **REST Endpoints**: Routes for uploading files, analyzing data context, and running the agent loop.

### 3. State Persistence (Supabase)
Supabase is used as the remote datastore.
- The `services/supabase_service.py` handles writing tracking metrics, user agent histories, and statuses for each run execution.
- Enables history fetching via the `/agent/runs` endpoints.

## Data Flow

1. **Ingest Phase**: Files are uploaded via the `/api/upload` endpoint and validated.
2. **Contextualizing**: The `/api/process` endpoint triggers extraction/processing on the uploaded files and constructs a `_processing_context`.
3. **Execution**: The user sends a task/query via SSE to `/api/agent/run`. The orchestrator executes the Plan-Code-Execute-Verify loop.
4. **Metrics**: Performance constraints like memory/time and agent loop complexities are saved to Supabase upon completion.
