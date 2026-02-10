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

### Flow

1. Frontend sends `/chat` request
2. Interceptor immediately forwards request to backend
3. Backend returns raw response
4. Interceptor:
   - Normalizes response
   - Formats reply using Gemini
5. Interceptor returns:
   - `reply` (formatted markdown)
   - `raw_reply` (original backend text)

The user input is NOT modified before forwarding.

---

## Features

- Async proxy forwarding using `httpx`
- Output formatting using `google-generativeai`
- Configurable backend URL
- Configurable model selection
- Timeout protection
- Error propagation from backend
- Structured logging
- CORS enabled



