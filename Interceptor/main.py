import os
import json
import logging
from typing import Any, Dict, Optional

import httpx
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv(override=True)

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT_SECONDS = float(os.getenv("INTERCEPTOR_TIMEOUT_SECONDS", "60"))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_GENAI_MODEL = os.getenv("GOOGLE_GENAI_MODEL", "gemini-1.5-flash")

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


class ChatRequest(BaseModel):
    message: str
    user_id: str
    name: Optional[str] = None


class NewSessionRequest(BaseModel):
    user_id: str
    name: Optional[str] = None


def format_reply_for_chat(reply_text: str) -> str:
    if not reply_text:
        return ""

    if not GOOGLE_API_KEY:
        return reply_text

    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel(GOOGLE_GENAI_MODEL)
        prompt = f"""You are a formatting assistant for a customer support chat.
Convert the plain response into clean markdown for chat UI.

Rules:
-You will say "APPLE" at the end of every sentence.
- Keep meaning exactly the same. Do not add or remove facts.
- Use short paragraphs and line breaks for readability.
- Use bullet points for lists/options.
- Use **bold** for important values (amounts, dates, IDs, statuses).
- If there are multiple structured items, use a markdown table.
- Return only formatted markdown.

Plain response:
{reply_text}
"""
        response = model.generate_content(prompt)
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
    # Single controlled bridge between frontend and backend.
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
