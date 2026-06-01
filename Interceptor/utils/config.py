"""
Configuration Module
====================
Centralized configuration management for the Interceptor service.
All settings are loaded from environment variables with sensible defaults.

Environment Variables:
  BACKEND_URL                  — Backend service URL (default: http://127.0.0.1:8000)
  INTERCEPTOR_TIMEOUT_SECONDS  — HTTP timeout for Backend requests (default: 60s)
  GOOGLE_API_KEY               — Google Gemini API key (required for agent)
  GOOGLE_GENAI_MODEL           — Gemini model name (default: gemini-1.5-flash)
  OPENAI_API_KEY               — OpenAI API key (required for voice + embeddings)
  OPENAI_REALTIME_MODEL        — OpenAI Realtime model (default: gpt-4o-realtime-preview-2025-06-03)
  SUPABASE_URL                 — Supabase project URL
  SUPABASE_SERVICE_KEY         — Supabase service role key (full access)

The Config class is instantiated as a singleton (`config`) at module level
and imported throughout the Interceptor.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)


class Config:
    """
    Application configuration — all values from environment variables.
    
    Used as a singleton via the `config` instance below.
    Access like: config.BACKEND_URL, config.OPENAI_API_KEY, etc.
    """
    
    # ─── Backend Connection ──────────────────────────────────────────
    # URL of the Backend FastAPI service (agent + Supabase tools)
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
    # HTTP timeout for Backend requests (covers full agent loop which can take 3-8s)
    TIMEOUT_SECONDS: float = float(os.getenv("INTERCEPTOR_TIMEOUT_SECONDS", "60"))
    
    # ─── Google Gemini AI ────────────────────────────────────────────
    # Used by the Backend agent for reasoning and tool calling
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    GOOGLE_GENAI_MODEL: str = os.getenv("GOOGLE_GENAI_MODEL", "gemini-1.5-flash")
    
    # ─── OpenAI ──────────────────────────────────────────────────────
    # Used for: voice (Realtime API), embeddings (knowledge search)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    # The Realtime model powers the voice WebRTC session
    OPENAI_REALTIME_MODEL: str = os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview-2025-06-03")
    
    # ─── Supabase ────────────────────────────────────────────────────
    # Used by the Interceptor's ToolExecutor for fast-path direct queries
    # and by VoiceAuthService for user validation
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_KEY: Optional[str] = os.getenv("SUPABASE_SERVICE_KEY")
    
    # ─── Voice System Instructions ───────────────────────────────────
    # Path to the markdown file containing the voice agent's personality and rules
    # Resolved relative to this file: Interceptor/utils/config.py → ../../eleven_labs_prompts/system.md
    VOICE_INSTRUCTIONS_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        "..", 
        "eleven_labs_prompts", 
        "system.md"
    )
    
    @classmethod
    def validate(cls) -> None:
        """Validate that required API keys are present. Raises ValueError if missing."""
        if not cls.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is required")
        
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for voice features")


# Singleton instance — imported as `from utils.config import config`
config = Config()
