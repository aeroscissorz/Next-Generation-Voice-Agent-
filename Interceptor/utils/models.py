"""
Pydantic Request Models
=======================
Request models for the Interceptor API endpoints.
These define the expected JSON body structure for each POST endpoint.

Models:
  - ChatRequest       — Used by /chat and /chat/stream (message + user_id + optional name)
  - NewSessionRequest — Used by /new-session (user_id + optional name)
  - ToolCallRequest   — Used by /voice/tool-call (tool_name + arguments + user_id + call_id)
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    Request body for /chat and /chat/stream endpoints.
    
    Fields:
      - message: The user's message text (may be injected with context by the Interceptor)
      - user_id: User identifier (email from Supabase Auth)
      - name: Optional display name for personalized responses
    """
    message: str = Field(..., description="User message")
    user_id: str = Field(..., description="User identifier (email)")
    name: Optional[str] = Field(None, description="User display name")


class NewSessionRequest(BaseModel):
    """
    Request body for /new-session endpoint.
    Creates or resets a conversation session for the user.
    """
    user_id: str = Field(..., description="User identifier (email)")
    name: Optional[str] = Field(None, description="User display name")


class ToolCallRequest(BaseModel):
    """
    Request body for /voice/tool-call endpoint.
    
    Sent by the Frontend when the OpenAI Realtime model calls a tool
    during a voice session. The Frontend intercepts the tool call from
    the WebRTC connection and POSTs it here.
    
    Fields:
      - tool_name: "validate_user" or "forward_to_backend"
      - arguments: Tool-specific arguments (e.g., {"user_id": "42"} or {"message": "show my invoices"})
      - user_id: The Frontend user's email (used for auth state tracking)
      - call_id: Unique identifier for this tool call (returned in the response
                 so the Frontend can match it back to the Realtime session)
    """
    tool_name: str = Field(..., description="Name of the tool to call")
    arguments: Dict[str, Any] = Field(..., description="Tool arguments")
    user_id: str = Field(..., description="User identifier (email)")
    call_id: str = Field(..., description="Unique call identifier")
