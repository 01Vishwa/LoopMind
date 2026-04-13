# Retriever

## Model
Uses a local hardware-accelerated embedding model via `sentence-transformers` (specifically `all-MiniLM-L6-v2`). This serves as an LLM-free retriever structure utilizing CPU evaluation to spare API costs. 

## Tools
Operates exclusively using pure `numpy` vector mathematics to calculate bounded Cosine Similarity `[-1, 1]`. Features a robust fallback scoring system mapping Keyword overlap (TF-IDF) if `sentence-transformers` libraries are missing.

## Orchestration Layer
An upstream layer preceding standard DS-STAR processing loops. When multiple heterogeneous files are dumped into the system environment crossing max token thresholds, the retriever intercepts context embeddings. Computes similarities sequentially and yields only the `Top-K` files directly relevant to the user query constraint.

## Deployment
Configured tightly within the backend core `retrieval` path to serve as a fast filtering gateway. Extends standard orchestration capabilities by truncating unneeded data boundaries.
