# PlannerAgent

## Model
Uses the Pro model tier (`NIM_MODEL_PRO` / `NIM_MODEL_DEFAULT`), which acts as the core reasoning engine. Designed to handle deep context scaling and logical strategy generation.

## Tools
Utilizes Langchain's `.with_structured_output()` mechanism to enforce strict schema-compliance using Pydantic (`PlanOutput`).

## Orchestration Layer
Functions as the primary strategic controller in the DS-STAR loop. Evaluates user intent against environment context (e.g., File summaries) to build a step-by-step logic map. When guided by the `RouterAgent`, the Planner can mutate its plan dynamically (Add Step, Fix Step, Remove Steps) to adapt to changing environments or previous execution failures.

## Deployment
Runs within the core DS-STAR loop engine block located in the backend orchestrator. Thread-safe execution wrapper.
