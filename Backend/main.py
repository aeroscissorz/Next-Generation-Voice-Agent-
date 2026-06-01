"""
Backend FastAPI Server
======================
The main entry point for the Backend service. Exposes REST endpoints that the
Interceptor (and optionally the Frontend directly) calls to interact with the
AI support agent.

Architecture Overview:
  Frontend ──► Interceptor ──► Backend (this file) ──► Gemini LLM + Supabase
                                  │
                                  ├─ /chat          (synchronous, full agent loop)
                                  ├─ /chat/stream   (SSE streaming with tool-call status)
                                  ├─ /chat/fast     (single LLM call, no agent loop)
                                  ├─ /new-session   (reset conversation history)
                                  └─ /prefetch      (warm caches for a user)

Key Concepts:
  - Runner: ADK's orchestrator that manages the agent loop (user msg → LLM → tool calls → LLM → response)
  - InMemorySessionService: Stores conversation history per user in memory (lost on restart)
  - Session ID convention: "{user_id}-default" — one session per user
  - Fast-path (/chat/fast): Bypasses the agent loop entirely; the Interceptor pre-fetches
    tool data and sends it here for a single Gemini call to format a response.
"""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import json
import time

# Load environment variables first — must happen before any Google SDK imports
# so that GOOGLE_API_KEY / GOOGLE_GENAI_MODEL are available
load_dotenv(override=True)

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import google.genai as genai

# Import the root agent defined in agent.py
from agent import root_agent

# ─── App Setup ────────────────────────────────────────────────────────────────
app = FastAPI()

# CORS: Allow all origins for development. In production, restrict to the
# Frontend's domain and the Interceptor's origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Application name used by ADK to namespace sessions
APP_NAME = "Backend"

# ─── Session & Runner ────────────────────────────────────────────────────────
# InMemorySessionService: Stores conversation history in a dict keyed by
# (app_name, user_id, session_id). Data is lost on server restart.
# For production, swap with a persistent session service (e.g., Firestore).
session_service = InMemorySessionService()

# Runner: ADK's main orchestrator. It takes a user message, runs the agent loop
# (LLM reasoning → tool calls → LLM reasoning → ... → final response), and
# yields events for each step. The runner uses the session service to maintain
# conversation context across turns.
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)


# ─── Request Models ──────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    """Standard chat request. Message may include context injected by the Interceptor."""
    message: str
    user_id: str
    name: Optional[str] = None

class NewSessionRequest(BaseModel):
    """Request to create/reset a conversation session for a user."""
    user_id: str
    name: Optional[str] = None

class FastChatRequest(BaseModel):
    """Fast-path request: tool data already fetched by the Interceptor,
    just needs a single LLM call to format a human-readable response."""
    message: str
    user_id: str
    tool_data: Dict[str, Any]   # Pre-fetched data (invoices, outages, etc.)
    name: Optional[str] = None

class PrefetchRequest(BaseModel):
    """Request to warm all caches for a user (called on login/new-session)."""
    user_id: str


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/")
def health():
    """Simple health check endpoint used by the Interceptor to verify Backend is up."""
    return {"status": "ok"}

@app.options("/chat")
async def chat_options():
    """CORS preflight handler for the /chat endpoint."""
    return {"status": "ok"}


# ─── Prefetch Endpoint ───────────────────────────────────────────────────────
@app.post("/prefetch")
async def prefetch_user_data(req: PrefetchRequest):
    """
    Warm all Supabase caches for a user. Called by the Interceptor on
    login or new-session so that subsequent tool calls are instant.

    Caches warmed:
      - Invoices (+ invoice breakdowns for each invoice)
      - Roaming status
      - Open support tickets
      - Wallet balances per invoice
    """
    from tools.billing_tools import (
        get_user_invoices,
        check_roaming_status, check_wallet_amount_settlement,
    )
    from tools.support_tools import get_open_tickets

    uid = req.user_id
    try:
        # These calls populate the in-memory billing cache (see billing_tools._query_cache)
        # get_user_invoices also prefetches breakdowns for all invoices
        invoices = get_user_invoices(uid)
        check_roaming_status(uid)
        get_open_tickets(uid)

        # Warm wallet cache for each invoice (needed for bill overdue → payment flow)
        for inv in (invoices or []):
            inv_id = str(inv.get("invoice_id", ""))
            if inv_id:
                try:
                    check_wallet_amount_settlement(uid, inv_id)
                except Exception:
                    pass  # Non-critical — skip silently

        print(f"⚡ Prefetched all Backend caches for user {uid}")
        return {"status": "ok"}
    except Exception as e:
        print(f"Prefetch error: {e}")
        return {"status": "partial", "error": str(e)}


