from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Backend")

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
    name: str = None  # Optional: User's name for personalization

class NewSessionRequest(BaseModel):
    user_id: str
    name: str = None  # Optional: User's name for personalization

# ROUTES 
@app.get("/")
def health():
    logger.info("Health check endpoint called")
    return {"status": "ok"}

@app.options("/chat")
async def chat_options():
    logger.info("CORS preflight request received")
    return {"status": "ok"}

@app.post("/new-session")
async def new_session(req: NewSessionRequest):
    """
    Create a new session for a user.
    This will reset the conversation history and start fresh.
    """
    logger.info(f"Creating new session for user: {req.user_id}, name: {req.name}")
    session_id = f"{req.user_id}-default"
    
    try:
        # Create or reset the session
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=req.user_id,
            session_id=session_id,
        )
        
        logger.info(f"✓ New session created successfully: {session_id}")
        return {
            "status": "success",
            "message": "New session created successfully",
            "session_id": session_id,
            "user_id": req.user_id,
            "user_name": req.name
        }
    except Exception as e:
        # If session already exists, delete and recreate
        logger.warning(f"Session exists, attempting to reset: {session_id}")
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
            logger.info(f"✓ Session reset successfully: {session_id}")
            return {
                "status": "success",
                "message": "Session reset successfully",
                "session_id": session_id,
                "user_id": req.user_id,
                "user_name": req.name
            }
        except Exception as reset_error:
            logger.error(f"✗ Failed to create/reset session: {str(reset_error)}")
            return {
                "status": "error",
                "message": f"Failed to create session: {str(reset_error)}"
            }

@app.post("/chat")
async def chat(req: ChatRequest):
    logger.info(f"📨 Received chat request from user: {req.user_id}")
    logger.info(f"   Message: {req.message[:100]}{'...' if len(req.message) > 100 else ''}")
    logger.info(f"   User name: {req.name}")
    
    session_id = f"{req.user_id}-default"
    
    # Prepare the message with user context
    message_text = req.message
    
    # Add user name context if provided
    if req.name:
        message_text = f"[USER_NAME: {req.name}] " + message_text

    content = types.Content(
        role="user",
        parts=[types.Part(text=message_text)]
    )

    async def run_agent():
        logger.info(f"🤖 Running agent for session: {session_id}")
        final_text = ""
        async for event in runner.run_async(
            user_id=req.user_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_text = event.content.parts[0].text
        logger.info(f"✓ Agent response generated (length: {len(final_text)} chars)")
        return final_text if final_text else "I'm here to help! How can I assist you today?"

    try:
        reply = await run_agent()

    except ValueError as e:
        if "Session not found" not in str(e):
            logger.error(f"✗ Agent error: {str(e)}")
            raise

        logger.warning(f"Session not found, creating on demand: {session_id}")
        #  create session ON DEMAND
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=req.user_id,
            session_id=session_id,
        )

        #  retry once (now runner sees it)
        reply = await run_agent()

    logger.info(f"📤 Sending response back (length: {len(reply)} chars)")
    logger.info(f"   Response preview: {reply[:150]}{'...' if len(reply) > 150 else ''}")
    
    return {
        "reply": reply,
        "user_name": req.name
    }
