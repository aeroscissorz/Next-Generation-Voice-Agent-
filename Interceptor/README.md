# Interceptor Service

A middleware layer that sits between the Frontend and Backend, handling channel-specific message processing and formatting.

## Architecture

```
Frontend (Port 5173)
    ↓
Interceptor Service (Port 8001) ← You are here
    ↓
Backend Agent (Port 8000)
```

## Purpose

The interceptor service:
1. Receives messages from the frontend with channel information (chat, voice, telephonic)
2. Forwards messages to the backend agent (without channel info)
3. Receives raw responses from the backend
4. Formats responses based on the channel type
5. Returns formatted responses to the frontend

## Channel Processing

### Chat Channel
- Formats responses using Gemini AI
- Converts plain text into structured markdown
- Adds formatting for better readability (bold, bullets, tables)

### Voice/Telephonic Channels
- Returns raw response without formatting
- Handled by ElevenLabs Widget on the frontend

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env`:
```
INTERCEPTOR_PORT=8001
BACKEND_URL=http://localhost:8000
GOOGLE_API_KEY=your_google_api_key
GOOGLE_GENAI_MODEL=gemini-2.0-flash-exp
```

3. Run the service:
```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

## API Endpoints

### `GET /`
Health check endpoint

### `GET /health`
Detailed health status

### `POST /chat`
Process chat message through interceptor

**Request:**
```json
{
  "message": "What's my balance?",
  "user_id": "user@example.com",
  "name": "John Doe",
  "channel": "chat"
}
```

**Response:**
```json
{
  "reply": "**Your current balance is $150.00**",
  "user_name": "John Doe",
  "channel": "chat",
  "formatted": true
}
```

### `POST /new-session`
Create new session (forwarded to backend)

**Request:**
```json
{
  "user_id": "user@example.com",
  "name": "John Doe"
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `INTERCEPTOR_PORT` | Port for interceptor service | `8001` |
| `BACKEND_URL` | Backend service URL | `http://localhost:8000` |
| `GOOGLE_API_KEY` | Google API key for Gemini | Required |
| `GOOGLE_GENAI_MODEL` | Gemini model name | `gemini-2.0-flash-exp` |

## Development

The interceptor service is stateless and can be scaled horizontally. It maintains no session state and simply acts as a formatting middleware.