# ─── New Session Endpoint ────────────────────────────────────────────────────
@app.post("/new-session")
async def new_session(req: NewSessionRequest):
    """
    Create a new session for a user, resetting conversation history.

    Session ID convention: "{user_id}-default"
    If a session already exists, it's deleted and recreated (full reset).
    This is called when the user clicks "New Chat" in the Frontend.
    """
    session_id = f"{req.user_id}-default"
    
    try:
        # Attempt to create a fresh session
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=req.user_id,
            session_id=session_id,
        )
        
        return {
            "status": "success",
            "message": "New session created successfully",
            "session_id": session_id,
            "user_id": req.user_id,
            "user_name": req.name
        }
    except Exception as e:
        # Session likely already exists — delete and recreate
        try:
            await session_service.delete_session(
                app_name=APP_NAME,
                user_id=req.user_id,
                session_id=session_id,
            )
            await session_service.create_session(
                app_name=APP_NAME,
                user_id=req.user_id,
                session_id=session_id,
            )
            return {
                "status": "success",
                "message": "Session reset successfully",
                "session_id": session_id,
                "user_id": req.user_id,
                "user_name": req.name
            }
        except Exception as reset_error:
            return {
                "status": "error",
                "message": f"Failed to create session: {str(reset_error)}"
            }


