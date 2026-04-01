"""CSV file parser.

Handles ingestion and basic parsing of comma-separated value files into
standardized structured dictionaries aligning with UnifiedDocumentContext.
"""

from typing import Dict, Any
import io
import pandas as pd
from core.validation import sanitize_text


def parse_csv(file_name: str, file_content: bytes) -> Dict[str, Any]:
    """Parses a CSV file dynamically in-memory into a UnifiedDocumentContext format.

    Args:
        file_name (str): The filename string.
        file_content (bytes): Raw binary stream of the CSV file.

    Returns:
        Dict[str, Any]: The parsed data structure unified map.

    Raises:
        ValueError: If file cannot be parsed.
    """
    try:
        df = pd.read_csv(io.BytesIO(file_content))

        # We extract raw string representation of the pandas memory map
        raw_text = df.to_string()
        sanitized = sanitize_text(raw_text)

        return {
            "file_name": file_name,
            "source_type": "csv",
            "sanitized_content": sanitized[:5000],
            "metadata": {
                "columns": list(df.columns),
                "rows": len(df),
                "sample_data": df.head(5).to_dict(orient="records")
            }
        }
    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {e}")
