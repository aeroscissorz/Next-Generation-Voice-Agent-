"""
Interceptor Services Package
==============================
Re-exports service modules for convenient importing in main.py.

Services:
  - backend_proxy       — HTTP proxy for Backend API communication (singleton)
  - voice_auth          — Voice authentication state management
"""

from .backend_proxy import backend_proxy, BackendProxy
from .voice_auth import (
    voice_auth_service,
    init_voice_auth_service,
    VoiceAuthService
)

__all__ = [
    # Backend Proxy — singleton instance + class
    "backend_proxy",
    "BackendProxy",
    
    # Voice Auth — singleton instance + factory + class
    "voice_auth_service",
    "init_voice_auth_service",
    "VoiceAuthService",
]
