"""PDF document parser (pdfplumber).

Extracts text from PDF files using pdfplumber.

Fix: Renamed ``page_count`` → ``pages`` to match the key contract expected
by FileAnalyzerAgent.  Also changed from a hard 10-page cap to a character-
budget approach (all pages, up to 20 000 chars) so long technical documents
aren't arbitrarily truncated at page 10.
"""

import io
from typing import Any, Dict

import pdfplumber

from core.validation import sanitize_text

# Maximum characters to extract across all pages
_MAX_CHARS: int = 20_000


def parse_pdf(file_name: str, file_content: bytes) -> Dict[str, Any]:
    """Extracts text content from a PDF file in-memory.

    Args:
        file_name: Original filename of the PDF.
        file_content: Raw binary stream of the PDF file.

    Returns:
        Dict[str, Any]: Structured unified document holding text blocks.

    Raises:
        ValueError: If the file is unreadable.
    """
    try:
        content_accumulator = []
        page_count = 0
        total_chars = 0

        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            page_count = len(pdf.pages)

            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    content_accumulator.append(text)
                    total_chars += len(text)
                # Stop extracting once we have enough context
                if total_chars >= _MAX_CHARS:
                    break

        full_text = "\n".join(content_accumulator)
        sanitized = sanitize_text(full_text)

        return {
            "file_name": file_name,
            "source_type": "pdf",
            "sanitized_content": sanitized[:8000],   # higher cap than original 5000
            "metadata": {
                "pages": page_count,              # matches analyzer L61 ("pages")
                "text_preview": sanitized[:1000],
            },
        }
    except Exception as exc:
        raise ValueError(f"Failed to parse PDF via pdfplumber: {exc}") from exc
