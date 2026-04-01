"""Markdown (.md) parser.

Extracts and parses standard Markdown text files into unified context, mapping
the logic via the `markdown` module for extended functionality later.
"""

from typing import Dict, Any
import markdown
from core.validation import sanitize_text


def parse_md(file_name: str, file_content: bytes) -> Dict[str, Any]:
    """Ingests Markdown representations directly from memory buffers.

    Args:
        file_name (str): Original filename of the Markdown file.
        file_content (bytes): The raw Markdown text bytes.

    Returns:
        Dict[str, Any]: The extracted text formatted unified.

    Raises:
        ValueError: If the file cannot be read.
    """
    try:
        content = file_content.decode('utf-8')

        # Parse into HTML to strip raw structural blocks, then pass to sanitizer
        html_converted = markdown.markdown(content)
        sanitized = sanitize_text(html_converted)

        return {
            "file_name": file_name,
            "source_type": "md",
            "sanitized_content": sanitized[:5000],
            "metadata": {
                "char_count": len(sanitized),
                "content_preview": sanitized[:1000]
            }
        }
    except Exception as e:
        raise ValueError(f"Failed to parse Markdown: {e}")
