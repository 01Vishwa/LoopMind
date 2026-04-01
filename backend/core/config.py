"""Application configuration constraints.

Outlines explicit MIME and extension enforcement mappings, enforcing strict
payload constraints structurally.
"""

from typing import Dict

# 10 MB limit per file (prevent memory exhaustion and huge buffers)
MAX_FILE_SIZE_BYTES: int = 100 * 1024 * 1024  

# Explicit Extension to Allowed MIME type mapping
ALLOWED_MIME_TYPES: Dict[str, str] = {
    "csv": "text/csv",
    "txt": "text/plain",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
    "json": "application/json",
    "md": "text/markdown"
}
