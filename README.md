# Chat Interceptor Service

## Overview

The Chat Interceptor is a middleware service that sits between the frontend and the backend.

Its primary responsibility is to:

- Forward user chat messages to the backend instantly (for now, but we can add other processing steps too)
- Format backend responses using Google Gemini
- Normalize inconsistent backend responses
- Provide structured logging
- Handle CORS safely
- Serve as a controlled gateway for future enhancements

This service ensures the frontend receives consistently formatted markdown responses without modifying backend business logic.

---

## Architecture

Frontend → Interceptor → Backend (and vice versa)

### Request Lifecycle

1. Frontend sends `POST /chat`
2. Interceptor validates request using Pydantic models
3. Request is forwarded asynchronously to backend using `httpx.AsyncClient`
4. Backend response is parsed and normalized
5. If `GOOGLE_API_KEY` is configured:
   - Response is reformatted using Gemini (`google-generativeai`)
6. Final response is returned to frontend with:
   - `reply` (formatted markdown)
   - `raw_reply` (original backend text)

The user input is NOT modified before forwarding.

---
### ChatRequest

```json
{
  "message": "string",
  "user_id": "string",
  "name": "optional"
}
