from pydantic import BaseModel, Field
from typing import Literal, List, Optional
from datetime import datetime

class ModelAssignmentResponse(BaseModel):
    tier: str  # reasoning | utility | embedding
    provider_connection_id: Optional[str] = None
    model_id: Optional[str] = None
    provider_display_name: Optional[str] = None
    model_display_name: Optional[str] = None

class AgentDefaultsResponse(BaseModel):
    assignments: List[ModelAssignmentResponse]
    max_rounds: int
    max_cost_usd: float
    max_debug_attempts: int
    retriever_top_k: int

class UpdateAssignment(BaseModel):
    tier: Literal["reasoning", "utility", "embedding"]
    provider_connection_id: str
    model_id: str

class UpdateAgentDefaultsRequest(BaseModel):
    assignments: Optional[List[UpdateAssignment]] = None
    max_rounds: Optional[int] = Field(None, ge=1, le=20)
    max_cost_usd: Optional[float] = Field(None, ge=0.10, le=50.0)
    max_debug_attempts: Optional[int] = Field(None, ge=1, le=10)
    retriever_top_k: Optional[int] = Field(None, ge=1, le=50)
