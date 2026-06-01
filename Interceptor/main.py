"""
Interceptor Service (Middleware Layer)
======================================
Channel-specific middleware that sits between the Frontend and the Backend.
Handles context injection, response formatting, voice authentication,
fast-path optimization, and the OpenAI Realtime API integration for voice.

Architecture:
  Frontend (React) ──► Interceptor (this file) ──► Backend (FastAPI + Gemini Agent)
       │                      │
       │                      ├─ Chat endpoints: inject context → proxy to Backend → format response
       │                      ├─ Voice endpoints: OpenAI Realtime API token + tool call handling
       │                      └─ Fast-path: intent detection → direct Supabase query → Backend /chat/fast
       │
       └─ Voice (WebRTC) ──► OpenAI Realtime API ──► tool calls ──► Interceptor /voice/tool-call

Key Responsibilities:
  1. Context Injection: Prepends [USER_ID], [CONTEXT: Voice/Chat], and formatting
     instructions to every message before forwarding to the Backend.
  2. Response Formatting: Cleans up Backend responses for the appropriate channel
     (markdown for chat, plain speech for voice).
  3. Voice Authentication: Manages auth state for voice callers (validate_user tool).
  4. Fast-Path Optimization: Detects simple intents (e.g., "show my invoices"),
     fetches data directly from Supabase, and sends to Backend /chat/fast for
     a single LLM formatting call (skips the full agent loop).
  5. Cache Warming: Prefetches user data on login/new-session for faster responses.

Endpoints:
  Chat:
    GET  /              — Health check (proxied to Backend)
    POST /new-session   — Create/reset session + warm caches
    POST /chat          — Synchronous chat (context inject → Backend → format)
    POST /chat/stream   — SSE streaming chat (proxied with context injection)

  Voice:
    GET  /voice/token       — Get OpenAI Realtime API ephemeral token
    POST /voice/tool-call   — Handle tool calls from OpenAI Realtime (validate_user, forward_to_backend)
"""

import asyncio
import json
import logging
import time
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

# ─── Logging Setup ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)

# ─── Internal Module Imports ─────────────────────────────────────────────────
from utils import (
    config,                          # Centralized env config (URLs, API keys, timeouts)
    inject_chat_context,             # Prepends chat-specific context to messages
    inject_voice_context,            # Prepends voice-specific context to messages
    format_reply_for_chat,           # Cleans up markdown for chat UI
    format_reply_for_voice,          # Strips markdown, limits to 1-3 sentences for voice
    normalize_to_text,               # Converts any value (dict, list, None) to string
    load_system_instructions,        # Loads voice system prompt from markdown file
    extract_user_id_from_spoken,     # Extracts digits from spoken user ID ("forty two" → "42")
    ChatRequest,                     # Pydantic model for chat requests
    NewSessionRequest,               # Pydantic model for new session requests
    ToolCallRequest,                 # Pydantic model for voice tool call requests
    VOICE_TOOLS,                     # OpenAI Realtime API tool definitions
)
from utils.intent_detector import detect_intent  # Fast-path intent matching
from services import backend_proxy, init_voice_auth_service  # Backend proxy + voice auth

# ─── App Setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="Chat Interceptor")
logger = logging.getLogger("interceptor")

# CORS: Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ─── Supabase Client (for fast-path direct queries) ─────────────────────────
# The Interceptor has its own Supabase client for the fast-path ToolExecutor.
# This allows it to fetch data directly without going through the Backend.
supabase: Optional[Client] = None
if config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY:
    try:
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        logger.info("✓ Supabase initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase: {e}")

# ─── Voice Auth Service ──────────────────────────────────────────────────────
# Manages authentication state for voice callers.
# Voice users must provide their User ID at the start of each call.
# The service validates against the 'users_voice' table in Supabase.
_voice_auth = init_voice_auth_service(supabase)

# Load the voice system instructions (personality, tone, flow rules)
# from eleven_labs_prompts/system.md — sent to OpenAI Realtime API
VOICE_SYSTEM_INSTRUCTIONS = load_system_instructions(config.VOICE_INSTRUCTIONS_PATH)


# ═══════════════════════════════════════════════════════════════════════════════
# CHAT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/")
async def health():
    """Health check — proxied to Backend to verify the full stack is up."""
    return await backend_proxy.health_check()


@app.options("/chat")
async def chat_options():
    """CORS preflight handler."""
    return {"status": "ok"}


@app.post("/new-session")
async def new_session(req: NewSessionRequest):
    """
    Create a new conversation session.

    1. Proxies the request to Backend to create/reset the ADK session
    2. Kicks off a background task to warm caches (both Interceptor and Backend)
       so that the first real query is fast
    """
    result = await backend_proxy.new_session(req.user_id, req.name)

    # Prefetch user data in background (non-blocking)
    asyncio.create_task(_prefetch_user(req.user_id))

    return result


