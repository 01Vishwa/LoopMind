"""PDF Document parser (pdfplumber).

Extracts base text from PDF files utilizing pdfplumber.
"""

from typing import Dict, Any
import io
import pdfplumber
from core.validation import sanitize_text


def parse_pdf(file_name: str, file_content: bytes) -> Dict[str, Any]:
    """Extracts raw text content from PDF files dynamically in-memory.

    Args:
        file_name (str): Original filename of the PDF.
        file_content (bytes): Raw binary stream of the PDF file.

    Returns:
        Dict[str, Any]: Structured unified document holding text blocks.

    Raises:
        ValueError: If file is unreadable.
    """
    try:
        content_accumulator = []
        page_count = 0

        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            page_count = len(pdf.pages)

            # Extract text from the first up to 10 pages for immediate context
            for page_num in range(min(page_count, 10)):
                page = pdf.pages[page_num]
                text = page.extract_text()
                if text:
                    content_accumulator.append(text)

        full_text = "\n".join(content_accumulator)
        sanitized = sanitize_text(full_text)

        return {
            "file_name": file_name,
            "source_type": "pdf",
            "sanitized_content": sanitized[:5000],
            "metadata": {
                "page_count": page_count,
                "text_preview": sanitized[:1000]
            }
        }
    except Exception as e:
        raise ValueError(f"Failed to parse PDF via pdfplumber: {e}")
