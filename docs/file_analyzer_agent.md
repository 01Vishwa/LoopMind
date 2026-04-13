# FileAnalyzerAgent

## Model
Uses the Flash model tier (`NIM_MODEL_FLASH`) as defined in `config.py`. The Flash model is selected for its high throughput and cost-efficiency, which is suitable for summarizing and categorizing structured/unstructured files.

## Orchestration Layer
Operates as the initial preprocessing step in the DS-STAR run. By consuming unstructured datastores, it extracts semantic structures, summary statistics, column relationships, and generates context descriptions. This extracted metadata is then forwarded to the `PlannerAgent` schema creation process.

## Deployment
Runs within the backend orchestrator loop asynchronously prior to initiating the core DS-STAR Plan/Code loop. Allows context ingestion of varied dataset file uploads.
