"""
Interceptor Service - Refactored
Channel-specific middleware for message processing and formatting
"""

import json
import logging
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

# Import from our organized modules
from utils import (
    config,
    inject_chat_context,
    inject_voice_context,
    format_reply_for_chat,
    format_reply_for_voice,
    normalize_to_text,
    load_system_instructions,
    extract_user_id_from_spoken,
    # Models
    ChatRequest,
    NewSessionRequest,
    ToolCallRequest,
    # Tools
    VOICE_TOOLS,
)
from services import (
    backend_proxy,
    init_voice_auth_service,
)

# Initialize FastAPI app
app = FastAPI(title="Chat Interceptor")
logger = logging.getLogger("interceptor")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Initialize Supabase
supabase: Optional[Client] = None
if config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY:
    try:
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        logger.info("✓ Supabase initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase: {e}")

# Initialize voice auth service
_voice_auth = init_voice_auth_service(supabase)

# Load voice system instructions
VOICE_SYSTEM_INSTRUCTIONS = load_system_instructions(config.VOICE_INSTRUCTIONS_PATH)


# ---------------------------------------------------------------------------
# Chat Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def health():
    """Health check - proxies to Backend"""
    return await backend_proxy.health_check()


@app.options("/chat")
async def chat_options():
    """CORS preflight for chat endpoint"""
    return {"status": "ok"}


