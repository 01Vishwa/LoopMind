"""JSON file parser.

Reads structured JSON payloads and returns validated root objects formatted
within the standardised UnifiedDocumentContext shape.

Fix: Renamed ``keys_present`` → ``keys`` and ``data_preview`` → ``sample_rows``
to match the key contract expected by FileAnalyzerAgent.  Also handles JSON
arrays properly by producing columnar metadata when the root is a list of dicts.
"""

import json
from typing import Any, Dict, List

from core.validation import sanitize_text


def parse_json(file_name: str, file_content: bytes) -> Dict[str, Any]:
    """Parses a JSON file in-memory into UnifiedDocumentContext format.

    Args:
        file_name: Path alias or filename.
        file_content: Raw JSON data as bytes.

    Returns:
        Dict[str, Any]: Unified map containing JSON preview and metadata.

    Raises:
        ValueError: If the file is not valid JSON.
    """
    try:
        data = json.loads(file_content.decode("utf-8"))

        raw_string_data = json.dumps(data, indent=2)
        sanitized = sanitize_text(raw_string_data)

        # Build metadata matching FileAnalyzerAgent key contract
        metadata: Dict[str, Any] = {}

        if isinstance(data, dict):
            metadata["keys"] = list(data.keys())          # matches analyzer L59
            # Try to surface sample rows if values are list-of-dicts
            first_list = next(
                (v for v in data.values() if isinstance(v, list)), None
            )
            if first_list and all(isinstance(r, dict) for r in first_list[:5]):
                sample: List[Dict] = first_list[:5]
                metadata["columns"] = list(sample[0].keys()) if sample else []
                metadata["sample_rows"] = sample
                metadata["row_count"] = len(first_list)
            else:
                metadata["sample_rows"] = sanitized[:500]

        elif isinstance(data, list):
            metadata["keys"] = ["root_list"]
            metadata["row_count"] = len(data)
            if data and all(isinstance(r, dict) for r in data[:5]):
                sample = data[:5]
                metadata["columns"] = list(sample[0].keys()) if sample else []
                metadata["sample_rows"] = sample
            else:
                metadata["sample_rows"] = sanitized[:500]
        else:
            metadata["keys"] = []
            metadata["sample_rows"] = sanitized[:200]

        return {
            "file_name": file_name,
            "source_type": "json",
            "sanitized_content": sanitized[:5000],
            "metadata": metadata,
        }
    except Exception as exc:
        raise ValueError(f"Failed to parse JSON: {exc}") from exc
