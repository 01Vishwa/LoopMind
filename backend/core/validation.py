"""Stringent validation and sanitization filters.

Enforces explicit limits against Mime typing, byte limits, and unsafe text
to proactively harden the application.
"""

import re
from fastapi import UploadFile
from core.config import ALLOWED_MIME_TYPES, MAX_FILE_SIZE_BYTES

def validate_file_metadata(file: UploadFile) -> str:
    """Verifies file against extension extraction and declared MIME mapping.

    Args:
        file (UploadFile): Streamed file payload.

    Returns:
        str: Empty string if valid, otherwise returns string matching the precisely formatted
        rejection reason to populate the frontend Toast.
    """
    filename = file.filename or ""
    if '.' not in filename:
        return "Missing extension."
        
    ext = filename.rsplit('.', 1)[-1].lower()
    
    # Check extension validation explicitly
    if ext not in ALLOWED_MIME_TYPES:
        return f"Unsupported format: {ext}"
        
    # Check MIME alignment strictly
    expected_mime = ALLOWED_MIME_TYPES[ext]
    actual_mime = file.content_type
    
    if actual_mime != expected_mime:
        return f"MIME mismatch (Got {actual_mime}, expected {expected_mime})."
        
    # Valid
    return ""

def validate_file_size(file_size: int) -> str:
    """Validates the byte count against local configurations.

    Args:
        file_size (int): Analyzed memory overhead of an asset.

    Returns:
        str: Error payload string or empty if clean.
    """
    if file_size > MAX_FILE_SIZE_BYTES:
        mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        return f"File exceeds {mb}MB limit."
    return ""

def sanitize_text(raw_text: str) -> str:
    """Safely cleans out anomalous characters or execution blocks.

    Args:
        raw_text (str): Extracted memory text from parser.

    Returns:
        str: Output devoid of dangerous execution characters or script tags.
    """
    # Exterminate raw null bytes
    clean_text = raw_text.replace('\x00', '')
    
    # Strip basic HTML tags (simplistic regex for script/html block stripping)
    clean_html = re.compile('<.*?>')
    clean_text = re.sub(clean_html, '', clean_text)
    
    return clean_text.strip()
