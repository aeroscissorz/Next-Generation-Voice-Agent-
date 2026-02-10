# Interceptor Service

This service is the only bridge between frontend and backend for chat flows.

## Responsibilities
- Accept requests from frontend.
- Forward `/chat` and `/new-session` to backend.
- Format backend `/chat` replies into chat-friendly markdown using Gemini.
- Return formatted responses to frontend.

## Local Setup
1. Create and activate a Python virtual environment.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set `BACKEND_URL`.
   Also set `GOOGLE_API_KEY` for Gemini formatting.
4. Run:
   `uvicorn main:app --host 0.0.0.0 --port 8001 --reload`

## Frontend
Set:
`VITE_INTERCEPTOR_URL=http://127.0.0.1:8001`

Frontend requests should target interceptor, not backend.
