"""Process controller.

Handles request-level orchestration for the /process endpoint:
resolves file paths and delegates to the process service.
"""

from typing import List, Dict, Any

from services.process_service import process_documents
from services.upload_service import clear_file_cache


def handle_process(
    filenames: List[str],
    session_id: str = "__anon__",
) -> Dict[str, Any]:
    """Resolves upload references and triggers document processing in-memory.

    Args:
        filenames: Filenames of previously uploaded documents.
        session_id: Session identifier used to look up files from the
            session-scoped cache.

    Returns:
        Dict[str, Any]: Structured process result with status and details.
    """
    context = process_documents(filenames, session_id=session_id)

    return {
        "status": "success",
        "message": f"Successfully processed {context.get('files_processed')} files.",
        "details": context,
    }


def handle_clear(session_id: str = "__anon__") -> Dict[str, Any]:
    """Triggers the clearing of the session's byte cache.

    Args:
        session_id: Session to wipe.  Only that session's files are removed.

    Returns:
        Dict[str, Any]: Response status.
    """
    clear_file_cache(session_id=session_id)
    return {"status": "success", "message": "In-memory cache completely wiped."}