# ─── Synchronous Chat Endpoint ──────────────────────────────────────────────
@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Main chat endpoint (synchronous). Runs the full agent loop and returns
    the final text response.

    Flow:
      1. Build a Content object from the user's message
      2. Run the agent loop via runner.run_async() — this may involve
         multiple LLM calls and tool executions
      3. Collect the final response text from the last event
      4. If session doesn't exist, auto-create it and retry once

    The message arrives pre-injected with context from the Interceptor:
      Format: "[CONTEXT: ...] User message: <actual message>"
    This tells the agent whether it's a voice call or web chat, and includes
    the authenticated user ID so the agent doesn't need to ask for it.
    """
    import time
    start_total = time.time()
    
    session_id = f"{req.user_id}-default"
    
    # Message comes pre-injected with context from Interceptor
    # The Interceptor handles channel-specific context injection
    # Format: [USER_ID: ...] [CONTEXT: Voice call / Web chat interface] User message: <msg>
    message_text = req.message

    # Wrap the message in ADK's Content format (role="user")
    content = types.Content(
        role="user",
        parts=[types.Part(text=message_text)]
    )

    async def run_agent():
        """
        Execute the agent loop and return the final response text.
        
        The runner yields events for each step:
          - Tool call events (function_call) — logged for timing visibility
          - Tool response events (function_response) — logged for debugging
          - Final response event (is_final_response=True) — contains the reply
        """
        final_text = ""
        step = 0
        async for event in runner.run_async(
            user_id=req.user_id,
            session_id=session_id,
            new_message=content,
        ):
            step += 1
            elapsed = time.time() - start_total
            author = getattr(event, 'author', '?')
            etype = type(event).__name__
            is_final = event.is_final_response()

            # Log tool calls and responses for timing/debugging
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        print(f"  ⏱️ [{elapsed:.2f}s] step={step} Tool call: {part.function_call.name}")
                    if hasattr(part, 'function_response') and part.function_response:
                        print(f"  ⏱️ [{elapsed:.2f}s] step={step} Tool response: {part.function_response.name}")

            # Capture the final text response from the agent
            if is_final and event.content and event.content.parts:
                final_text = event.content.parts[0].text
                print(f"  ⏱️ [{elapsed:.2f}s] step={step} FINAL response received")

        return final_text if final_text else "I'm here to help! How can I assist you today?"

    try:
        start_agent = time.time()
        reply = await run_agent()
        agent_time = time.time() - start_agent
        print(f"⏱️ Agent processing took: {agent_time:.2f}s")

    except ValueError as e:
        if "Session not found" not in str(e):
            raise

        # Auto-create session on demand if it doesn't exist yet
        # This handles the case where a user sends a message before /new-session
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=req.user_id,
            session_id=session_id,
        )

        # Retry the agent loop now that the session exists
        start_agent = time.time()
        reply = await run_agent()
        agent_time = time.time() - start_agent
        print(f"⏱️ Agent processing took: {agent_time:.2f}s (after session create)")

    total_time = time.time() - start_total
    print(f"⏱️ TOTAL Backend /chat: {total_time:.2f}s")
    
    return {
        "reply": reply,
        "user_name": req.name
    }


# ─── Streaming Chat Endpoint ────────────────────────────────────────────────
@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).

    Unlike /chat, this streams intermediate status updates to the Frontend
    so the UI can show what the agent is doing (e.g., "Fetching your invoices...",
    "Checking for outages...") while the agent loop is still running.

    SSE message format:
      - Status update:  {"status": "Fetching your invoices...", "done": false}
      - Final response: {"text": "Here are your invoices...", "done": true}
      - Error:          {"error": "Something went wrong", "done": true}

    The tool_labels dict maps tool function names to user-friendly status messages.
    """
    session_id = f"{req.user_id}-default"
    message_text = req.message

    content = types.Content(
        role="user",
        parts=[types.Part(text=message_text)]
    )

    async def generate():
        """SSE generator — yields 'data: {...}\n\n' lines."""
        try:
            final_text = ""

            async for event in runner.run_async(
                user_id=req.user_id,
                session_id=session_id,
                new_message=content,
            ):
                # Stream tool call status so the UI shows activity
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        # When the agent calls a tool, send a status message
                        if hasattr(part, 'function_call') and part.function_call:
                            fc = part.function_call
                            print(f"🔧 TOOL CALL: {fc.name} args={fc.args}")

                            # Map tool names to user-friendly status labels
                            tool_labels = {
                                "get_user_invoices": "Fetching your invoices...",
                                "get_user_invoices_breakdown": "Loading invoice breakdown...",
                                "check_roaming_status": "Checking roaming status...",
                                "check_roaming_status_monthwise": "Checking roaming history...",
                                "update_roaming_status_monthwise": "Updating roaming settings...",
                                "check_wallet_amount_settlement": "Checking wallet balance...",
                                "update_wallet_amount": "Updating wallet credit...",
                                "create_wallet_entry": "Processing refund...",
                                "get_open_tickets": "Loading support tickets...",
                                "check_outage": "Checking for outages in your area...",
                                "search_company_knowledge": "Searching knowledge base...",
                                "is_user_service_active": "Checking your service status...",
                                "get_bill_overdue_date": "Checking bill due date...",
                                "set_promise_date": "Setting your promise date...",
                                "make_payment": "Processing your payment...",
                                "set_settle_wallet_amount": "Settling wallet credit...",
                                "get_promise_date": "Getting promised date...."
                            }
                            label = tool_labels.get(part.function_call.name, f"Looking up {part.function_call.name.replace('_', ' ')}...")
                            status_msg = json.dumps({"status": label, "done": False})
                            yield f"data: {status_msg}\n\n"

                        # Log tool responses for debugging
                        if hasattr(part, 'function_response') and part.function_response:
                            print(f"🔧 TOOL RESPONSE: {part.function_response.name} => {str(part.function_response.response)[:500]}")

                # Capture the final text response
                if event.is_final_response() and event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            final_text = part.text
                            print(f"📝 FINAL RESPONSE: {final_text[:300]}")

            # Send the final response (or a fallback)
            if final_text:
                yield f"data: {json.dumps({'text': final_text, 'done': True})}\n\n"
            else:
                yield f"data: {json.dumps({'text': 'Im here to help! How can I assist you today?', 'done': True})}\n\n"

        except ValueError as e:
            # Auto-create session and retry if session not found
            if "Session not found" in str(e):
                await session_service.create_session(
                    app_name=APP_NAME,
                    user_id=req.user_id,
                    session_id=session_id,
                )
                final_text = ""
                async for event in runner.run_async(
                    user_id=req.user_id,
                    session_id=session_id,
                    new_message=content,
                ):
                    if event.is_final_response() and event.content and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                final_text = part.text
                if final_text:
                    yield f"data: {json.dumps({'text': final_text, 'done': True})}\n\n"
                else:
                    yield f"data: {json.dumps({'text': 'Im here to help! How can I assist you today?', 'done': True})}\n\n"
            else:
                yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ─── Fast-Path Chat Endpoint ────────────────────────────────────────────────
