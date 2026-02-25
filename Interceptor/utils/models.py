"""
Pydantic Models
Request models for the Interceptor API
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    user_id: str = Field(..., description="User identifier (email)")
    name: Optional[str] = Field(None, description="User display name")


class NewSessionRequest(BaseModel):
    user_id: str = Field(..., description="User identifier (email)")
    name: Optional[str] = Field(None, description="User display name")


class ToolCallRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to call")
    arguments: Dict[str, Any] = Field(..., description="Tool arguments")
    user_id: str = Field(..., description="User identifier (email)")
    call_id: str = Field(..., description="Unique call identifier")
