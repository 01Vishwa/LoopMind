# Semantica

Semantica is an **Intelligent Document Processing (IDP)** Platform powered by an iterative Data Science AI. At its core lives the **DS-STAR Agent Framework**, an AI loop that reads data, plans, codes, executes locally, and self-verifies.

![React](https://img.shields.io/badge/React-19-blue?logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-green?logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)

## 📖 Deep Dive Documentation
Everything regarding the underlying framework logic and structure is documented in our new `docs/` folder:

- 🏗️ **[System Architecture](docs/architecture.md)** — Explores the structural design, tech stack overview, and interaction between the Vite Frontend, FastAPI Backend, and Supabase persistent layers.
- 🤖 **[DS-STAR Agent Framework](docs/agent_framework.md)** — Breakdown of the iterative workflow consisting of specialized LLMs: `FileAnalyzerAgent`, `PlannerAgent`, `CoderAgent`, `VerifierAgent`, `RouterAgent`.
- 🔌 **[API Reference](docs/api.md)** — The definitions of the REST and the core SSE streaming endpoints.
- 🎨 **[Frontend Architecture](docs/frontend.md)** — Breakdown of Vite, React Hook states, and UI components used.

---

## 🚀 Quick Start / Local Setup

### 1. Requirements
Ensure you have the following installed:
- [Node.js (18+)](https://nodejs.org/)
- [Python 3.10+](https://www.python.org/)

### 2. Backend Setup
Set up the python environment and run the backend endpoints:
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate.ps1  |  Mac/Linux: source venv/bin/activate
pip install -r requirements.txt

# Environment Setup
cp .env.example .env
# Edit your .env with your LLM Endpoints (like NIM) & Supabase credentials

# Run Server
python main.py
```
> Fast API will start serving at `http://localhost:8000`

### 3. Frontend Setup
Run the development environment in a new terminal prompt:
```bash
# From root directory
npm install
npm run dev
```
> The vite proxy will automatically link `/api` calls to the python port. Follow the output URL (`localhost:5173` typically) to launch the app UI.
