"""
Interceptor Utilities Package
==============================
Re-exports all utility modules for convenient importing in main.py.

Modules:
  - config             — Environment variables and app configuration
  - context_injection   — Channel-specific message context injection
  - formatters          — Response formatting for chat and voice
  - helpers             — normalize_to_text, load_system_instructions, extract_user_id_from_spoken
  - models              — Pydantic request models (ChatRequest, NewSessionRequest, ToolCallRequest)
  - tools               — OpenAI Realtime API voice tool definitions
  - intent_detector     — Fast-path intent matching (imported separately in main.py)
"""

from .config import config, Config
from .context_injection import inject_chat_context, inject_voice_context
from .formatters import format_reply_for_chat, format_reply_for_voice
from .helpers import (
    normalize_to_text,
    load_system_instructions,
    extract_user_id_from_spoken,
    USER_ID_MIN_LENGTH,
    USER_ID_MAX_LENGTH,
)
from .models import ChatRequest, NewSessionRequest, ToolCallRequest
from .tools import VOICE_TOOLS
