"""TXT file parser.

Reads standard text files and returns raw blocks filtered through
the unified document context schemas and sanitizers.
"""

from typing import Dict, Any
from core.validation import sanitize_text


def parse_txt(file_name: str, file_content: bytes) -> Dict[str, Any]:
    """Parses a raw text buffer into a structured dictionary format.

    Args:
        file_name (str): Original filename structure.
        file_content (bytes): Content buffer to inject.

    Returns:
        Dict[str, Any]: Unified format holding character counts
        and a preview of the text.

    Raises:
        ValueError: If string decode format is misaligned.
    """
    try:
        content = file_content.decode('utf-8')

        sanitized = sanitize_text(content)

        return {
            "file_name": file_name,
            "source_type": "txt",
            "sanitized_content": sanitized[:5000],
            "metadata": {
                "char_count": len(sanitized),
                "preview": sanitized[:100] + "..." if len(sanitized) > 100 else sanitized
            }
        }
    except Exception as e:
        raise ValueError(f"Failed to parse TXT: {e}")
