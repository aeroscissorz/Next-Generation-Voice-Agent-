from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from voice_agents_adk.agent import root_agent

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

APP_NAME = "voice_agents_adk"

session_service = InMemorySessionService()

runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)


class ChatRequest(BaseModel):
    message: str
    user_id: str

# ROUTES 
@app.get("/")
def health():
    return {"status": "ok"}
@app.post("/chat")
async def chat(req: ChatRequest):
    session_id = f"{req.user_id}-default"

    content = types.Content(
        role="user",
        parts=[types.Part(text=req.message)]
    )

    async def run_agent():
        final_text = ""
        async for event in runner.run_async(
            user_id=req.user_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response() and event.content:
                final_text = event.content.parts[0].text
        return final_text

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

    return {"reply": reply}
