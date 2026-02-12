import os
import json
import logging
from typing import Any, Dict, Optional

import httpx

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from supabase import create_client, Client

# ... (imports)

load_dotenv(override=True)

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT_SECONDS = float(os.getenv("INTERCEPTOR_TIMEOUT_SECONDS", "60"))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_GENAI_MODEL = os.getenv("GOOGLE_GENAI_MODEL", "gemini-1.5-flash")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_REALTIME_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview-2025-06-03")

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

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase: {e}")


# ---------------------------------------------------------------------------
# Session auth state  –  keyed by user_id (email from frontend)
# ---------------------------------------------------------------------------
_voice_auth_state: Dict[str, bool] = {}
_voice_customer_id: Dict[str, str] = {}  # Maps email -> validated customer ID (e.g. "42")

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    user_id: str
    name: Optional[str] = None


class NewSessionRequest(BaseModel):
    user_id: str
    name: Optional[str] = None


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    user_id: str
    call_id: str


# ---------------------------------------------------------------------------

# Voice system instructions
# ---------------------------------------------------------------------------
def load_system_instructions():
    """Load system instructions from the markdown file."""
    try:
        # Go up one level from 'Interceptor' to 'eleven_labs_prompts'
        prompt_path = os.path.join(os.path.dirname(__file__), "..", "eleven_labs_prompts", "system.md")
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load system instructions: {e}")
        # Fallback to a minimal instruction set if file read fails
        return """You are a helpful telecom voice assistant. 
        Strictly handle telecom support and billing only. 
        Ask for numeric User ID first. 
        Always say a filler before calling tools.
        """

VOICE_SYSTEM_INSTRUCTIONS = load_system_instructions()

VOICE_TOOLS = [
    {
        "type": "function",
        "name": "validate_user",
        "description": "Validate a user's identity by their User ID. Must be called before any support queries are allowed.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The user ID spoken by the caller"
                }
            },
            "required": ["user_id"]
        }
    },
    {
        "type": "function",
        "name": "forward_to_backend",
        "description": "Forward a user query to the backend support system. Use for billing, invoices, payments, support tickets, outages, roaming, wallet, and all account queries.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "A clear natural-language description of what the user needs"
                }
            },
            "required": ["message"]
        }
    }
]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

from google import genai
# ... (imports)

# ...

def format_reply_for_chat(reply_text: str) -> str:
    if not reply_text:
        return ""

    if not GOOGLE_API_KEY:
        return reply_text

    try:
        client = genai.Client(api_key=GOOGLE_API_KEY)
        prompt = f"""You are a formatting assistant for a customer support chat.
Convert the plain response into clean markdown for chat UI.

Rules:
- Keep meaning exactly the same. Do not add or remove facts.
- Use short paragraphs and line breaks for readability.
- Use bullet points for lists/options.
- Use **bold** for important values (amounts, dates, IDs, statuses).
- If there are multiple structured items, use a markdown table.
- Return only formatted markdown.

Plain response:
{reply_text}
"""
        response = client.models.generate_content(
            model=GOOGLE_GENAI_MODEL,
            contents=prompt
        )
        formatted = response.text if response and response.text else ""
        return formatted.strip() if formatted else reply_text
    except Exception:
        return reply_text


def format_reply_for_voice(reply_text: str) -> str:
    """Convert a backend reply into voice-friendly text (1-2 sentences, no symbols)."""
    if not reply_text:
        return ""

    if not GOOGLE_API_KEY:
        return reply_text

    try:
        client = genai.Client(api_key=GOOGLE_API_KEY)
        prompt = f"""You are a voice formatting assistant. Convert this customer support response
into 1-2 short spoken sentences suitable for text-to-speech.

Rules:
- Extract only the most important information.
- Use simple, spoken language.
- No markdown, no bullet points, no special characters.
- Say "dollar" not "$", say "percent" not "%".
- Numbers should be spoken naturally (e.g., "fourteen hundred" not "1400").
- Keep it brief — maximum 2 sentences.

Response to convert:
{reply_text}
"""
        response = client.models.generate_content(
            model=GOOGLE_GENAI_MODEL,
            contents=prompt
        )
        formatted = response.text if response and response.text else ""
        return formatted.strip() if formatted else reply_text
    except Exception:
        return reply_text


def normalize_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value).strip()
    return str(value).strip()


