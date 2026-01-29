from fastapi import APIRouter, UploadFile

router = APIRouter()

@router.post("/")
async def upload_file(file: UploadFile):
    return {"filename": file.filename, "status": "uploaded"}
