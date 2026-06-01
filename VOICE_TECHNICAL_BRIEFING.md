# Voice Agent — Technical Briefing Document

## 1. System Overview

This is a **real-time conversational voice assistant** for telecom customer support. Users speak naturally via browser, the system listens, fetches real customer data (bills, tickets, outages), and **speaks back** with accurate answers.

**Capabilities:** Billing inquiries, support tickets, outage checks, roaming management, wallet/credits.
**Strict Scope:** Refuses non-telecom requests (no weather, jokes, general knowledge).

---

## 2. Architecture — Dynamic Prompt Injection Pattern

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────┐     ┌──────────────┐
│   Frontend   │────►│   Interceptor    │────►│   Backend   │────►│   Supabase   │
│  (React/Vite)│     │   (FastAPI)      │     │  (FastAPI)  │     │  (Postgres)  │
│   Port 5173  │     │   Port 8001      │     │  Port 8000  │     │    Cloud     │
└──────────────┘     └──────────────────┘     └─────────────┘     └──────────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │  OpenAI Realtime │
                     │   (Voice/WebRTC) │
                     └──────────────────┘
```

### Why 3 Services?

| Reason | Explanation |
|--------|-------------|
| **Security** | Browser never has API keys. Ephemeral tokens expire in ~60s. |
| **Separation of Concerns** | Backend is pure AI agent. Interceptor handles channel adaptation. |
| **Reusability** | Same Backend serves chat UI and voice. Interceptor adapts response format. |
| **Dynamic Prompt Injection** | Channel-specific context injected at middleware layer. |

---

## 3. Dynamic Prompt Injection — Core Innovation

### 3.1 The Problem

Different channels require different response styles from the same AI backend:

| Channel | Response Requirements |
|---------|----------------------|
| Web Chat | Detailed, markdown formatted, tables, bullet points |
| Voice | Brief (1-3 sentences), conversational, TTS-friendly |
| SMS | Ultra-brief (160 chars), plain text |
| WhatsApp | Brief, basic formatting, emojis allowed |

### 3.2 The Solution

Instead of building separate backends, we **inject channel-specific instructions directly into the user's message** at the middleware layer.

```
Traditional: User Message → Backend → Response
Our Pattern: User Message → Interceptor (Inject Context) → Enhanced Message → Backend → Response → Interceptor (Format) → Formatted Response
```

### 3.3 Technical Implementation

**Context Injection Module** (`Interceptor/utils/context_injection.py`):

```python
def inject_chat_context(message: str, user_id: str, name: str = None) -> str:
    """
    Transforms: "What's my balance?"
    Into: "[USER_ID: x] [USER_NAME: y] [CONTEXT: ...] User message: What's my balance?"
    """
    name_context = f"[USER_NAME: {name}] " if name else ""
    context_prefix = f"""[USER_ID: {user_id}] {name_context}[CONTEXT: User is authenticated via web interface. User ID: {user_id} is verified. 
You can proceed directly with their request without asking for identification.
User expects detailed, formatted responses with all relevant information.]

User message: """
    return context_prefix + message
```

**Key Insight:** The LLM doesn't care where instructions come from. By prepending context to the user message, we "reprogram" the agent's behavior per-request without modifying the backend.

### 3.4 Injection Format

```
[USER_ID: test@email.com] [USER_NAME: John] [CONTEXT: User is authenticated via web interface...
User expects detailed, formatted responses with all relevant information.]

User message: What's my balance?
```

- `[USER_ID: x]` — Backend tools extract this for database queries
- `[USER_NAME: x]` — Personalization
- `[CONTEXT: ...]` — Channel-specific behavior instructions
- `User message:` — Clear delimiter separating context from actual query

---

## 4. Module Architecture

### 4.1 Interceptor Structure

```
Interceptor/
├── main.py                 # FastAPI entry point, routes
├── utils/
│   ├── config.py           # Environment variables (API keys, URLs)
│   ├── context_injection.py # Dynamic prompt injection functions
│   ├── formatters.py       # Response formatting (Gemini AI)
│   ├── helpers.py          # Utility functions
│   ├── models.py           # Pydantic request/response schemas
│   └── tools.py            # OpenAI voice tool definitions
└── services/
    ├── backend_proxy.py    # HTTP client to Backend
    └── voice_auth.py       # Voice authentication state management
