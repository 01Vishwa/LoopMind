from pydantic import BaseModel, Field
from typing import Literal, List, Optional
from datetime import datetime

class TestProviderKeyRequest(BaseModel):
    kind: Literal["openrouter", "nvidia_nim"]
    api_key: str = Field(min_length=10)
    base_url: Optional[str] = None

class TestKeyResponse(BaseModel):
    status: Literal["valid", "invalid_format", "invalid_key", "provider_unreachable"]
    model_count: Optional[int] = None

class ModelInfoResponse(BaseModel):
    model_id: str
    display_name: str
    context_window: Optional[int] = None
    input_price_per_m: Optional[float] = None
    output_price_per_m: Optional[float] = None
    supports_json_mode: bool
    supports_vision: bool

class ModelsResponse(BaseModel):
    models: List[ModelInfoResponse]

class RegisterProviderRequest(BaseModel):
    kind: Literal["openrouter", "nvidia_nim"]
    display_name: str = Field(min_length=1, max_length=100)

class ProviderConnectionResponse(BaseModel):
    id: str
    kind: str
    display_name: str
    created_at: datetime
