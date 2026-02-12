"""
Pydantic Models
Request and response models for the Interceptor API
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., description="User message")
    user_id: str = Field(..., description="User identifier (email)")
    name: Optional[str] = Field(None, description="User display name")


class NewSessionRequest(BaseModel):
    """Request model for new session endpoint"""
    user_id: str = Field(..., description="User identifier (email)")
    name: Optional[str] = Field(None, description="User display name")


class ToolCallRequest(BaseModel):
    """Request model for voice tool call endpoint"""
    tool_name: str = Field(..., description="Name of the tool to call")
    arguments: Dict[str, Any] = Field(..., description="Tool arguments")
    user_id: str = Field(..., description="User identifier (email)")
    call_id: str = Field(..., description="Unique call identifier")


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    reply: str = Field(..., description="Formatted response")
    raw_reply: Optional[str] = Field(None, description="Raw response from backend")
    user_name: Optional[str] = Field(None, description="User display name")
    channel: Optional[str] = Field(None, description="Channel type")
    formatted: Optional[bool] = Field(None, description="Whether response was formatted")


class VoiceTokenResponse(BaseModel):
    """Response model for voice token endpoint"""
    ephemeral_token: str = Field(..., description="OpenAI ephemeral token")
    model: str = Field(..., description="OpenAI model name")
    voice: str = Field(..., description="Voice identifier")
    expires_at: Optional[str] = Field(None, description="Token expiration time")


class ToolCallResponse(BaseModel):
    """Response model for tool call endpoint"""
    call_id: str = Field(..., description="Unique call identifier")
    result: str = Field(..., description="Tool execution result (JSON string)")


class HealthResponse(BaseModel):
    """Response model for health check endpoint"""
    status: str = Field(..., description="Service status")
    service: Optional[str] = Field(None, description="Service name")
    backend_url: Optional[str] = Field(None, description="Backend URL")
