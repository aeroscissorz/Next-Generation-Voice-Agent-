"""
Configuration and Environment Variables
Centralized configuration management for the Interceptor service
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)


class Config:
    """Application configuration"""
    
    # Backend Configuration
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
    TIMEOUT_SECONDS: float = float(os.getenv("INTERCEPTOR_TIMEOUT_SECONDS", "60"))
    
    # Google Gemini AI Configuration
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    GOOGLE_GENAI_MODEL: str = os.getenv("GOOGLE_GENAI_MODEL", "gemini-1.5-flash")
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_REALTIME_MODEL: str = os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview-2025-06-03")
    
    # Supabase Configuration
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_KEY: Optional[str] = os.getenv("SUPABASE_SERVICE_KEY")
    
    # Voice System Instructions Path
    VOICE_INSTRUCTIONS_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        "..", 
        "eleven_labs_prompts", 
        "system.md"
    )
    
    @classmethod
    def validate(cls) -> None:
        """Validate required configuration"""
        if not cls.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is required")
        
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for voice features")


# Create singleton instance
config = Config()
