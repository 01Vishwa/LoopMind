from pydantic import BaseModel

class FileResponse(BaseModel):
    id: str
    filename: str
    kind: str
    size_bytes: int
    content_sha256: str
    has_description: bool
    created_at: str

class FileDetailResponse(FileResponse):
    storage_path: str # internal only

class SchemaFieldResponse(BaseModel):
    name: str
    dtype: str
    samples: list[str]
    warning: str | None

class FileDescriptionResponse(BaseModel):
    file_id: str
    summary_text: str
    schema_fields: list[SchemaFieldResponse]
    row_count: int | None
    sheet_names: list[str] | None
    sample_rows: list[dict] | None
    analyzer_script: str | None
    analyzer_model: str
    prompt_version: str
    created_at: str
