"""
Interceptor Service - Middleware layer between Frontend and Backend
Handles channel-specific message processing and formatting
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import httpx
from google import genai

# Load environment variables
load_dotenv(override=True)

app = FastAPI(title="Interceptor Service")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Initialize Gemini AI for text formatting
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


class MessageRequest(BaseModel):
    message: str
    user_id: str
    name: str = None
    channel: str = "chat"  # 'chat', 'voice', 'telephonic'


class NewSessionRequest(BaseModel):
    user_id: str
    name: str = None


@app.get("/")
def health():
    return {"status": "ok", "service": "interceptor"}


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "interceptor"}


@app.post("/chat")
async def process_chat(req: MessageRequest):
    """
    Process chat message through interceptor layer
    1. Forward to backend agent
    2. Format response based on channel
    3. Return formatted response to frontend
    """
    try:
        # Step 1: Forward message to backend (without channel info)
        async with httpx.AsyncClient(timeout=60.0) as client:
            backend_response = await client.post(
                f"{BACKEND_URL}/chat",
                json={
                    "message": req.message,
                    "user_id": req.user_id,
                    "name": req.name
                }
            )
            
            if backend_response.status_code != 200:
                raise HTTPException(
                    status_code=backend_response.status_code,
                    detail="Backend service error"
                )
            
            backend_data = backend_response.json()
            raw_reply = backend_data.get("reply", "")
        
        # Step 2: Process based on channel
        if req.channel == "chat":
            # Format for chat channel using Gemini AI
            formatted_reply = await format_for_chat_channel(raw_reply)
            return {
                "reply": formatted_reply,
                "user_name": req.name,
                "channel": "chat",
                "formatted": True
            }
        
        elif req.channel in ["voice", "telephonic"]:
            # Voice/Telephonic: Return raw response (handled by ElevenLabs)
            return {
                "reply": raw_reply,
                "user_name": req.name,
                "channel": req.channel,
                "formatted": False
            }
        
        else:
            # Unknown channel, return raw
            return {
                "reply": raw_reply,
                "user_name": req.name,
                "channel": req.channel,
                "formatted": False
            }
    
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Backend service unavailable: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Interceptor error: {str(e)}"
        )


@app.post("/new-session")
async def create_session(req: NewSessionRequest):
    """
    Forward session creation to backend
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            backend_response = await client.post(
                f"{BACKEND_URL}/new-session",
                json={
                    "user_id": req.user_id,
                    "name": req.name
                }
            )
            
            if backend_response.status_code != 200:
                raise HTTPException(
                    status_code=backend_response.status_code,
                    detail="Backend service error"
                )
            
            return backend_response.json()
    
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Backend service unavailable: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Interceptor error: {str(e)}"
        )


async def format_for_chat_channel(text: str) -> str:
    """
    Format response for chat channel using Gemini AI
    Converts natural language into structured markdown
    """
    try:
        prompt = f"""You are a formatting assistant for a customer service chat interface. Convert the following plain text response into well-formatted markdown.

            Rules:
            - Use **bold** for important information like amounts, dates, invoice numbers, and statuses
            - Use bullet points (*) for lists of items or options
            - Use tables (markdown format) when showing multiple invoices, breakdowns, or structured data
            - Keep the friendly, conversational tone intact
            - Add appropriate line breaks for readability
            - Use ✓ checkmarks for confirmations or completed actions
            - Do NOT change the content, meaning, or add new information - only format it
            - Return ONLY the formatted markdown, no explanations or meta-commentary

            Plain text to format:
            {text}"""

        response = client.models.generate_content(
            model=os.getenv("GOOGLE_GENAI_MODEL", "gemini-2.0-flash-exp"),
            contents=prompt
        )
        
        formatted_text = response.text
        return formatted_text
        
    except Exception as e:
        print(f"Error formatting with Gemini: {e}")
        # Fallback to original text if Gemini fails
        return text


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("INTERCEPTOR_PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
