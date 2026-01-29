from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import shutil
import os
import uuid

# Internal Services
from app.agents.supervisor import SupervisorAgent
from app.rl_engine.bandit import ContextualBandit

app = FastAPI(title="AutoGraph Brain")

# Initialize Agents
supervisor = SupervisorAgent()
rl_bandit = ContextualBandit()

DATA_DIR = os.environ.get("DATA_DIR", "./data")
os.makedirs(DATA_DIR, exist_ok=True)

# --- Models ---
class AnalyzeRequest(BaseModel):
    query: str
    file_id: str

class FeedbackRequest(BaseModel):
    action: str
    reward: float
    context: Dict[str, Any]

# --- Endpoints ---

@app.post("/api/v1/upload")
async def upload_file(file: UploadFile = File(...)):
    file_id = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(DATA_DIR, file_id)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"file_id": file_id, "filename": file.filename}

@app.post("/api/v1/analysis/chat")
async def analyze(request: AnalyzeRequest):
    try:
        result = await supervisor.process_request(request.query, request.file_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/feedback")
async def feedback(request: FeedbackRequest):
    # Update RL Model
    rl_bandit.update(request.context, request.action, request.reward)
    return {"status": "success", "new_weights_sample": rl_bandit.weights.tolist()}

@app.get("/")
def health_check():
    return {"status": "AutoGraph Brain is outputting signals."}