# ---------------------------------------------------------------------------
# Backend proxy helper
# ---------------------------------------------------------------------------

async def proxy_request(method: str, path: str, payload: Optional[Dict[str, Any]] = None):
    target_url = f"{BACKEND_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.request(method, target_url, json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Backend unavailable: {exc}") from exc

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Invalid JSON from backend") from exc


# ---------------------------------------------------------------------------
# Existing text-chat endpoints  (unchanged)
# ---------------------------------------------------------------------------

@app.get("/")
async def health():
    return await proxy_request("GET", "/")


@app.options("/chat")
async def chat_options():
    return {"status": "ok"}


@app.post("/new-session")
async def new_session(req: NewSessionRequest):
    return await proxy_request("POST", "/new-session", req.model_dump())


@app.post("/chat")
async def chat(req: ChatRequest):
    backend_response = await proxy_request("POST", "/chat", req.model_dump())
    logger.info("Chat request user_id=%s message_len=%s", req.user_id, len(req.message or ""))
    logger.info("Backend response type=%s", type(backend_response).__name__)

    if not isinstance(backend_response, dict):
        backend_response = {"reply": str(backend_response)}
    else:
        logger.info("Backend response keys=%s", list(backend_response.keys()))

    raw_reply = normalize_to_text(backend_response.get("reply", ""))
    if not raw_reply:
        raw_reply = normalize_to_text(backend_response.get("detail", ""))
    if not raw_reply:
        raw_reply = "I'm here to help! How can I assist you today?"

    formatted_reply = format_reply_for_chat(raw_reply)
    formatted_reply = normalize_to_text(formatted_reply) or raw_reply
    logger.info("Raw reply len=%s, formatted reply len=%s", len(raw_reply), len(formatted_reply))
    logger.info("Formatted preview=%s", formatted_reply[:200].replace("\n", " "))

    backend_response["raw_reply"] = raw_reply
    backend_response["reply"] = formatted_reply
    return backend_response


# ===========================================================================
#  VOICE ENDPOINTS  (new)
# ===========================================================================

