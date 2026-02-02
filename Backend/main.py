from fastapi import FastAPI
from pydantic import BaseModel
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
    name: str = None  # Optional: User's name
    channel_type: str = "text"  # Default to "text", can be "voice" for ElevenLabs

# ROUTES 
@app.get("/")
def health():
    return {"status": "ok"}

@app.options("/chat")
async def chat_options():
    return {"status": "ok"}

@app.post("/chat")
async def chat(req: ChatRequest):
    session_id = f"{req.user_id}-default"
    
    # Prepare the message with context about channel type and user name
    message_text = req.message
    
    # Add channel context to the message for the agent
    if req.channel_type == "voice":
        context_prefix = "[VOICE_CHANNEL] "
        if req.name:
            context_prefix += f"[USER_NAME: {req.name}] "
        message_text = context_prefix + message_text
    elif req.name:
        # For text channel, still include name if provided
        message_text = f"[USER_NAME: {req.name}] " + message_text

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
        "channel_type": req.channel_type,
        "user_name": req.name
    }