@app.post("/new-session")
async def new_session(req: NewSessionRequest):
    """Create new session - proxies to Backend"""
    return await backend_proxy.new_session(req.user_id, req.name)


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Process chat message with context injection and formatting.
    
    Flow:
    1. Inject chat-specific context
    2. Forward to Backend
    3. Format response for chat (markdown)
    4. Return formatted response
    """
    # Inject chat-specific context
    enhanced_message = inject_chat_context(req.message, req.user_id)
    
    logger.info(f"Chat request: user_id={req.user_id}, message_len={len(req.message)}")
    
    # Forward to Backend with enhanced message
    backend_response = await backend_proxy.chat(
        message=enhanced_message,
        user_id=req.user_id,
        name=req.name
    )
    
    logger.info(f"Backend response type: {type(backend_response).__name__}")
    
    # Normalize response
    if not isinstance(backend_response, dict):
        backend_response = {"reply": str(backend_response)}
    
    # Extract reply
    raw_reply = normalize_to_text(backend_response.get("reply", ""))
    if not raw_reply:
        raw_reply = normalize_to_text(backend_response.get("detail", ""))
    if not raw_reply:
        raw_reply = "I'm here to help! How can I assist you today?"
    
    # Format for chat
    formatted_reply = format_reply_for_chat(raw_reply)
    formatted_reply = normalize_to_text(formatted_reply) or raw_reply
    
    logger.info(f"Response lengths: raw={len(raw_reply)}, formatted={len(formatted_reply)}")
    logger.info(f"Formatted preview: {formatted_reply[:200].replace(chr(10), ' ')}")
    
    # Return formatted response
    backend_response["raw_reply"] = raw_reply
    backend_response["reply"] = formatted_reply
    return backend_response


# ---------------------------------------------------------------------------
# Voice Endpoints
# ---------------------------------------------------------------------------

@app.get("/voice/token")
async def get_voice_token(user_id: str = Query(..., description="User identifier")):
    """
    Generate ephemeral token for OpenAI Realtime API.
    
    Args:
        user_id: User identifier (email)
    
    Returns:
        Ephemeral token and session configuration
    """
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/realtime/sessions",
                headers={
                    "Authorization": f"Bearer {config.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config.OPENAI_REALTIME_MODEL,
                    "modalities": ["text", "audio"],
                    "voice": "alloy",
                    "instructions": VOICE_SYSTEM_INSTRUCTIONS,
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "tools": VOICE_TOOLS,
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 1000,
                    },
                },
            )

        if response.status_code >= 400:
            error_body = response.text
            logger.error(f"OpenAI session creation failed: {response.status_code} {error_body}")
            raise HTTPException(
                status_code=502,
                detail=f"OpenAI API error ({response.status_code}): {error_body[:300]}",
            )

        session_data = response.json()

        # Extract ephemeral token
        client_secret = session_data.get("client_secret", {})
        ephemeral_token = client_secret.get("value", "") if isinstance(client_secret, dict) else ""

        if not ephemeral_token:
            logger.error(f"No ephemeral token in response: {json.dumps(session_data)[:500]}")
            raise HTTPException(status_code=502, detail="No ephemeral token returned by OpenAI")

        # Reset auth state for new session
        _voice_auth.reset_auth(user_id)

        return {
            "ephemeral_token": ephemeral_token,
            "model": config.OPENAI_REALTIME_MODEL,
            "voice": "alloy",
            "expires_at": client_secret.get("expires_at"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create ephemeral token")
        raise HTTPException(status_code=500, detail=f"Failed to create voice session: {exc}") from exc


@app.post("/voice/tool-call")
async def handle_voice_tool_call(req: ToolCallRequest):
    """
    Handle tool calls from OpenAI Realtime session.
    
    Tools:
    - validate_user: Validate user ID against database
    - forward_to_backend: Forward query to Backend
    """
    logger.info(f"Voice tool call: name={req.tool_name}, user_id={req.user_id}, call_id={req.call_id}")

    if req.tool_name == "validate_user":
        return await _handle_validate_user(req)
    elif req.tool_name == "forward_to_backend":
        return await _handle_forward_to_backend(req)
    else:
        return {
            "call_id": req.call_id,
            "result": json.dumps({"error": f"Unknown tool: {req.tool_name}"})
        }


# ---------------------------------------------------------------------------
# Tool Call Request functions
# ---------------------------------------------------------------------------

async def _handle_validate_user(req: ToolCallRequest) -> dict:
    """
    Validate user identity against Supabase database.
    
    Args:
        req: Tool call request with user_id argument
    
    Returns:
        Validation result
    """
    raw_user_id = req.arguments.get("user_id", "").strip()
    spoken_user_id = extract_user_id_from_spoken(raw_user_id)
    
    logger.info(f"Validating user: raw='{raw_user_id}', normalized='{spoken_user_id}'")

    if not spoken_user_id:
        return {
            "call_id": req.call_id,
            "result": json.dumps({
                "authenticated": False,
                "reason": "No user ID provided"
            }),
        }

    # Validate against database
    authenticated, customer_id, message = await _voice_auth.validate_user_id(spoken_user_id)
    
    if authenticated and customer_id:
        # Mark user as authenticated
        _voice_auth.set_authenticated(req.user_id, customer_id)
        
        return {
            "call_id": req.call_id,
            "result": json.dumps({
                "authenticated": True,
                "customer_id": customer_id,
                "message": message
            }),
        }
    else:
        return {
            "call_id": req.call_id,
            "result": json.dumps({
                "authenticated": False,
                "reason": "User ID not found",
                "message": message
            }),
        }


async def _handle_forward_to_backend(req: ToolCallRequest) -> dict:
    """
    Forward user query to Backend with voice context injection.
    
    Args:
        req: Tool call request with message argument
    
    Returns:
        Backend response formatted for voice
    """
    user_message = req.arguments.get("message", "")
    if not user_message:
        return {
            "call_id": req.call_id,
            "result": json.dumps({"error": "No message provided"}),
        }

    # Check authentication
    if not _voice_auth.is_authenticated(req.user_id):
        return {
            "call_id": req.call_id,
            "result": json.dumps({
                "error": "User not authenticated. Please ask for their User ID first and call validate_user."
            }),
        }

    # Get validated customer ID
    customer_id = _voice_auth.get_customer_id(req.user_id) or req.user_id
    
    # Inject voice-specific context
    enhanced_message = inject_voice_context(user_message, customer_id, is_authenticated=True)

    try:
        # Forward to Backend
        backend_response = await backend_proxy.chat(
            message=enhanced_message,
            user_id=customer_id
        )

        # Extract reply
        raw_reply = normalize_to_text(
            backend_response.get("reply", "") if isinstance(backend_response, dict)
            else str(backend_response)
        )
        if not raw_reply:
            raw_reply = "I couldn't get that information right now."

        # Format for voice
        voice_reply = format_reply_for_voice(raw_reply)
        voice_reply = normalize_to_text(voice_reply) or raw_reply

        return {
            "call_id": req.call_id,
            "result": json.dumps({"response": voice_reply}),
        }
    except HTTPException:
        return {
            "call_id": req.call_id,
            "result": json.dumps({
                "error": "Sorry, I'm having trouble reaching the support system right now."
            }),
        }
    except Exception as exc:
        logger.exception("forward_to_backend failed")
        return {
            "call_id": req.call_id,
            "result": json.dumps({"error": f"Backend error: {exc}"}),
        }
