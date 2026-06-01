"""
Backend Proxy Service
=====================
Handles all HTTP communication between the Interceptor and the Backend service.
Uses httpx.AsyncClient for non-blocking requests with connection pooling.

This is a singleton service — one instance shared across all requests.
The Backend URL and timeout are configured via environment variables
(see utils/config.py).

Endpoints proxied:
  GET  /           → Backend health check
  POST /new-session → Create/reset conversation session
  POST /chat       → Synchronous chat (full agent loop)
  POST /chat/stream → SSE streaming chat
  POST /chat/fast  → Fast-path (single LLM call with pre-fetched data)
  POST /prefetch   → Warm Backend caches for a user
"""

import httpx
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from fastapi import HTTPException

from utils.config import config

logger = logging.getLogger("backend_proxy")


class BackendProxy:
    """
    Async HTTP proxy for Backend API communication.
    
    Uses a persistent httpx.AsyncClient for connection reuse (avoids
    TCP handshake overhead on every request). The client is configured
    with the timeout from config.TIMEOUT_SECONDS (default 60s).
    """
    
    def __init__(self):
        self.backend_url = config.BACKEND_URL
        self.timeout = config.TIMEOUT_SECONDS
        # Persistent async HTTP client — reuses connections across requests
        self._client = httpx.AsyncClient(timeout=self.timeout)
    
    async def request(
        self, 
        method: str, 
        path: str, 
        payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generic request method for Backend API calls.
        
        Handles error cases:
          - httpx.HTTPError → 502 Backend unavailable
          - 4xx/5xx from Backend → forwarded as-is
          - Invalid JSON → 502 with descriptive error
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., "/chat", "/new-session")
            payload: JSON body for POST requests
        
        Returns:
            Parsed JSON response from Backend
        """
        target_url = f"{self.backend_url}{path}"
        
        logger.info(f"Backend request: {method} {target_url}")
        
        try:
            response = await self._client.request(method, target_url, json=payload)
        except httpx.HTTPError as exc:
            logger.error(f"Backend unavailable: {exc}")
            raise HTTPException(
                status_code=502, 
                detail=f"Backend unavailable: {exc}"
            ) from exc

        if response.status_code >= 400:
            logger.error(f"Backend error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=response.status_code, 
                detail=response.text
            )

        try:
            return response.json()
        except ValueError as exc:
            logger.error(f"Invalid JSON from backend: {response.text}")
            raise HTTPException(
                status_code=502, 
                detail="Invalid JSON from backend"
            ) from exc
    
    async def chat(
        self, 
        message: str, 
        user_id: str, 
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a chat message to Backend /chat endpoint.
        The message should already have context injected by the Interceptor.
        """
        payload = {
            "message": message,
            "user_id": user_id,
        }
        if name:
            payload["name"] = name
        
        return await self.request("POST", "/chat", payload)
    
    async def new_session(
        self, 
        user_id: str, 
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new session in Backend.
        Resets conversation history for the user.
        """
        payload = {
            "user_id": user_id,
        }
        if name:
            payload["name"] = name
        
        return await self.request("POST", "/new-session", payload)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Backend health via GET /."""
        return await self.request("GET", "/")
    
    async def chat_stream(
        self,
        message: str,
        user_id: str,
        name: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response from Backend /chat/stream via SSE.
        
        Uses httpx streaming to forward SSE events line-by-line.
        Each line starting with "data: " is an SSE event containing
        either a status update or the final response.
        """
        target_url = f"{self.backend_url}/chat/stream"
        payload = {
            "message": message,
            "user_id": user_id,
        }
        if name:
            payload["name"] = name
        
        logger.info(f"Backend stream request: POST {target_url}")
        
        try:
            async with self._client.stream("POST", target_url, json=payload) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        yield line + "\n\n"
        except httpx.HTTPError as exc:
            logger.error(f"Backend stream error: {exc}")
            yield f"data: {{\"error\": \"{exc}\", \"done\": true}}\n\n"

    async def chat_fast(
        self,
        message: str,
        user_id: str,
        tool_data: dict,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fast-path: send pre-fetched tool data to Backend /chat/fast.
        
        The Interceptor's intent detector + ToolExecutor already fetched the
        relevant data from Supabase. This endpoint just needs Gemini to
        format it into a human-readable response (single LLM call, no agent loop).
        """
        payload = {
            "message": message,
            "user_id": user_id,
            "tool_data": tool_data,
        }
        if name:
            payload["name"] = name

        return await self.request("POST", "/chat/fast", payload)


# Singleton instance used by main.py and other modules
backend_proxy = BackendProxy()
