"""Upload controller.

Handles request-level orchestration for file upload:
validates metadata, delegates disk-write to upload_service,
and builds the structured UploadResponse.
"""

import os
from typing import List

from fastapi import UploadFile

from core.validation import validate_file_metadata
from models.schemas import UploadResponse, FileStatusItem
from services.upload_service import save_upload_file


async def handle_upload(files: List[UploadFile]) -> UploadResponse:
    """Orchestrates validation and persistence for a batch of uploaded files.

    Args:
        files (List[UploadFile]): Multipart file payloads from the request.

    Returns:
        UploadResponse: Lists of accepted and rejected FileStatusItems.
    """
    accepted: List[FileStatusItem] = []
    rejected: List[FileStatusItem] = []

    for file in files:
        if not file.filename:
            continue

        # Extension & MIME validation
        meta_issue = validate_file_metadata(file)
        if meta_issue:
            rejected.append(
                FileStatusItem(filename=file.filename, status="error", reason=meta_issue)
            )
            continue

        try:
            await save_upload_file(file)
            accepted.append(
                FileStatusItem(
                    filename=file.filename,
                    status="success",
                    reason="Uploaded and correctly sanitized."
                )
            )
        except ValueError as ve:
            rejected.append(
                FileStatusItem(filename=file.filename, status="error", reason=str(ve))
            )
        except Exception as e:
            rejected.append(
                FileStatusItem(
                    filename=file.filename,
                    status="error",
                    reason=f"Stream error: {str(e)}"
                )
            )

    return UploadResponse(accepted_files=accepted, rejected_files=rejected)
