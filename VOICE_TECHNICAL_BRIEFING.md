# Voice Agent — Technical Briefing Document

## 1. What Is This System?

This is a **real-time conversational voice assistant** for telecom customer support. A user opens the web app, clicks a microphone button, and speaks naturally — the system listens, understands, fetches real customer data (bills, tickets, outages), and **speaks back** with accurate answers. All in real-time, like a phone call.

It handles: billing inquiries, support tickets, outage checks, roaming management, wallet/credits — and **refuses** everything else (no weather, no jokes, no general knowledge).

---

## 2. High-Level Architecture — The 3-Service Design

We have **3 independently running services** + 2 external cloud APIs:

```
┌─────────────────────────────────────────────────────────────────────┐
│  USER'S BROWSER (Frontend - React, Port 5173)                      │
│                                                                     │
│  ┌──────────────┐     ┌──────────────────────────────────────────┐  │
│  │ VoiceInterface│────▶│ OpenAI Realtime API (WebRTC, Cloud)     │  │
│  │  Component    │◀────│  - Speech-to-Text (Whisper)             │  │
│  │              │     │  - LLM Reasoning (GPT-4o Realtime)      │  │
│  │  Captures mic│     │  - Text-to-Speech (Alloy voice)         │  │
│  │  Plays audio │     │  - Voice Activity Detection (Server VAD)│  │
│  └──────┬───────┘     └──────────────────────────────────────────┘  │
│         │ HTTP calls for tool results                               │
└─────────┼───────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  INTERCEPTOR (FastAPI Python, Port 8001)                            │
│                                                                     │
│  - Generates ephemeral tokens for secure browser-to-OpenAI access   │
│  - Handles tool calls: validate_user, forward_to_backend            │
│  - Manages per-session authentication state                         │
│  - Reformats responses for spoken delivery using Gemini             │
│  - Connects to Supabase for user validation                        │
└─────────┬───────────────────────────────────────────────────────────┘
          │ HTTP proxy
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BACKEND (FastAPI + Google ADK, Port 8000)                          │
│                                                                     │
│  - Multi-agent AI system (Root Agent → Billing Agent + Support Agent)│
│  - Each agent has specific tools to query Supabase                  │
│  - Maintains conversation history per session (in-memory)           │
│  - Returns natural language answers                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Why 3 services instead of 1?

| Reason | Explanation |
|--------|-------------|
| **Security** | The Interceptor acts as a gateway — the browser never has the OpenAI API key or the backend URL directly. The ephemeral token expires quickly. |
| **Separation of concerns** | The Backend is purely an AI agent system — it doesn't know about voice, WebRTC, or formatting. The Interceptor handles all voice-specific logic. |
| **Reusability** | The same Backend serves both the text chat UI and the voice interface. The Interceptor adapts the response format depending on the channel. |
| **Security of tool execution** | Tool calls from the AI model are executed server-side (Interceptor), never directly in the browser. |

---

## 3. The Complete Voice Flow — Step by Step

### STEP 1: Session Initialization (User clicks the mic)

**What happens:**
1. Frontend sends `GET /voice/token?user_id=user@email.com` to the Interceptor
2. Interceptor makes a server-to-server call to OpenAI's REST API: `POST https://api.openai.com/v1/realtime/sessions`
3. This call includes the **entire configuration** for the voice session:
   - **Model**: `gpt-4o-realtime-preview-2025-06-03` (the realtime-capable model)
   - **System prompt**: A 179-line instruction set defining personality, scope, authentication rules, filler behavior, response formatting
   - **Tool definitions**: Two tools (`validate_user`, `forward_to_backend`) with JSON schemas
   - **Voice**: `alloy` (OpenAI's predefined voice)
   - **VAD config**: Server-side Voice Activity Detection with 0.5 threshold, 300ms prefix padding, 1000ms silence duration
   - **Transcription**: Whisper-1 model for input audio transcription
4. OpenAI returns a **short-lived ephemeral token** (~60 seconds lifespan)
5. Interceptor resets authentication state for this user and returns the token to the Frontend

**Why ephemeral tokens?**
- The real OpenAI API key (`sk-proj-...`) never leaves the server
- The ephemeral token can only be used for the specific session configuration defined in step 3
- Even if intercepted, it expires within ~60 seconds
- The browser gets *just enough* permission to stream audio, nothing more

### STEP 2: WebRTC Connection (Browser ↔ OpenAI)

**What happens:**
1. Browser requests microphone access: `navigator.mediaDevices.getUserMedia({ audio: true })`
2. Creates an `RTCPeerConnection` — this is the standard WebRTC protocol used by Zoom, Google Meet, etc.
3. Adds the microphone audio track to the peer connection
4. Creates a **data channel** named `oai-events` — this is a side channel for sending/receiving JSON events alongside the audio stream
5. Creates an SDP offer (Session Description Protocol — describes what audio codecs the browser supports)
6. Sends the SDP offer to `https://api.openai.com/v1/realtime?model=...` with the ephemeral token
7. OpenAI responds with an SDP answer — WebRTC is now connected

**Why WebRTC instead of WebSockets?**
- WebRTC is a peer-to-peer protocol optimized for **real-time audio** — sub-100ms latency
- It handles audio codecs, echo cancellation, jitter buffers automatically
- WebSockets would require manual audio chunking and have higher latency
- The data channel gives us a reliable event stream alongside the audio (no separate connection needed)

### STEP 3: Initial Greeting

Once the data channel opens, the Frontend immediately injects a hidden text message:
```
"Hello! Please greet me and ask for my User ID."
```
This triggers the model to speak a greeting like: *"Hello! How can I help with your telecom account today? Can I get your User ID to look up your account?"*

**Why do this?** Without it, the model would wait silently until the user speaks first — awkward for a support call.

### STEP 4: Continuous Real-Time Conversation

This is where the magic happens. The entire loop runs in real-time:

```
[User speaks] → [Audio streams via WebRTC to OpenAI]
                          │
                  Server-side VAD detects speech start
                  Server-side VAD detects 1 second of silence → speech ended
                          │
                  Whisper-1 transcribes the audio to text
                          │
                  GPT-4o Realtime processes the text with full conversation context
                          │
              ┌───────────┴───────────┐
              │                       │
      Simple response            Needs data from backend
      (greeting, refusal)        (billing, support query)
              │                       │
      Model generates text       Model calls a tool
      + streams TTS audio        (validate_user or forward_to_backend)
      back via WebRTC                 │
              │                  Frontend receives tool call via data channel
              │                  Frontend POSTs to Interceptor /voice/tool-call
              │                  Interceptor executes the tool
              │                  Returns result to Frontend
              │                  Frontend sends result back to OpenAI via data channel
              │                  Model uses result to generate voice response
              │                       │
              └───────────┬───────────┘
                          │
                  [User hears the response via WebRTC audio]
```

### STEP 5: Authentication Flow (validate_user tool)

**This happens before any data query is allowed.**

1. User says: *"My ID is forty two"*
2. OpenAI's model interprets this and calls: `validate_user(user_id="42")`
   - The system prompt has explicit rules for number interpretation:
     - "forty two" → "42"
     - "one zero one" → "101"
     - Only numeric IDs accepted
3. The model first says a filler: *"Let me verify that ID..."* (required by system prompt to avoid awkward silence)
4. Frontend catches the `response.function_call_arguments.done` event
5. Frontend POSTs to Interceptor: `POST /voice/tool-call { tool_name: "validate_user", arguments: { user_id: "42" }, user_id: "user@email.com", call_id: "call_xxx" }`
6. Interceptor normalizes the ID (strips non-alphanumeric chars)
7. Queries Supabase: `SELECT id FROM users_voice WHERE id = 42`
8. If found:
   - Stores auth state in memory: `_voice_auth_state["user@email.com"] = True`
   - Maps email → customer ID: `_voice_customer_id["user@email.com"] = "42"`
   - Returns success message
9. If not found: Returns failure message suggesting digit-by-digit input
10. Frontend sends the result back to OpenAI via data channel
11. Model speaks: *"Thanks! I've confirmed your account. How can I help you today?"*

**Why is there a per-session auth state?**
- The voice session is identified by the user's email from the Frontend login
- But the Backend needs the *numeric customer ID* to query billing/support data
- The Interceptor bridges this: it validates the spoken ID exists in the database, then uses it for all subsequent Backend calls
- This prevents a user from querying another user's data

### STEP 6: Data Query Flow (forward_to_backend tool)

**This is the main workhorse — all billing/support queries go through this.**

1. User asks: *"What's my bill this month?"*
2. Model says filler: *"Sure, let me check that for you..."*
3. Model calls: `forward_to_backend(message="What's my bill this month?")`
4. Frontend POSTs to Interceptor
5. Interceptor checks:
   - Is user authenticated? (checks `_voice_auth_state`) — if not, rejects
   - Swaps user_id from email → validated customer ID (e.g., "42")
6. Interceptor proxies to Backend: `POST http://localhost:8000/chat { message: "What's my bill this month?", user_id: "42" }`
7. **Backend processing** (Google ADK multi-agent system):
   - Prepends context: `[USER_ID: 42] What's my bill this month?`
   - **Root Agent** (Gemini model) reads the message and decides routing:
     - This is a billing question → delegates to **Billing Agent**
   - **Billing Agent** has tools connected to Supabase. It calls:
     - `get_user_invoices(user_id="42")` → queries `invoices` table
     - Optionally `get_user_invoices_breakdown(invoice_id="INV-001")` for details
   - Billing Agent composes a natural language response using the data
   - Response flows back through the Runner to the Backend API
8. Backend returns: `{ "reply": "Looking at your January invoice, the total is $1,400. That's about $300 higher than last month, mainly due to roaming charges in the Delhi region..." }`
9. **Interceptor reformats for voice** using Gemini Flash:
   - Input: The verbose backend response
   - Gemini prompt: "Convert to 1-2 short spoken sentences. Say 'dollar' not '$'. Numbers spoken naturally."
   - Output: *"Your January bill is fourteen hundred dollars. It's three hundred higher than last month due to roaming."*
10. Returns to Frontend → Frontend sends to OpenAI → Model speaks it via TTS

**Why reformat with Gemini?**
- The Backend's response is designed for text chat — it can be verbose, have formatting, symbols
- Voice needs ultra-brief, symbol-free, naturally spoken text
- Gemini Flash is fast and cheap enough for real-time reformatting

### STEP 7: Silence Handling

If the user stops talking for 20 seconds:
1. Frontend timer fires
2. Injects a system message: *"The user has been silent. Gently check in."*
3. Model responds: *"Still there? No rush."*
4. After 2 such nudges, the system goes quiet and waits indefinitely

---

## 4. The Multi-Agent Backend — How Routing Works

The Backend uses **Google Agent Development Kit (ADK)** with 3 agents:

```
                    ┌──────────────┐
                    │  Root Agent  │  ← First contact, routes queries
                    │  (Gemini)    │
                    └──────┬───────┘
                           │
                ┌──────────┴──────────┐
                │                     │
        ┌───────▼──────┐      ┌──────▼────────┐
        │ Billing Agent│      │ Support Agent  │
        │              │      │               │
        │ Tools:       │      │ Tools:        │
        │ - Invoices   │      │ - Tickets     │
        │ - Payments   │      │ - Outages     │
        │ - Roaming    │      │ - Knowledge   │
        │ - Wallet     │      │ - Memory      │
        │ - Breakdown  │      │               │
        │ - Knowledge  │      │               │
        │ - Memory     │      │               │
        └──────────────┘      └───────────────┘
```

**Root Agent decides routing:**
- *"What's my bill?"* → Billing Agent
- *"Is there an outage?"* → Support Agent
- *"My internet is down and I want a refund"* → Billing Agent (it can call outage tools too)
- *"What's 2+2?"* → Declined (not telecom-related)

**Each agent has its own Supabase tools:**

| Tool | Table | What it does |
|------|-------|-------------|
| `get_user_invoices` | `invoices` | Get all invoices for a user |
| `get_user_invoices_breakdown` | `invoice_breakdown` | Line-item details for an invoice |
| `get_payment_methods` | `payment_methods` | How the user pays |
| `check_roaming_status` | `roaming` | Is roaming enabled? |
| `update_roaming_status_monthwise` | `roaming` | Disable roaming for a month |
| `check_wallet_amount_settlement` | `wallet_amount` | Check wallet credits |
| `create_wallet_entry` | `wallet_amount` | Issue a new credit/refund |
| `update_wallet_amount` | `wallet_amount` | Update existing credit |
| `get_open_tickets` | `support_tickets` | Open support tickets |
| `check_outage` | `outages` | Check outages by area |
| `search_company_knowledge` | (knowledge base) | FAQ/policy search |
| `get_user_memory` / `update_user_memory` | (memory store) | Persist context across calls |

---

## 5. Security Model

| Layer | Protection |
|-------|-----------|
| **API Key** | OpenAI API key never leaves the Interceptor server. Browser only gets an ephemeral token (~60s lifespan). |
| **Authentication** | User must validate their numeric ID before any data queries are allowed. Auth state tracked server-side per session. |
| **ID Isolation** | Interceptor maps login email → validated customer ID. Backend only receives the numeric ID — no PII leakage. |
| **Tool execution** | All tools execute server-side on the Interceptor/Backend. The browser only forwards requests, never executes DB queries. |
| **Scope restriction** | System prompt strictly limits the agent to telecom topics. Off-topic requests are declined. |
| **CORS** | All services allow `*` origins (development mode — should be restricted in production). |

---

## 6. Technology Stack Summary

| Component | Technology | Why This Choice |
|-----------|-----------|-----------------|
| Frontend | React + Vite | Fast dev server, modern React with hooks |
| Voice capture | WebRTC (native browser API) | Sub-100ms latency, built-in echo cancellation |
| Speech-to-Text | OpenAI Whisper-1 | Best-in-class transcription accuracy, especially for numbers |
| LLM (realtime) | GPT-4o Realtime Preview | Only model supporting real-time audio I/O via WebRTC |
| Text-to-Speech | OpenAI Realtime (Alloy voice) | Integrated with the model — no separate TTS step needed |
| Voice Activity Detection | OpenAI Server VAD | Detects when user starts/stops speaking automatically |
| Interceptor | FastAPI (Python) | Async, fast, perfect for proxying HTTP calls |
| Response formatting | Google Gemini Flash | Fast, cheap reformatting of verbose text for voice output |
| Backend agents | Google ADK (Agent Development Kit) | Multi-agent routing, tool orchestration, session memory |
| Backend LLM | Gemini 3 Flash Preview | Powers the billing/support agents' reasoning |
| Database | Supabase (PostgreSQL) | Hosted DB with real-time API, easy Python/JS SDKs |
| User validation | Supabase `users_voice` table | Simple ID lookup for voice authentication |

---

## 7. Latency Breakdown — What the User Experiences

| Phase | Estimated Latency | What's Happening |
|-------|-------------------|-----------------|
| Click mic → audio starts | ~1-2 seconds | Token fetch + WebRTC handshake + mic permission |
| User finishes speaking → model starts responding | ~1-3 seconds | 1s silence detection + Whisper transcription + LLM processing |
| Tool call round-trip (validate_user) | ~1-2 seconds | Frontend → Interceptor → Supabase → back |
| Tool call round-trip (forward_to_backend) | ~3-6 seconds | Frontend → Interceptor → Backend (agent reasoning + Supabase queries) → Gemini reformat → back |
| Model gets tool result → starts speaking | ~0.5-1 second | LLM processes result + TTS begins streaming |

**Total for a data query:** User speaks → ~4-8 seconds → hears the answer. The filler phrases ("Let me check that...") cover most of this wait time.

---

## 8. Key Design Decisions & Trade-offs

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **Using OpenAI Realtime API instead of separate STT + LLM + TTS** | Single API handles all three, much lower latency, native function calling | Vendor lock-in to OpenAI, higher cost per session |
| **Interceptor as a middle layer** | Keeps API keys server-side, enables voice-specific formatting | Adds one more hop of latency |
| **Gemini for response reformatting** | Backend responses are too verbose for voice; need 1-2 sentence summaries | Adds ~0.5-1s latency, additional API cost |
| **Server-side VAD** | Automatic speech boundary detection without Frontend logic | Less control than push-to-talk; occasional false triggers |
| **In-memory auth state** | Simple, fast for MVP | Lost on server restart; doesn't scale horizontally |
| **Two separate LLM providers** | OpenAI for realtime voice (only provider with WebRTC), Google for backend agents (ADK ecosystem) | Managing two provider APIs, two billing accounts |
| **Ephemeral token pattern** | Industry standard for securing client-side access to cloud APIs | Token expiry means reconnection needed for long sessions |
