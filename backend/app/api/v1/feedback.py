from fastapi import APIRouter

router = APIRouter()

@router.post("/")
async def submit_feedback(reward: float):
    return {"status": "feedback_received", "reward": reward}
