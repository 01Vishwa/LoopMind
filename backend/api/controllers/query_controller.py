"""Query controller.

Handles request-level orchestration for the /query endpoint:
sanitizes input and dispatches to the query service.
"""

from typing import Dict, Any

from core.validation import sanitize_text
from services.query_service import run_query


def handle_query(query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitizes query input and dispatches to the query service.

    Args:
        query (str): Raw natural language query from the user.
        context (Dict[str, Any]): In-memory document processing context.

    Returns:
        Dict[str, Any]: The QueryResponse-compatible result payload.
    """
    clean_query = sanitize_text(query)
    return run_query(clean_query, context)
