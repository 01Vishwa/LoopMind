"""Application configuration — environment-driven settings.

Loads all credentials and tuning parameters from the .env file.
Swapped from Gemini to NVIDIA NIM; GEMINI_API_KEY is no longer used.
"""

import os
from typing import Dict, Set

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# ---------------------------------------------------------------------------
# File size limit
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 MB

# ---------------------------------------------------------------------------
# MIME type mappings — used by metadata validator
# ---------------------------------------------------------------------------

ALLOWED_MIME_TYPES: Dict[str, str] = {
    "csv": "text/csv",
    "txt": "text/plain",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
    "json": "application/json",
    "md": "text/markdown",
}

ANALYSIS_MODE_ALLOWED_FORMATS: Set[str] = {"csv", "xlsx", "json"}
IDP_ALLOWED_FORMATS: Set[str] = set(ALLOWED_MIME_TYPES.keys())

# ---------------------------------------------------------------------------
# Supabase credentials
# ---------------------------------------------------------------------------

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_PUBLISHABLE_KEY: str = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
SUPABASE_BUCKET: str = os.getenv("SUPABASE_BUCKET", "semantica-uploads")

# ---------------------------------------------------------------------------
# NVIDIA NIM configuration (replaces Gemini)
# ---------------------------------------------------------------------------

NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")

# Reasoning / planning / verification model (fast, large context)
NIM_MODEL_DEFAULT: str = os.getenv(
    "NIM_MODEL_DEFAULT", "meta/llama-3.1-70b-instruct"
)

# Code-generation model (stronger for producing runnable Python)
NIM_MODEL_CODER: str = os.getenv(
    "NIM_MODEL_CODER", "meta/llama-3.1-70b-instruct"
)

# ---------------------------------------------------------------------------
# DS-STAR Agent tuning
# ---------------------------------------------------------------------------

MAX_AGENT_ROUNDS: int = int(os.getenv("MAX_AGENT_ROUNDS", "10"))
EXECUTION_TIMEOUT_SECONDS: int = int(os.getenv("EXECUTION_TIMEOUT_SECONDS", "30"))
MAX_TOKENS_PER_RUN: int = int(os.getenv("MAX_TOKENS_PER_RUN", "50000"))