```

### 4.2 Module Responsibilities

| Module | Layer | Responsibility |
|--------|-------|---------------|
| `config.py` | Utils | Singleton config class, loads env vars |
| `context_injection.py` | Utils | Builds channel-specific prompts |
| `formatters.py` | Utils | Transforms responses per channel (uses Gemini) |
| `helpers.py` | Utils | `normalize_to_text()`, `load_system_instructions()` |
| `models.py` | Utils | Pydantic schemas for API validation |
| `tools.py` | Utils | OpenAI Realtime tool definitions |
| `backend_proxy.py` | Services | Async HTTP client to Backend |
| `voice_auth.py` | Services | In-memory auth state per voice session |

---

## 5. Data Flow — Chat Channel

```
Frontend                    Interceptor                      Backend
   │                            │                               │
   │  POST /chat                │                               │
   │  {message, user_id, name}  │                               │
   │───────────────────────────►│                               │
   │                            │                               │
   │                    inject_chat_context()                   │
   │                    "[USER_ID: x] [CONTEXT: ...]            │
   │                     User message: ..."                     │
   │                            │                               │
   │                            │  POST /chat                   │
   │                            │  {enhanced_message}           │
   │                            │──────────────────────────────►│
   │                            │                               │
   │                            │                      Google ADK Agent
   │                            │                      processes message
   │                            │                               │
   │                            │  {reply: "Your balance..."}   │
   │                            │◄──────────────────────────────│
   │                            │                               │
   │                    format_reply_for_chat()                 │
   │                    (Gemini adds markdown)                  │
   │                            │                               │
   │  {reply: "**Balance**: $150", raw_reply: "..."}           │
   │◄───────────────────────────│                               │
```

**Code Flow:**

```python
@app.post("/chat")
async def chat(req: ChatRequest):
    # 1. Inject context (O(n) string concat)
    enhanced_message = inject_chat_context(req.message, req.user_id, req.name)
    
    # 2. Forward to Backend
    backend_response = await backend_proxy.chat(enhanced_message, req.user_id)
    
    # 3. Format response using Gemini AI
    formatted_reply = format_reply_for_chat(backend_response["reply"])
    
    return {"reply": formatted_reply, "raw_reply": backend_response["reply"]}
```

---

## 6. Data Flow — Voice Channel

### 6.1 Session Initialization

```python
@app.get("/voice/token")
async def get_voice_token(user_id: str):
    # 1. Load system prompt from eleven_labs_prompts/system.md
    # 2. Call OpenAI to create realtime session with:
    #    - System instructions (179 lines of voice behavior rules)
    #    - Tool definitions (validate_user, forward_to_backend)
    #    - Voice config (coral voice, server VAD)
    # 3. Return ephemeral token to browser
    # 4. Reset auth state for this user
```

### 6.2 Voice Flow Diagram

```
User          OpenAI Realtime        Interceptor           Backend
 │                  │                     │                    │
 │  Audio stream    │                     │                    │
 │─────────────────►│                     │                    │
 │                  │                     │                    │
 │          Transcription + Intent        │                    │
 │                  │                     │                    │
 │                  │  forward_to_backend │                    │
 │                  │  {message: "..."}   │                    │
 │                  │────────────────────►│                    │
 │                  │                     │                    │
 │                  │             inject_voice_context()       │
 │                  │             "[USER_ID: 42] [CONTEXT:     │
 │                  │              Voice call. Keep brief...]" │
 │                  │                     │                    │
 │                  │                     │  POST /chat        │
 │                  │                     │───────────────────►│
 │                  │                     │                    │
 │                  │                     │  {reply: "..."}    │
 │                  │                     │◄───────────────────│
 │                  │                     │                    │
 │                  │             format_reply_for_voice()     │
 │                  │             (Gemini: 1-2 sentences,      │
 │                  │              "dollar" not "$")           │
 │                  │                     │                    │
 │                  │  {response: "..."}  │                    │
 │                  │◄────────────────────│                    │
 │                  │                     │                    │
 │  TTS Audio       │                     │                    │
 │◄─────────────────│                     │                    │
```

### 6.3 Voice Authentication Flow

```python
# voice_auth.py - State management
class VoiceAuthService:
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self._auth_state: Dict[str, bool] = {}      # email -> authenticated
        self._customer_id: Dict[str, str] = {}      # email -> customer_id
    
    async def validate_user_id(self, spoken_user_id: str) -> tuple[bool, str, str]:
        # Query Supabase users_voice table
        response = self.supabase.table("users_voice")\
            .select("user_id")\
            .eq("user_id", spoken_user_id)\
            .execute()
        
        if response.data:
            return (True, response.data[0]['user_id'], "Account verified")
        return (False, None, "User not found")
```

**Why per-session auth state?**
- Voice session identified by email from Frontend login
- Backend needs numeric customer ID for database queries
- Interceptor bridges: validates spoken ID exists, then uses it for all Backend calls
- Prevents user from querying another user's data

---

## 7. Response Formatting Pipeline

```python
# formatters.py - Uses Gemini AI for intelligent formatting