async def _prefetch_user(user_id: str):
    """
    Background task: warm both Interceptor and Backend caches for a user.

    - Interceptor side: ToolExecutor prefetches invoices, breakdowns, roaming,
      tickets, and wallet data from Supabase
    - Backend side: Calls /prefetch endpoint to warm the Backend's billing cache
    """
    try:
        _tool_executor.prefetch_user_data(user_id)
        # Also warm the Backend's caches via a lightweight HTTP call
        await backend_proxy.request("POST", "/prefetch", {"user_id": user_id})
    except Exception as e:
        logger.warning(f"Background prefetch failed: {e}")


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Main chat endpoint (synchronous).

    Flow:
      1. Inject chat-specific context into the message
         (adds [USER_ID], [CONTEXT: Web chat interface], formatting instructions)
      2. Forward the enhanced message to Backend /chat
      3. Format the response for the chat UI (clean up markdown, structure payment options)
      4. Return both raw and formatted replies

    The context injection tells the Backend agent:
      - Which channel this is (chat vs voice) — affects response length/format
      - The authenticated user ID — so the agent doesn't ask for it
      - Formatting guidelines (use tables, bold, etc.)
    """
    # Step 1: Inject channel context
    enhanced_message = inject_chat_context(
        req.message, req.user_id, req.name
    )
    logger.info(f"Chat request: user_id={req.user_id}, message_len={len(req.message)}")

    # Step 2: Forward to Backend
    backend_response = await backend_proxy.chat(
        message=enhanced_message, user_id=req.user_id, name=req.name
    )

    if not isinstance(backend_response, dict):
        backend_response = {"reply": str(backend_response)}

    # Step 3: Extract and format the reply
    raw_reply = normalize_to_text(backend_response.get("reply", ""))
    if not raw_reply:
        raw_reply = normalize_to_text(backend_response.get("detail", ""))
    if not raw_reply:
        raw_reply = "I'm here to help! How can I assist you today?"

    # Format for chat: clean whitespace, structure payment options
    formatted_reply = normalize_to_text(format_reply_for_chat(raw_reply)) or raw_reply

    # Return both raw (for debugging) and formatted (for display) replies
    backend_response["raw_reply"] = raw_reply
    backend_response["reply"] = formatted_reply
    return backend_response


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    Streaming chat endpoint (SSE).

    Same as /chat but streams the Backend's SSE response through to the Frontend.
    The Backend sends intermediate status updates (tool call labels) and the
    final response as SSE events.
    """
    enhanced_message = inject_chat_context(
        req.message, req.user_id, req.name
    )

    async def generate():
        """Pass through SSE events from Backend."""
        async for chunk in backend_proxy.chat_stream(
            message=enhanced_message, user_id=req.user_id, name=req.name
        ):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# VOICE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/voice/token")
async def get_voice_token(user_id: str = Query(..., description="User identifier")):
    """
    Get an ephemeral token for the OpenAI Realtime API.

    Called by the Frontend when the user starts a voice call. The token is
    short-lived and scoped to a single WebRTC session.

    Configuration sent to OpenAI:
      - Model: gpt-4o-realtime-preview (configurable via env)
      - Voice: "coral" (female, warm tone)
      - Instructions: Loaded from eleven_labs_prompts/system.md
      - Tools: validate_user + forward_to_backend (defined in utils/tools.py)
      - VAD: Server-side voice activity detection with tuned thresholds

    Auth reset: Resets voice auth state for this user on every new token request,
    ensuring the user must re-authenticate at the start of each call.
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
                    "voice": "coral",
                    "instructions": VOICE_SYSTEM_INSTRUCTIONS,
                    "input_audio_transcription": {"model": "whisper-1"},
                    "tools": VOICE_TOOLS,
                    "turn_detection": {
                        "type": "server_vad",       # Server-side voice activity detection
                        "threshold": 0.75,           # Sensitivity (higher = less sensitive)
                        "prefix_padding_ms": 200,    # Audio before speech detection
                        "silence_duration_ms": 500,  # Silence before end-of-turn
                    },
                },
            )

        if response.status_code >= 400:
            error_body = response.text
            logger.error(f"OpenAI session creation failed: {response.status_code} {error_body}")
            raise HTTPException(status_code=502, detail=f"OpenAI API error ({response.status_code}): {error_body[:300]}")

        session_data = response.json()
        client_secret = session_data.get("client_secret", {})
        ephemeral_token = client_secret.get("value", "") if isinstance(client_secret, dict) else ""

        if not ephemeral_token:
            logger.error(f"No ephemeral token in response: {json.dumps(session_data)[:500]}")
            raise HTTPException(status_code=502, detail="No ephemeral token returned by OpenAI")

        # Reset auth state — user must re-authenticate on each new voice session
        _voice_auth.reset_auth(user_id)

        return {
            "ephemeral_token": ephemeral_token,
            "model": config.OPENAI_REALTIME_MODEL,
            "voice": "coral",
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
    Handle tool calls from the OpenAI Realtime API during a voice session.

    The OpenAI Realtime model (running on the client via WebRTC) can call two tools:
      1. validate_user — Authenticate the caller by their spoken User ID
      2. forward_to_backend — Forward a support query to the Backend agent

    The Frontend intercepts these tool calls from the WebRTC connection and
    POSTs them here. We execute the tool and return the result, which the
    Frontend sends back to the Realtime model.

    Args:
        req: ToolCallRequest with tool_name, arguments, user_id, and call_id

    Returns:
        Dict with call_id and JSON-encoded result string
    """
    logger.info(f"Voice tool call: name={req.tool_name}, user_id={req.user_id}, call_id={req.call_id}")

    if req.tool_name == "validate_user":
        return await _handle_validate_user(req)
    elif req.tool_name == "forward_to_backend":
        return await _handle_forward_to_backend(req)
    else:
        return {"call_id": req.call_id, "result": json.dumps({"error": f"Unknown tool: {req.tool_name}"})}


