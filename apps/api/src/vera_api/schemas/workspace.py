from pydantic import BaseModel, Field
from typing import Literal
from vera_api.schemas.file import FileResponse

class WorkspaceResponse(BaseModel):
    id: str
    name: str
    description: str | None
    file_count: int
    described_count: int
    status: Literal["empty", "partial", "ready"]
    created_at: str
    updated_at: str

class CreateWorkspaceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)

class UpdateWorkspaceRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)

class WorkspaceDetailResponse(WorkspaceResponse):
    files: list["FileResponse"]
