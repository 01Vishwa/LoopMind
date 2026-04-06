"""FileAnalyzerAgent — Stage 1 of the DS-STAR pipeline.

Converts the already-parsed ``combined_extractions`` context map into a rich
textual data description that grounds all subsequent LLM-agent prompts.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger("uvicorn.info")


class FileAnalyzerAgent:
    """Generates a structured textual summary of all data files in context.

    Instead of re-running file I/O, this agent consumes the normalised
    ``UnifiedDocumentContext`` dicts already produced by the process pipeline
    and synthesises a plain-English description of each file's structure,
    columns, dtypes, and sample rows.
    """

    def analyze(self, combined_extractions: Dict[str, Any]) -> str:
        """Builds a data description from the processing context.

        Args:
            combined_extractions (Dict[str, Any]): Keyed by filename, each
                value is a ``UnifiedDocumentContext``-shaped dict.

        Returns:
            str: Multi-section plain-English data description.
        """
        if not combined_extractions:
            return "No data files are available in the current context."

        sections = ["=== DATA DESCRIPTION ===\n"]

        for filename, doc in combined_extractions.items():
            if not isinstance(doc, dict):
                continue

            source_type = doc.get("source_type", "unknown").upper()
            content = doc.get("sanitized_content", "")
            metadata = doc.get("metadata", {})

            section = [f"--- File: {filename} (type: {source_type}) ---"]

            # Structured metadata (CSV / XLSX / JSON)
            if "columns" in metadata:
                section.append(f"  Columns     : {metadata['columns']}")
            if "dtypes" in metadata:
                section.append(f"  Data Types  : {metadata['dtypes']}")
            if "shape" in metadata:
                section.append(f"  Shape       : {metadata['shape']}")
            if "row_count" in metadata:
                section.append(f"  Row Count   : {metadata['row_count']}")
            if "sample_rows" in metadata:
                section.append(f"  Sample Rows : {metadata['sample_rows']}")
            if "keys" in metadata:
                section.append(f"  JSON Keys   : {metadata['keys']}")
            if "pages" in metadata:
                section.append(f"  Pages       : {metadata['pages']}")

            # For unstructured formats include a larger full-text block so the
            # CoderAgent can work with the text directly without needing to
            # open any raw file at execution time.
            if content:
                if source_type in {"PDF", "TXT", "MD", "MARKDOWN", "UNKNOWN"}:
                    full_text = content[:6000]
                    section.append(
                        f"  Full Text Content (use this directly in code — do NOT open the file):\n"
                        f"{full_text}"
                    )
                else:
                    preview = content[:4000].replace("\n", " ")
                    section.append(f"  Content Preview: {preview}")

            if "error" in metadata:
                section.append(f"  ⚠ Parse Error: {metadata['error']}")

            sections.append("\n".join(section))

        description = "\n\n".join(sections)
        logger.info("[FileAnalyzer] Generated data description (%d chars)", len(description))
        return description
