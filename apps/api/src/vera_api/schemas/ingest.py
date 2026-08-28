from pydantic import BaseModel
from typing import Literal

class IngestResponse(BaseModel):
    total: int
    pending: int

class IngestStatusResponse(BaseModel):
    total: int
    analyzed: int
    pending: int
    failed: int
    current_file: str | None
    status: Literal["idle", "running", "complete"]
