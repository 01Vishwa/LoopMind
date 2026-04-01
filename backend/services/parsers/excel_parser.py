"""Excel file parser (XLSX).

Handles ingestion and basic parsing of Excel spreadsheet files into
standardized structured dictionaries using pandas and openpyxl.
"""

from typing import Dict, Any
import io
import pandas as pd
from core.validation import sanitize_text


def parse_excel(file_name: str, file_content: bytes) -> Dict[str, Any]:
    """Parses an XLSX file dynamically in-memory into a standard dictionary format.

    Args:
        file_name (str): The filename of the Excel document.
        file_content (bytes): Raw binary stream of the Excel sheet.

    Returns:
        Dict[str, Any]: Unified structured format holding sheet names, data,
        and sanitized raw extractions.

    Raises:
        ValueError: If file cannot be parsed or missing dependencies.
    """
    try:
        excel_data = pd.read_excel(io.BytesIO(file_content), sheet_name=None)
        sheets = list(excel_data.keys())

        # Combine all sheets into a single text block for the LLM context string
        raw_text_blocks = []
        for s_name, _df in excel_data.items():
            raw_text_blocks.append(f"--- Sheet: {s_name} ---\n{_df.to_string()}")

        full_text = "\n".join(raw_text_blocks)
        sanitized = sanitize_text(full_text)

        preview = {}
        if sheets:
            first_sheet_df = excel_data[sheets[0]]
            preview = first_sheet_df.head(5).to_dict(orient="records")

        return {
            "file_name": file_name,
            "source_type": "xlsx",
            "sanitized_content": sanitized[:5000],
            "metadata": {
                "sheet_count": len(sheets),
                "sheet_names": sheets,
                "preview_first_sheet": preview
            }
        }
    except Exception as e:
        raise ValueError(f"Failed to parse Excel file: {e}")
