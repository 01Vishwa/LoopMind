"""Pydantic schemas for unified API routing.

Enforces deep structural normalization across all analytical parsers, ensuring
that parsed output merges identically regardless of its source file origin.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class FileStatusItem(BaseModel):
    """Represents the status of an uploaded file."""
    filename: str
    status: str
    reason: str = ""

class UploadResponse(BaseModel):
    """Structured response for file uploads."""
    accepted_files: List[FileStatusItem]
    rejected_files: List[FileStatusItem]

class UnifiedDocumentContext(BaseModel):
    """Normalization standard for EVERY parsed document.
    
    All parsers must return this strict dictionary shape to unify
    downstream analytics effortlessly.
    """
    file_name: str
    source_type: str
    sanitized_content: str
    metadata: Dict[str, Any]

class QueryRequest(BaseModel):
    """Structured payload for incoming natural language queries."""
    query: str

class QueryInsights(BaseModel):
    """The narrative output of the query engine."""
    summary: str
    bullets: List[str]

class QueryResponse(BaseModel):
    """Output payload encapsulating structural insights and mock code."""
    insights: QueryInsights
    code: Dict[str, str]

class ErrorResponse(BaseModel):
    """Structured unified error response."""
    status: str
    message: str
