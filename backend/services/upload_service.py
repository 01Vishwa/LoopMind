"""Upload service.

Encapsulates the file-write logic for in-memory processing,
performing chunked streaming reads with mid-stream size validation.
"""

import os
import logging
from typing import Tuple, Optional, Dict

from fastapi import UploadFile

from core.validation import validate_file_size

logger = logging.getLogger("uvicorn.info")


# Global in-memory cache to replace disk storage
_FILE_CACHE: Dict[str, bytes] = {}


async def save_upload_file(file: UploadFile) -> Tuple[int, str]:
    """Streams a single UploadFile into memory with mid-stream size checks.

    Args:
        file (UploadFile): The incoming multipart file payload.

    Returns:
        Tuple[int, str]: Bytes read and an in-memory status string.

    Raises:
        ValueError: If the file exceeds the configured size limit.
    """
    bytes_read = 0
    content_chunks = []

    while chunk := await file.read(1024 * 1024):  # 1 MB chunks
        bytes_read += len(chunk)

        size_issue = validate_file_size(bytes_read)
        if size_issue:
            raise ValueError(size_issue)

        content_chunks.append(chunk)

    # Store fully in memory
    _FILE_CACHE[file.filename] = b"".join(content_chunks)

    file_format = (
        file.filename.rsplit('.', 1)[-1].lower()
        if file.filename and '.' in file.filename
        else "unknown"
    )
    logger.info(
        "Uploaded File Metadata - Name: %s, Format: %s",
        file.filename,
        file_format,
    )

    return bytes_read, "Stored in memory"


def get_file_content(filename: str) -> Optional[bytes]:
    """Retrieves cached file bytes from the in-memory store."""
    return _FILE_CACHE.get(filename)


def clear_file_cache() -> None:
    """Empties the file representation dictionary."""
    _FILE_CACHE.clear()