async def _handle_validate_user(req: ToolCallRequest) -> dict:
    """
    Handle the validate_user tool call from voice.

    Flow:
      1. Extract and normalize the spoken user ID (strip non-digits)
      2. Validate against the 'users_voice' table in Supabase
      3. If valid: mark user as authenticated, prefetch their data in background
      4. Return result to the Realtime model (which speaks the confirmation/error)
    """
    raw_user_id = req.arguments.get("user_id", "").strip()
    # Normalize spoken input: "forty two" → "42", "one two three" → "123"
    spoken_user_id = extract_user_id_from_spoken(raw_user_id)
    logger.info(f"Validating user: raw='{raw_user_id}', normalized='{spoken_user_id}'")

    if not spoken_user_id:
        return {
            "call_id": req.call_id,
            "result": json.dumps({
                "authenticated": False,
                "reason": "No user ID provided",
                "message": "No valid user ID could be extracted from the input."
            }),
        }

    # Validate against Supabase 'users_voice' table
    authenticated, customer_id, message = await _voice_auth.validate_user_id(spoken_user_id)

    if authenticated and customer_id:
        # Mark as authenticated for this session — subsequent forward_to_backend
        # calls will use this customer_id
        _voice_auth.set_authenticated(req.user_id, customer_id)
        # Prefetch user data in background so subsequent tool calls are instant
        asyncio.create_task(_prefetch_user(customer_id))
        return {
            "call_id": req.call_id,
            "result": json.dumps({"authenticated": True, "customer_id": customer_id, "message": message}),
        }
    else:
        return {
            "call_id": req.call_id,
            "result": json.dumps({"authenticated": False, "reason": message or "Validation failed", "message": message}),
        }


async def _handle_forward_to_backend(req: ToolCallRequest) -> dict:
    """
    Handle the forward_to_backend tool call from voice.

    Flow:
      1. Check that the user is authenticated (must have called validate_user first)
      2. Inject voice-specific context into the message
      3. Forward to Backend /chat (full agent loop)
      4. Format the response for voice (strip markdown, limit to 1-3 sentences)
      5. Return the voice-friendly response to the Realtime model

    The Realtime model speaks this response back to the caller via WebRTC audio.
    """
    start_total = time.time()

    user_message = req.arguments.get("message", "")
    if not user_message:
        return {"call_id": req.call_id, "result": json.dumps({"error": "No message provided"})}

    # Require authentication before processing any support query
    if not _voice_auth.is_authenticated(req.user_id):
        return {
            "call_id": req.call_id,
            "result": json.dumps({"error": "User not authenticated. Please ask for their User ID first and call validate_user."}),
        }

    # Use the validated customer ID (e.g., "42") instead of the email-based user_id
    customer_id = _voice_auth.get_customer_id(req.user_id) or req.user_id
    # Inject voice context: [USER_ID: 42] [CONTEXT: Voice call. User authenticated.]
    enhanced_message = inject_voice_context(user_message, customer_id, is_authenticated=True)

    try:
        # Forward to Backend's full agent loop
        start_backend = time.time()
        backend_response = await backend_proxy.chat(message=enhanced_message, user_id=customer_id)
        backend_time = time.time() - start_backend
        logger.info(f"⏱️ Backend took: {backend_time:.2f}s")

        # Extract the text reply
        raw_reply = normalize_to_text(
            backend_response.get("reply", "") if isinstance(backend_response, dict) else str(backend_response)
        )
        if not raw_reply:
            raw_reply = "I couldn't get that information right now."

        # Format for voice: strip markdown, limit to 1-3 sentences, replace symbols
        voice_reply = normalize_to_text(format_reply_for_voice(raw_reply)) or raw_reply

        total_time = time.time() - start_total
        logger.info(f"⏱️ TOTAL forward_to_backend: {total_time:.2f}s")

        return {"call_id": req.call_id, "result": json.dumps({"response": voice_reply})}
    except HTTPException:
        return {"call_id": req.call_id, "result": json.dumps({"error": "Sorry, I'm having trouble reaching the support system right now."})}
    except Exception as exc:
        logger.exception("forward_to_backend failed")
        return {"call_id": req.call_id, "result": json.dumps({"error": f"Backend error: {exc}"})}
