from fastapi import APIRouter

router = APIRouter()

@router.post("/chat")
async def chat(query: str):
    return {"response": "This is a placeholder response"}
