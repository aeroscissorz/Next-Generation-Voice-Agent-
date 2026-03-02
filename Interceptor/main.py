"""
Interceptor Service
Channel-specific middleware for message processing and formatting
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)

from utils import (
    config,
    inject_chat_context,
    inject_voice_context,
    format_reply_for_chat,
    format_reply_for_voice,
    normalize_to_text,
    load_system_instructions,
    extract_user_id_from_spoken,
    ChatRequest,
    NewSessionRequest,
    ToolCallRequest,
    VOICE_TOOLS,
)
from utils.intent_detector import detect_intent
from services import backend_proxy, init_voice_auth_service

app = FastAPI(title="Chat Interceptor")
logger = logging.getLogger("interceptor")

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

_voice_auth = init_voice_auth_service(supabase)
VOICE_SYSTEM_INSTRUCTIONS = load_system_instructions(config.VOICE_INSTRUCTIONS_PATH)


# --- Chat Endpoints ---

@app.get("/")
async def health():
    return await backend_proxy.health_check()


@app.options("/chat")
async def chat_options():
    return {"status": "ok"}


@app.post("/new-session")
async def new_session(req: NewSessionRequest):
    result = await backend_proxy.new_session(req.user_id, req.name)

    # Prefetch user data in background to warm caches
    asyncio.create_task(_prefetch_user(req.user_id))

    return result


async def _prefetch_user(user_id: str):
    """Background task: warm Interceptor + Backend caches for this user."""
    try:
        _tool_executor.prefetch_user_data(user_id)
        # Also warm the Backend's caches via a lightweight call
        await backend_proxy.request("POST", "/prefetch", {"user_id": user_id})
    except Exception as e:
        logger.warning(f"Background prefetch failed: {e}")


@app.post("/chat")
async def chat(req: ChatRequest):
    enhanced_message = inject_chat_context(
        req.message, req.user_id, req.name
    )
    logger.info(f"Chat request: user_id={req.user_id}, message_len={len(req.message)}")

    backend_response = await backend_proxy.chat(
        message=enhanced_message, user_id=req.user_id, name=req.name
    )

    if not isinstance(backend_response, dict):
        backend_response = {"reply": str(backend_response)}

    raw_reply = normalize_to_text(backend_response.get("reply", ""))
    if not raw_reply:
        raw_reply = normalize_to_text(backend_response.get("detail", ""))
    if not raw_reply:
        raw_reply = "I'm here to help! How can I assist you today?"

    formatted_reply = normalize_to_text(format_reply_for_chat(raw_reply)) or raw_reply

    backend_response["raw_reply"] = raw_reply
    backend_response["reply"] = formatted_reply
    return backend_response



@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    enhanced_message = inject_chat_context(
        req.message, req.user_id, req.name
    )

    async def generate():
        async for chunk in backend_proxy.chat_stream(
            message=enhanced_message, user_id=req.user_id, name=req.name
        ):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# --- Voice Endpoints ---

@app.get("/voice/token")
async def get_voice_token(user_id: str = Query(..., description="User identifier")):
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
                        "type": "server_vad",
                        "threshold": 0.75,
                        "prefix_padding_ms": 200,
                        "silence_duration_ms": 500,
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

        # Reset auth only on fresh connections (new voice session)
        # This ensures user must re-authenticate when starting a new call
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
    logger.info(f"Voice tool call: name={req.tool_name}, user_id={req.user_id}, call_id={req.call_id}")

    if req.tool_name == "validate_user":
        return await _handle_validate_user(req)
    elif req.tool_name == "forward_to_backend":
        return await _handle_forward_to_backend(req)
    else:
        return {"call_id": req.call_id, "result": json.dumps({"error": f"Unknown tool: {req.tool_name}"})}


async def _handle_validate_user(req: ToolCallRequest) -> dict:
    raw_user_id = req.arguments.get("user_id", "").strip()
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

    authenticated, customer_id, message = await _voice_auth.validate_user_id(spoken_user_id)

    if authenticated and customer_id:
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
    start_total = time.time()

    user_message = req.arguments.get("message", "")
    if not user_message:
        return {"call_id": req.call_id, "result": json.dumps({"error": "No message provided"})}

    if not _voice_auth.is_authenticated(req.user_id):
        return {
            "call_id": req.call_id,
            "result": json.dumps({"error": "User not authenticated. Please ask for their User ID first and call validate_user."}),
        }

    customer_id = _voice_auth.get_customer_id(req.user_id) or req.user_id
    enhanced_message = inject_voice_context(user_message, customer_id, is_authenticated=True)

    try:
        start_backend = time.time()
        backend_response = await backend_proxy.chat(message=enhanced_message, user_id=customer_id)
        backend_time = time.time() - start_backend
        logger.info(f"⏱️ Backend took: {backend_time:.2f}s")

        raw_reply = normalize_to_text(
            backend_response.get("reply", "") if isinstance(backend_response, dict) else str(backend_response)
        )
        if not raw_reply:
            raw_reply = "I couldn't get that information right now."

        voice_reply = normalize_to_text(format_reply_for_voice(raw_reply)) or raw_reply

        total_time = time.time() - start_total
        logger.info(f"⏱️ TOTAL forward_to_backend: {total_time:.2f}s")

        return {"call_id": req.call_id, "result": json.dumps({"response": voice_reply})}
    except HTTPException:
        return {"call_id": req.call_id, "result": json.dumps({"error": "Sorry, I'm having trouble reaching the support system right now."})}
    except Exception as exc:
        logger.exception("forward_to_backend failed")
        return {"call_id": req.call_id, "result": json.dumps({"error": f"Backend error: {exc}"})}
