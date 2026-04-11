# Frontend Architecture

LoopMind's frontend relies on a reactive, modern Single-Page Application (SPA) architecture constructed with Vite and React 19. The system emphasizes low-latency updates when managing long-lived server streaming events.

## Tech Stack

- **Framework**: React 19 + Vite
- **Styling**: Tailwind CSS + raw Vanilla PostCSS setup
- **Icons**: `lucide-react`
- **Toasts**: `react-hot-toast`

## Component Structure

The interface relies on atomic, modular components:
- **`App.jsx`**: Central application wrapper mapping routing states and providing the global context `ToastContainer`.
- **`HomePage`**: Primary user engagement perspective encapsulating file uploads and prompt configurations.
- **`HistoryPanel`**: Real-time diagnostic viewer fetching Supabase-powered global histories (`/api/agent/runs`).
- **`AgentStatusView`**: Granular UI interpreting local SSE streams into UI progress indicators (loading bars, status ticks).

## State Management (Hooks)

Maintaining synchronous interactions while heavily parsing dynamic SSE string objects dictates our architecture rules.

- **Component-Level Bound State**: Pure UI states (dropdowns, inputs) use local `useState`.
- **Complex Event Streams (`useAgentRun.js`)**: 
  A dedicated asynchronous context hook that abstracts connection mechanics.
  - Consumes the `fetch` body via `getReader()`.
  - Continuously parses fragmented buffer bytes into valid `JSON` payload objects.
  - Yields discrete React states: `isStreaming`, `agentPhase` (analyzing, planning, coding, etc.), `artifacts`, and `errors`.

## API Integration Strategy

Network connectivity implements simple abstractions:
1. Standard data payloads (uploading chunks, fetching history JSON) rely heavily on conventional `async/await fetch()` with basic try/catch wrappers.
2. **Server-Sent Events**: Replaces WebSockets for unilateral server-to-client streaming during loops, heavily simplifying connection teardown constraints. State accumulation appends logic to arrays rather than replacing states entirely.

## Streaming Handling & Edge Cases

The `/api/agent/run` endpoint presents connection instability challenges natively. The frontend manages this actively:
- **Chunk Reassembly**: Stream buffers handle byte divisions dynamically to ensure `JSON.parse` does not break on cross-network fragments.
- **Early Termination**: Discard mechanisms trigger automatically on Unmount to release hanging `Reader` locks.
- **Stream Resiliency**: Implements visual `max_rounds` loops gracefully to ensure the UI represents "retry" phases without indicating explicit failures immediately.

## Custom API Proxy Configuration

> [!IMPORTANT]
> The `vite.config.js` maintains strict Cross-Origin bounds without requiring backend exceptions.
> Vite heavily leverages HTTP proxy bindings to channel UI traffic hitting `/api/*` directly across to `http://localhost:8000/api` transparently. Ensure identical setups during production configurations (Nginx/Traefik).