@app.get("/voice/token")
async def get_voice_token(user_id: str = Query(..., description="User identifier")):
    """
    Generate a short-lived ephemeral token for the browser to connect
    directly to the OpenAI Realtime API via WebRTC.
    Uses a direct HTTP call — no openai SDK dependency needed.
    """
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/realtime/sessions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": OPENAI_REALTIME_MODEL,
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
            logger.error("OpenAI session creation failed: %s %s", response.status_code, error_body)
            raise HTTPException(
                status_code=502,
                detail=f"OpenAI API error ({response.status_code}): {error_body[:300]}",
            )

        session_data = response.json()

        # Extract ephemeral token from response
        client_secret = session_data.get("client_secret", {})
        ephemeral_token = client_secret.get("value", "") if isinstance(client_secret, dict) else ""

        if not ephemeral_token:
            logger.error("No ephemeral token in response: %s", json.dumps(session_data)[:500])
            raise HTTPException(status_code=502, detail="No ephemeral token returned by OpenAI")

        # Reset auth state for this user when they start a new voice session
        _voice_auth_state[user_id] = False
        _voice_customer_id.pop(user_id, None)

        return {
            "ephemeral_token": ephemeral_token,
            "model": OPENAI_REALTIME_MODEL,
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
    Handle tool calls from the Frontend's OpenAI Realtime session.
    - validate_user: handled locally in the interceptor
    - forward_to_backend: proxied to Backend /chat
    """
    logger.info("Voice tool call: name=%s user_id=%s call_id=%s", req.tool_name, req.user_id, req.call_id)

    if req.tool_name == "validate_user":
        return await _handle_validate_user(req)
    elif req.tool_name == "forward_to_backend":
        return await _handle_forward_to_backend(req)
    else:
        return {"call_id": req.call_id, "result": json.dumps({"error": f"Unknown tool: {req.tool_name}"})}


async def _handle_validate_user(req: ToolCallRequest) -> dict:
    """
    Validate user identity. Sends a check to the backend to confirm
    the user exists, then tracks auth state in the interceptor.
    """
    raw_user_id = req.arguments.get("user_id", "").strip()
    # Normalize: remove spaces, dashes to handle "1 0 1" -> "101"
    spoken_user_id = "".join(c for c in raw_user_id if c.isalnum())
    
    logger.info("Validating user: raw='%s' normalized='%s'", raw_user_id, spoken_user_id)

    if not spoken_user_id:
        return {
            "call_id": req.call_id,
            "result": json.dumps({"authenticated": False, "reason": "No user ID provided"}),
        }

    # ---------------------------------------------------------------
    # Supabase "users_voice" validation
    # ---------------------------------------------------------------
    if not supabase:
        logger.error("Supabase not initialized; cannot validate user")
        return {
            "call_id": req.call_id,
            "result": json.dumps({"authenticated": False, "reason": "System error: Validation service unavailable"}),
        }

    try:
        # The 'id' column is an INTEGER, so we cannot use ILIKE.
        # We must ensure the input is numeric before querying to avoid DB errors.
        
        target_id = None
        if spoken_user_id.isdigit():
            target_id = spoken_user_id
        elif raw_user_id.strip().isdigit():
            target_id = raw_user_id.strip()
            
        if not target_id:
             logger.info("Validation failed: User ID '%s' is not numeric, but DB requires integer ID.", spoken_user_id)
             return {
                "call_id": req.call_id,
                "result": json.dumps({
                    "authenticated": False, 
                    "reason": "Invalid User ID format",
                    "message": f"I couldn't find a user with ID {spoken_user_id}. Please double-check your ID."
                }),
            }

        # Check if ID exists in 'users_voice' table using EQ (exact match for integers)
        response = supabase.table("users_voice").select("user_id").eq("user_id", target_id).execute()
        
        # response.data is a list of rows. If empty, user not found.
        if not response.data or len(response.data) == 0:
            logger.info("Validation failed for user_id=%s (not found in DB)", target_id)
            return {
                "call_id": req.call_id,
                "result": json.dumps({
                    "authenticated": False, 
                    "reason": "User ID not found",
                    "message": f"I heard {spoken_user_id}, but I couldn't find that ID. Could you try saying it digit by digit?"
                }),
            }

        # User found
        db_user_id = str(response.data[0]['user_id']) # ensuring it is string for consistency
        logger.info("User validated successfully: %s", db_user_id)
        
        authenticated = True
        _voice_auth_state[req.user_id] = True
        _voice_customer_id[req.user_id] = db_user_id

        return {
            "call_id": req.call_id,
            "result": json.dumps({
                "authenticated": authenticated,
                "customer_id": db_user_id,
                "message": "Thanks! I've confirmed your account. How can I help you today?"
            }),
        }
    except Exception as exc:
        logger.exception("validate_user DB query failed")
        return {
            "call_id": req.call_id,
            "result": json.dumps({"authenticated": False, "reason": "Validation error"}),
        }


async def _handle_forward_to_backend(req: ToolCallRequest) -> dict:
    """
    Forward a user query to the backend, format the reply for voice,
    and return it to the frontend for injection into the Realtime session.
    """
    user_message = req.arguments.get("message", "")
    if not user_message:
        return {
            "call_id": req.call_id,
            "result": json.dumps({"error": "No message provided"}),
        }

    # Check auth state
    if not _voice_auth_state.get(req.user_id, False):
        return {
            "call_id": req.call_id,
            "result": json.dumps({
                "error": "User not authenticated. Please ask for their User ID first and call validate_user."
            }),
        }

    # Use the validated customer ID (2-digit number), not the email
    customer_id = _voice_customer_id.get(req.user_id, req.user_id)

    try:
        backend_response = await proxy_request("POST", "/chat", {
            "message": user_message,
            "user_id": customer_id,
        })

        raw_reply = normalize_to_text(
            backend_response.get("reply", "") if isinstance(backend_response, dict)
            else str(backend_response)
        )
        if not raw_reply:
            raw_reply = "I couldn't get that information right now."

        # Format for voice — short, spoken-friendly
        voice_reply = format_reply_for_voice(raw_reply)
        voice_reply = normalize_to_text(voice_reply) or raw_reply

        return {
            "call_id": req.call_id,
            "result": json.dumps({"response": voice_reply}),
        }
    except HTTPException:
        return {
            "call_id": req.call_id,
            "result": json.dumps({"error": "Sorry, I'm having trouble reaching the support system right now."}),
        }
    except Exception as exc:
        logger.exception("forward_to_backend failed")
        return {
            "call_id": req.call_id,
            "result": json.dumps({"error": f"Backend error: {exc}"}),
        }
