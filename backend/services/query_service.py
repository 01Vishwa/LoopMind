"""Query engine service.

Consumes the aggregated context from the process step and generates
answering insights and analytical code structures to satisfy UI.
Moved from query/query_engine.py.
"""

from typing import Dict, Any


def run_query(query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Generates mock insights and code based on natural language query.

    Since there is no live LLM backing this endpoint, this service inspects
    the passed structured context and generates a deterministic formatted
    mock response adhering to the frontend schemas.

    Args:
        query (str): The natural language query from the user.
        context (Dict[str, Any]): The aggregated results from parsing.

    Returns:
        Dict[str, Any]: Match dictionary comprising `insights` and `code`.
    """
    files_used = context.get('files_processed', 0)
    docs_preview = list(context.get('combined_extractions', {}).keys())

    mocked_insights = {
        "summary": (
            f"Based on your request '{query}', we processed {files_used} "
            f"associated files: {', '.join(docs_preview)}."
        ),
        "bullets": [
            f"Input Query Tokens: ~{len(query.split()) * 2}",
            "Generated Output Tokens: ~45",
            "All formatting validations passed locally."
        ]
    }

    mocked_code = {
        "Python": (
            f"# Auto-generated analysis script for query:\n"
            f"# '{query}'\n\n"
            f"import pandas as pd\n\n"
            f"print('Loaded {files_used} semantic files.')\n"
            f"print('Execution completed perfectly.')"
        )
    }

    return {
        "insights": mocked_insights,
        "code": mocked_code
    }
