import hashlib
import re
import os
import io
import unicodedata
import zipfile
import uuid
import uuid6 # Assuming uuid6 is installed or we use uuid4
from pathlib import Path
from fastapi import UploadFile, HTTPException
from supabase._async.client import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from vera_db.repositories.file_repository import FileRepository
from vera_api.dependencies.auth import Principal
from vera_api.schemas.file import FileResponse

# --- Constants & Rules ---

SUPPORTED_EXTENSIONS = {
    ".csv", ".json", ".xlsx", ".xls", ".md", ".txt", ".pdf", ".sqlite", ".db", ".zip", ".parquet"
}

EXTENSION_TO_KIND = {
    ".csv": "csv",
    ".json": "json",
    ".xlsx": "xlsx",
    ".xls": "xlsx",
    ".parquet": "parquet",
    ".md": "markdown",
    ".txt": "txt",
    ".pdf": "pdf",
    ".sqlite": "sqlite",
    ".db": "sqlite",
    ".zip": "zip",
}

MAX_SIZES = {
    "csv": 100 * 1024 * 1024,
    "json": 50 * 1024 * 1024,
    "xlsx": 50 * 1024 * 1024,
    "parquet": 200 * 1024 * 1024,
    "markdown": 10 * 1024 * 1024,
    "txt": 10 * 1024 * 1024,
    "pdf": 50 * 1024 * 1024,
    "sqlite": 100 * 1024 * 1024,
    "zip": 100 * 1024 * 1024,
}

MAGIC_BYTES = {
    "xlsx": [b"PK\x03\x04"],  # ZIP-based
    "pdf": [b"%PDF"],
    "sqlite": [b"SQLite format 3\x00"],
    "zip": [b"PK\x03\x04"],
    "parquet": [b"PAR1"],
}

# --- Helpers ---

def sanitise_filename(name: str) -> str:
    # Strip any path prefix — only the filename
    name = name.split("/")[-1].split("\\")[-1]
    
    # Unicode normalise
    name = unicodedata.normalize("NFC", name)
    
    # Replace anything that isn't alphanumeric, dot, hyphen, or underscore
    name = re.sub(r"[^\w.\-]", "_", name)
    
    # Collapse underscores
    name = re.sub(r"_+", "_", name).strip("_")
    
    # Truncate preserving extension
    stem, ext = os.path.splitext(name)
    max_stem = 200 - len(ext)
    name = stem[:max_stem] + ext
    
    if not name or name == ext:
        raise HTTPException(status_code=422, detail="Filename is empty after sanitisation")
        
    return name

def validate_magic_bytes(data: bytes, kind: str) -> bool:
    expected = MAGIC_BYTES.get(kind)
    if expected is None:
        return True # text formats (csv, json, md, txt) have no magic bytes
    return any(data.startswith(magic) for magic in expected)

def check_zip_safety(data: bytes, max_ratio: float = 100.0, max_files: int = 500) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            if len(zf.infolist()) > max_files:
                return False
            total_uncompressed = sum(info.file_size for info in zf.infolist())
            if len(data) > 0 and total_uncompressed / len(data) > max_ratio:
                return False
        return True
    except zipfile.BadZipFile:
        return False

# --- Service Layer ---

async def upload_file(
    workspace_id: str, 
    file: UploadFile, 
    principal: Principal,
    supabase: AsyncClient,
    session: AsyncSession
) -> FileResponse:
    # STEP 1: Read file bytes
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=422, detail="File is empty")
        
    # STEP 2: Validate extension and size
    ext = Path(file.filename or "").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=422, detail=f"Unsupported file type: {ext}")
        
    kind = EXTENSION_TO_KIND.get(ext)
    if kind is None:
        raise HTTPException(status_code=422, detail=f"Unsupported file type: {ext}")
        
    max_size = MAX_SIZES.get(kind, 50 * 1024 * 1024)
    if len(file_bytes) > max_size:
        raise HTTPException(status_code=422, detail=f"File exceeds {max_size} byte limit for {kind}")
        
    # Validate magic bytes
    if not validate_magic_bytes(file_bytes, kind):
        raise HTTPException(status_code=422, detail=f"File extension is {ext} but content doesn't match.")
        
    # Validate ZIP safety
    if kind == "zip" and not check_zip_safety(file_bytes):
        raise HTTPException(status_code=422, detail="Invalid or unsafe ZIP file.")
        
    # STEP 3: Content hash
    content_sha256 = hashlib.sha256(file_bytes).hexdigest()
    
    # STEP 4: Check for duplicate
    file_repo = FileRepository(session=session)
    existing = await file_repo.find_by_sha(workspace_id=uuid.UUID(workspace_id), content_sha256=content_sha256)
    if existing:
        raise HTTPException(status_code=409, detail=f"This file already exists in the workspace as '{existing.filename}'")
        
    # STEP 5: Sanitise filename
    safe_name = sanitise_filename(file.filename or "uploaded_file")
    
    # UUID7 isn't strictly standard in python's `uuid` yet without packages, using uuid4 as fallback if unavailable.
    try:
        import uuid_utils
        file_id = uuid_utils.uuid7()
    except ImportError:
        file_id = uuid.uuid4()
        
    storage_path = f"{principal.tenant_id}/{workspace_id}/{file_id}_{safe_name}"
    
    # STEP 6: Upload to Supabase Storage
    try:
        storage = supabase.storage.from_("workspace-files")
        await storage.upload(
            path=storage_path, 
            file=file_bytes, 
            file_options={"content-type": file.content_type or "application/octet-stream"}
        )
    except Exception as e:
        # Check if the file already exists in storage for some reason
        raise HTTPException(status_code=502, detail="Upload failed. Try again.") from e
        
    # STEP 7: Insert database record
    try:
        file_record = await file_repo.create(
            id=file_id,
            workspace_id=uuid.UUID(workspace_id),
            tenant_id=principal.tenant_id,
            filename=safe_name,
            kind=kind,
            size_bytes=len(file_bytes),
            content_sha256=content_sha256,
            storage_path=storage_path,
            uploaded_by=principal.user_id,
        )
    except Exception as e:
        # Cleanup storage on DB failure
        await storage.remove([storage_path])
        raise e
        
    return FileResponse(
        id=str(file_record.id),
        filename=file_record.filename,
        kind=file_record.kind,
        size_bytes=file_record.size_bytes,
        content_sha256=file_record.content_sha256,
        has_description=False,
        created_at=str(file_record.created_at)
    )
