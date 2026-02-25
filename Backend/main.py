from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import json
import time

# Load environment variables first
load_dotenv(override=True)

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import google.genai as genai

from agent import root_agent

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

APP_NAME = "Backend"

session_service = InMemorySessionService()

runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)


class ChatRequest(BaseModel):
    message: str
    user_id: str
    name: Optional[str] = None

class NewSessionRequest(BaseModel):
    user_id: str
    name: Optional[str] = None

class FastChatRequest(BaseModel):
    message: str
    user_id: str
    tool_data: Dict[str, Any]
    name: Optional[str] = None

class PrefetchRequest(BaseModel):
    user_id: str

# ROUTES 
@app.get("/")
def health():
    return {"status": "ok"}

@app.options("/chat")
async def chat_options():
    return {"status": "ok"}


@app.post("/prefetch")
async def prefetch_user_data(req: PrefetchRequest):
    """Warm all caches for a user. Called on login/new-session."""
    from tools.billing_tools import (
        get_user_invoices, get_payment_methods,
        check_roaming_status,
    )
    from tools.support_tools import get_open_tickets

    uid = req.user_id
    try:
        # These calls populate the billing cache (including breakdown prefetch)
        get_user_invoices(uid)
        get_payment_methods(uid)
        check_roaming_status(uid)
        get_open_tickets(uid)
        print(f"⚡ Prefetched all Backend caches for user {uid}")
        return {"status": "ok"}
    except Exception as e:
        print(f"Prefetch error: {e}")
        return {"status": "partial", "error": str(e)}

@app.post("/new-session")
async def new_session(req: NewSessionRequest):
    """
    Create a new session for a user.
    This will reset the conversation history and start fresh.
    """
    session_id = f"{req.user_id}-default"
    
    try:
        # Create or reset the session
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
        # If session already exists, delete and recreate
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

@app.post("/chat")
async def chat(req: ChatRequest):
    import time
    start_total = time.time()
    
    session_id = f"{req.user_id}-default"
    
    # Message comes pre-injected with context from Interceptor
    # The Interceptor handles channel-specific context injection
    # Format: [CONTEXT: ...] User message: <actual message>
    message_text = req.message

    content = types.Content(
        role="user",
        parts=[types.Part(text=message_text)]
    )

    async def run_agent():
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
            # Log tool calls for timing visibility
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        print(f"  ⏱️ [{elapsed:.2f}s] step={step} Tool call: {part.function_call.name}")
                    if hasattr(part, 'function_response') and part.function_response:
                        print(f"  ⏱️ [{elapsed:.2f}s] step={step} Tool response: {part.function_response.name}")
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

        #  create session ON DEMAND
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=req.user_id,
            session_id=session_id,
        )

        #  retry once (now runner sees it)
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



@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Streaming chat endpoint with intermediate status updates."""
    session_id = f"{req.user_id}-default"
    message_text = req.message

    content = types.Content(
        role="user",
        parts=[types.Part(text=message_text)]
    )

    async def generate():
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
                        if hasattr(part, 'function_call') and part.function_call:
                            tool_label = part.function_call.name.replace("_", " ")
                            status_msg = json.dumps({"status": f"Looking up {tool_label}...", "done": False})
                            yield f"data: {status_msg}\n\n"

                if event.is_final_response() and event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            final_text = part.text

            if final_text:
                yield f"data: {json.dumps({'text': final_text, 'done': True})}\n\n"
            else:
                yield f"data: {json.dumps({'text': 'Im here to help! How can I assist you today?', 'done': True})}\n\n"

        except ValueError as e:
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


# Gemini client for fast-path (single LLM call with pre-fetched tool data)
_gemini_client = genai.Client()
_FAST_MODEL = os.environ.get("GOOGLE_GENAI_MODEL", "gemini-2.5-flash-lite")

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
    """Fast-path: tool data already fetched, just need 1 Gemini call to format."""
    start = time.time()

    template = FAST_FORMAT_PROMPT

    prompt = template.format(
        message=req.message,
        tool_data=json.dumps(req.tool_data, indent=2, default=str)
    )

    try:
        reply = None
        last_err = None
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
        # Return error so interceptor can fall back
        return {"reply": reply, "user_name": req.name, "fast_path_error": True}

    elapsed = time.time() - start
    print(f"⚡ Fast-path took: {elapsed:.2f}s")

    return {"reply": reply, "user_name": req.name}
