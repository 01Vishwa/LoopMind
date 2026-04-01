"""Document processing service.

Routes files to specific format parsers, retrieving in-memory bytes
and aggregating the output into a strictly normalized schema map matching
the UnifiedDocumentContext.
"""

from typing import List, Dict, Any
import os

from services.parsers.csv_parser import parse_csv
from services.parsers.txt_parser import parse_txt
from services.parsers.excel_parser import parse_excel
from services.parsers.pdf_parser import parse_pdf
from services.parsers.json_parser import parse_json
from services.parsers.md_parser import parse_md
from services.upload_service import get_file_content
from utils.helpers import sanitize_floats


def _get_extension(filename: str) -> str:
    """Safely extracts the lowercase file extension.

    Args:
        filename (str): The filename string.

    Returns:
        str: Lowercase extension, or empty string if none found.
    """
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ""


def process_documents(file_names: List[str]) -> Dict[str, Any]:
    """Routes files from memory cache to parsing logic.

    Args:
        file_names (List[str]): Filenames matching keys in the file cache.

    Returns:
        Dict[str, Any]: A unified memory map of normalized contextual documents,
        guaranteed to contain no nan/inf float values.
    """
    aggregated_context: Dict[str, Any] = {
        "files_processed": 0,
        "combined_extractions": {}
    }

    parser_map = {
        "csv": parse_csv,
        "txt": parse_txt,
        "xlsx": parse_excel,
        "pdf": parse_pdf,
        "json": parse_json,
        "md": parse_md,
    }

    for filename in file_names:
        ext = _get_extension(filename)

        parser_fn = parser_map.get(ext)
        file_content = get_file_content(filename)
        
        if file_content is None:
            aggregated_context["combined_extractions"][filename] = {
                "file_name": filename,
                "source_type": ext,
                "sanitized_content": "",
                "metadata": {"error": f"File '{filename}' missing from memory cache."}
            }
            continue

        if parser_fn:
            try:
                extraction = parser_fn(filename, file_content)
                aggregated_context["combined_extractions"][filename] = extraction
                aggregated_context["files_processed"] += 1
            except Exception as e:
                aggregated_context["combined_extractions"][filename] = {
                    "file_name": filename,
                    "source_type": ext,
                    "sanitized_content": "",
                    "metadata": {"error": f"Parse failure: {str(e)}"}
                }

    return sanitize_floats(aggregated_context)
