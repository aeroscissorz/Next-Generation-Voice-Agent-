"""
Backend Proxy Service
Handles all communication with the Backend service
"""

import httpx
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from fastapi import HTTPException

from utils.config import config

logger = logging.getLogger("backend_proxy")


class BackendProxy:
    """Proxy for Backend API communication"""
    
    def __init__(self):
        self.backend_url = config.BACKEND_URL
        self.timeout = config.TIMEOUT_SECONDS
        self._client = httpx.AsyncClient(timeout=self.timeout)
    
    async def request(
        self, 
        method: str, 
        path: str, 
        payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the Backend API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., "/chat")
            payload: Request payload (for POST requests)
        
        Returns:
            JSON response from Backend
        
        Raises:
            HTTPException: If Backend is unavailable or returns error
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
        Send a chat message to Backend.
        
        Args:
            message: User message (may include context injection)
            user_id: User identifier
            name: User name (optional)
        
        Returns:
            Backend response
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
        
        Args:
            user_id: User identifier
            name: User name (optional)
        
        Returns:
            Backend response
        """
        payload = {
            "user_id": user_id,
        }
        
        if name:
            payload["name"] = name
        
        return await self.request("POST", "/new-session", payload)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check Backend health.
        
        Returns:
            Backend health status
        """
        return await self.request("GET", "/")
    
    async def chat_stream(
        self,
        message: str,
        user_id: str,
        name: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response from Backend.
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
        Fast-path: send pre-fetched tool data to backend for single LLM formatting.
        """
        payload = {
            "message": message,
            "user_id": user_id,
            "tool_data": tool_data,
        }
        if name:
            payload["name"] = name

        return await self.request("POST", "/chat/fast", payload)


# Create singleton instance
backend_proxy = BackendProxy()