def format_reply_for_chat(reply_text: str) -> str:
    """Transforms plain text to markdown for web UI"""
    prompt = f"""Convert to markdown:
    - Use **bold** for important values
    - Use bullet points for lists
    - Use tables for structured data
    Text: {reply_text}"""
    
    response = genai.Client().models.generate_content(
        model="gemini-1.5-flash", contents=prompt
    )
    return response.text

def format_reply_for_voice(reply_text: str) -> str:
    """Transforms to TTS-friendly text"""
    prompt = f"""Convert for text-to-speech:
    - Maximum 2 sentences
    - Say "dollar" not "$", "percent" not "%"
    - No markdown or special characters
    Text: {reply_text}"""
    
    response = genai.Client().models.generate_content(
        model="gemini-1.5-flash", contents=prompt
    )
    return response.text
```

---

## 8. Backend Multi-Agent System

```
                    ┌──────────────┐
                    │  Root Agent  │  ← Routes queries
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
        └──────────────┘      └───────────────┘
```

**Routing Logic:**
- *"What's my bill?"* → Billing Agent
- *"Is there an outage?"* → Support Agent
- *"My internet is down and I want a refund"* → Billing Agent (can call outage tools)
- *"What's 2+2?"* → Declined (not telecom-related)

---

## 9. Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Frontend | React + Vite | Fast dev, modern hooks |
| Voice | WebRTC (native browser) | Sub-100ms latency, built-in echo cancellation |
| STT | OpenAI Whisper-1 | Best transcription accuracy for numbers |
| Realtime LLM | GPT-4o Realtime Preview | Only model with WebRTC audio I/O |
| TTS | OpenAI Realtime (Coral voice) | Integrated with model |
| Interceptor | FastAPI (Python) | Async, fast HTTP proxying |
| Response Formatting | Google Gemini Flash | Fast, cheap text transformation |
| Backend Agents | Google ADK | Multi-agent routing, tool orchestration |
| Backend LLM | Gemini 3 Flash | Powers billing/support reasoning |
| Database | Supabase (PostgreSQL) | Hosted DB with Python SDK |

---

## 10. Security Model

| Layer | Protection |
|-------|-----------|
| **API Keys** | Never leave server. Browser gets ephemeral token (~60s lifespan). |
| **Authentication** | User must validate numeric ID before data queries. Auth state server-side. |
| **ID Isolation** | Interceptor maps email → validated customer ID. Backend only sees numeric ID. |
| **Tool Execution** | All tools execute server-side. Browser only forwards requests. |
| **Scope Restriction** | System prompt limits agent to telecom topics only. |

---

## 11. Latency Breakdown

| Phase | Latency | What's Happening |
|-------|---------|-----------------|
| Click mic → audio starts | ~1-2s | Token fetch + WebRTC handshake |
| User finishes speaking → model responds | ~1-3s | 1s silence detection + Whisper + LLM |
| Tool call (validate_user) | ~1-2s | Interceptor → Supabase → back |
| Tool call (forward_to_backend) | ~3-6s | Interceptor → Backend (agent + DB) → Gemini format |
| Model gets result → speaks | ~0.5-1s | LLM processes + TTS streams |

**Total for data query:** ~4-8 seconds. Filler phrases cover wait time.

---

## 12. Design Decisions & Trade-offs

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **Dynamic Prompt Injection** | Single backend serves all channels | Adds string processing overhead |
| **OpenAI Realtime API** | Single API for STT + LLM + TTS | Vendor lock-in, higher cost |
| **Interceptor middleware** | Keeps API keys server-side | One more hop of latency |
| **Gemini for formatting** | Backend responses too verbose for voice | ~0.5-1s latency, API cost |
| **In-memory auth state** | Simple, fast for MVP | Lost on restart, doesn't scale horizontally |
| **Two LLM providers** | OpenAI for realtime (only WebRTC option), Google for agents | Two APIs, two billing accounts |

---

## 13. Potential Questions & Answers

**Q: Why not use system prompts in the Backend?**
A: System prompts are static per session. Dynamic injection allows per-message customization based on channel, auth state, user preferences.

**Q: What's the latency overhead of injection?**
A: O(n) string concatenation (~0.1ms). Formatting uses Gemini (~200-500ms) but runs after response is ready.

**Q: How does Backend know to use USER_ID?**
A: Backend agent instructions tell it to extract `[USER_ID: x]` from messages for tool calls.

**Q: Why in-memory auth state for voice?**
A: Voice sessions are short-lived (minutes). In-memory is faster than DB. For production scale, use Redis.

**Q: What if Gemini formatting fails?**
A: Fallback returns raw text. All formatters have try/except with graceful degradation.

**Q: Can we add SMS/WhatsApp channels?**
A: Yes. Just create new injection functions in `context_injection.py` and new formatters. Backend unchanged.

**Q: How do we A/B test different prompts?**
A: Modify injection functions in Interceptor. No Backend deployment needed.
