"""Process controller.

Handles request-level orchestration for the /process endpoint:
resolves file paths and delegates to the process service.
"""

from typing import List, Dict, Any

from services.process_service import process_documents
from services.upload_service import clear_file_cache


def handle_process(filenames: List[str]) -> Dict[str, Any]:
    """Resolves upload references and triggers document processing entirely in-memory.

    Args:
        filenames (List[str]): Filenames of previously uploaded documents.

    Returns:
        Dict[str, Any]: Structured process result with status and details.
    """
    context = process_documents(filenames)

    return {
        "status": "success",
        "message": f"Successfully processed {context.get('files_processed')} files.",
        "details": context
    }


def handle_clear() -> Dict[str, Any]:
    """Triggers the clearing of the byte caches.
    
    Returns:
        Dict[str, Any]: Response status.
    """
    clear_file_cache()
    return {"status": "success", "message": "In-memory cache completely wiped."}
