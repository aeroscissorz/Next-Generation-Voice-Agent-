from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables first
load_dotenv(override=True)

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

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
    name: Optional[str] = None  # Optional: User's name for personalization

class NewSessionRequest(BaseModel):
    user_id: str
    name: Optional[str] = None  # Optional: User's name for personalization

# ROUTES 
@app.get("/")
def health():
    return {"status": "ok"}

@app.options("/chat")
async def chat_options():
    return {"status": "ok"}

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
        async for event in runner.run_async(
            user_id=req.user_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_text = event.content.parts[0].text
        return final_text if final_text else "I'm here to help! How can I assist you today?"

    try:
        reply = await run_agent()

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
        reply = await run_agent()

    return {
        "reply": reply,
        "user_name": req.name
    }
