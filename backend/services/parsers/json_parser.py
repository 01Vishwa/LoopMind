"""JSON file parser.

Reads structured JSON payloads and returns validated root objects formatted
within the standardized UnifiedDocumentContext shape.
"""

import json
from typing import Dict, Any
from core.validation import sanitize_text


def parse_json(file_name: str, file_content: bytes) -> Dict[str, Any]:
    """Parses a JSON schema from memory directly into Unified format.

    Args:
        file_name (str): Path alias or filename.
        file_content (bytes): Raw JSON data schema.

    Returns:
        Dict[str, Any]: Unified map containing stringified json preview.

    Raises:
        ValueError: If the file is not valid JSON.
    """
    try:
        data = json.loads(file_content.decode('utf-8'))

        raw_string_data = json.dumps(data, indent=2)
        sanitized = sanitize_text(raw_string_data)

        return {
            "file_name": file_name,
            "source_type": "json",
            "sanitized_content": sanitized[:5000],
            "metadata": {
                "keys_present": list(data.keys()) if isinstance(data, dict) else ["root_list"],
                "data_preview": sanitized[:1000]
            }
        }
    except Exception as e:
        raise ValueError(f"Failed to parse JSON: {e}")
