# SubQuestionGeneratorAgent

## Model
Uses the Flash model tier (`NIM_MODEL_FLASH`) due to rapid evaluation and the inherent simplicity involved with segmenting questions rather than deeply reasoning about answers.

## Tools
Relies on Langchain `.with_structured_output()` and `SubQuestionsOutput` Pydantic models. Limits output ranges securely (between 2 to 8 maximum questions per operation).

## Orchestration Layer
Exclusive to the `DS-STAR+` mode operations. Resides before the initial branching pathways. Receives an open-ended super query alongside file summaries and breaks them down into atomic, independently solvable sub-questions. Enables massive parallelism as each sub-question spins up its own localized DS-STAR execution instance.

## Deployment
Deployed tightly to `ds_star_plus` operational loops, serving strictly nested multi-question routing matrices.