# Gemini client for fast-path (single LLM call with pre-fetched tool data)
_gemini_client = genai.Client()
_FAST_MODEL = os.environ.get("GOOGLE_GENAI_MODEL", "gemini-2.5-flash-lite")

# System prompt for the fast-path: tells Gemini to format pre-fetched data
# into a concise, natural response. No tool calling — just text generation.
FAST_FORMAT_PROMPT = """You are a telecom customer support agent. Be concise — 2-3 sentences max. Speak naturally.

User message: {message}

Data (JSON):
{tool_data}

Rules:
- Answer the user's question directly based on the data.
- When showing invoices or multiple items, ALWAYS use a markdown table.
- Don't repeat data the user didn't ask about.
- If an outage was found, tell the user what you found and ask "Would you like me to process a refund for this?" Do NOT process any refund yourself.
- If no outage found, say you couldn't find an outage record.
- For policy/knowledge questions, summarize the relevant policy concisely. If the data doesn't cover the question, say you're not sure.
- End with a short follow-up question if relevant.
- Never invent data. If the data is empty, say so."""


@app.post("/chat/fast")
async def chat_fast(req: FastChatRequest):
    """
    Fast-path endpoint: tool data already fetched by the Interceptor,
    just needs a single Gemini call to format a human-readable response.

    This skips the entire agent loop (no tool calling, no multi-step reasoning).
    The Interceptor's intent detector identifies simple queries (e.g., "show my invoices"),
    fetches the data directly from Supabase via ToolExecutor, and sends it here
    for formatting.

    Latency: ~0.5-1s (vs 3-8s for the full agent loop)

    Retry logic: Up to 3 attempts with exponential backoff for 503/UNAVAILABLE errors.
    On failure, returns fast_path_error=True so the Interceptor can fall back to /chat.
    """
    start = time.time()

    template = FAST_FORMAT_PROMPT

    # Inject the user's message and pre-fetched tool data into the prompt
    prompt = template.format(
        message=req.message,
        tool_data=json.dumps(req.tool_data, indent=2, default=str)
    )

    try:
        reply = None
        last_err = None
        # Retry up to 3 times for transient Gemini errors
        for attempt in range(3):
            try:
                response = _gemini_client.models.generate_content(
                    model=_FAST_MODEL,
                    contents=prompt,
                )
                reply = response.text or "I couldn't process that right now."
                break
            except Exception as e:
                last_err = e
                # Retry on 503 / UNAVAILABLE (Gemini overloaded)
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    import asyncio
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise
        if reply is None:
            raise last_err
    except Exception as e:
        print(f"Fast-path Gemini error: {e}")
        reply = "I'm having trouble processing that. Let me try the normal way."
        # Return error flag so the Interceptor can fall back to the full agent loop
        return {"reply": reply, "user_name": req.name, "fast_path_error": True}

    elapsed = time.time() - start
    print(f"⚡ Fast-path took: {elapsed:.2f}s")

    return {"reply": reply, "user_name": req.name}
