# KT Script: Headless Implementation & Dynamic Prompt Injection

> **Format**: Screen-share walkthrough in VS Code. Open each file as you narrate.
> **Duration**: ~25-30 minutes
> **Audience**: Client engineering team

---

## 1. Architecture Overview (2 min)

**Open**: `Interceptor/main.py` — read the docstring at the top (lines 1-40)

**Talk track**:
> "The system has three layers. The Frontend is a React app with voice (WebRTC) and chat. The Interceptor is a FastAPI middleware — this is the brain of the headless architecture. The Backend is a Google ADK agent running Gemini with Supabase tools.
>
> The key idea: the Interceptor sits between the user and the AI agent. It decides *how* to handle every request — sometimes it skips the agent entirely."

**Draw this on screen or point to the ASCII diagram in the docstring**:
```
Frontend ──► Interceptor ──► Backend (Gemini Agent)
                │
                ├─ Context injection (dynamic prompt injection)
                ├─ Fast-path (skip agent loop entirely)
                └─ Voice (OpenAI Realtime API)
```

---

## 2. Dynamic Prompt Injection — Chat Channel (5 min)

**Open**: `Interceptor/utils/context_injection.py`

**Talk track**:
> "This is the core of dynamic prompt injection. Every message gets context prepended *before* it reaches the AI agent."

**Highlight `inject_chat_context()` (line ~30)**:
> "For chat, we inject:
> - `[USER_ID: 42]` — the authenticated user ID so the agent never asks for it
> - `[USER_NAME: John]` — for personalization
> - `[CONTEXT: Web chat interface]` — tells the agent which channel, so it knows to use markdown tables, bold formatting, etc.
> - Formatting rules — date formats, payment flow structure, overdue bill presentation
>
> The agent's instruction prompt is trained to parse these `[CONTEXT]` blocks and adjust behavior. Chat gets rich markdown. Voice gets 1-3 sentences."

**Highlight `inject_voice_context()` (line ~85)**:
> "Voice injection is much lighter — just user ID, auth status, and 'keep it brief'. The voice model (OpenAI Realtime) handles the conversational tone via its own system prompt."

**Now open**: `Interceptor/main.py` — scroll to the `/chat` endpoint (around line 163)

**Talk track**:
> "Here's where injection happens in the flow. Line 1: `inject_chat_context()` wraps the raw message. Line 2: the enhanced message goes to the Backend. The Backend agent sees `[USER_ID: 42] [CONTEXT: Web chat interface...] User message: show my invoices` — it never sees the raw message."

---

## 3. Dynamic Prompt Injection — Agent Instructions (5 min)

**Open**: `Backend/instructions.py`

**Talk track**:
> "This is the unified instruction prompt — the agent's 'brain'. It's a single massive prompt that covers all business logic."

**Highlight key sections**:

1. **Response Length block** (top):
> "See how it says 'Check the [CONTEXT] in the user message'? This is where the injected context gets consumed. If CONTEXT says 'Voice call', the agent limits to 1-3 sentences. If 'Web chat interface', it goes full markdown."

2. **User Identification block**:
> "It says 'The USER_ID is provided in the message context. Use it directly.' — this is why we inject `[USER_ID: 42]`. The agent never asks the user to confirm their ID."

3. **Outage Refund Flow** (scroll down):
> "This is a multi-step decision tree baked into the prompt. Steps 1-7 with explicit YES/NO/AMBIGUOUS handling. The agent follows this like a flowchart. This is how we get deterministic business logic from an LLM."

**Open**: `Backend/agent.py`

**Talk track**:
> "The agent definition is simple — it's an ADK `LlmAgent` with the instruction prompt and a list of tool functions. ADK handles the loop: send message → Gemini reasons → calls tools → feeds results back → Gemini responds. The `Runner` in `main.py` orchestrates this."

---

## 4. Headless Implementation — The Fast Path (5 min)

**Open**: `Interceptor/utils/intent_detector.py`

**Talk track**:
> "This is the headless magic. Before any message hits the AI agent, the Interceptor pattern-matches it against known intents using regex."

**Walk through the priority order**:
1. **Follow-up blocklist** (line ~35): `"yes"`, `"no"`, `"sure"` → skip fast-path, needs conversation context
2. **Complaints/sentiment** (line ~50): emotional words → skip, needs full agent empathy
3. **Policy questions** (line ~55): → `knowledge_search` fast-path (RAG)
4. **Outage reports** (line ~65): → `outage_check` compound fast-path
5. **Complex flows** (line ~75): refunds, plan changes → skip, needs multi-step agent
6. **Bill explanation** (line ~80): → `bill_explain` compound fast-path
7. **Simple intents** (line ~100): `"show my invoices"` → `get_user_invoices` single query

> "If it matches, we get back a tuple: `(tool_name, tool_args)`. If not, `None` — full agent loop."

**Open**: `Interceptor/services/tool_executor.py`

**Talk track**:
> "When intent detection matches, the ToolExecutor fetches data directly from Supabase — no LLM involved. Look at `_dispatch()` (line ~120)."

**Highlight examples**:
- **Simple**: `get_user_invoices` — single table query + eager breakdown prefetch
- **Compound**: `bill_explain` — invoices + breakdowns + roaming in one shot
- **RAG**: `knowledge_search` — OpenAI embedding → pgvector similarity search → keyword fallback

> "The result goes to Backend `/chat/fast` — a single Gemini call just to format the data into natural language. No agent loop, no tool calling. Total latency: 0.5-1 second vs 3-8 seconds."

**Open**: `Backend/main.py` — scroll to `/chat/fast` endpoint (near the bottom)

**Talk track**:
> "Here's the fast-path endpoint. It takes the pre-fetched `tool_data`, injects it into a simple formatting prompt (`FAST_FORMAT_PROMPT`), and makes one `generate_content` call. If Gemini 503s, it retries 3 times with backoff. If it still fails, it returns `fast_path_error: true` so the Interceptor can fall back to the full agent loop."

---

## 5. Headless Implementation — Voice Channel (5 min)

**Open**: `Interceptor/main.py` — scroll to `/voice/token` endpoint

**Talk track**:
> "Voice is fully headless — no traditional UI flow. The Frontend gets an ephemeral token from OpenAI Realtime API via this endpoint. The token configures:
> - Model: `gpt-4o-realtime-preview`
> - Voice: `coral` (warm female)
> - System instructions: loaded from `eleven_labs_prompts/system.md`
> - Tools: `validate_user` and `forward_to_backend`
> - VAD: server-side voice activity detection with tuned thresholds"

**Open**: `Interceptor/utils/tools.py`

> "The Realtime model only has two tools. `validate_user` authenticates the caller. `forward_to_backend` sends their query to our Gemini agent. Everything else is handled by the Backend."

**Open**: `Frontend/src/components/VoiceInterface.jsx` — scroll to `handleRealtimeEvent` (around line 200)

**Talk track**:
> "The Frontend connects via WebRTC. When OpenAI's model calls a tool, the `response.function_call_arguments.done` event fires. The Frontend intercepts it, POSTs to `/voice/tool-call` on the Interceptor, gets the result, and sends it back to the Realtime model via the data channel."

**Highlight the filler logic** (around line 280):
> "While the tool call is in flight, we have a filler system. After 3 seconds, we inject a `[System: ...]` prompt telling the model to narrate what it's doing — 'Let me pull that up for you...' After 8 more seconds, a follow-up filler. This keeps the voice experience natural during backend latency."

**Open**: `Frontend/src/components/voiceFillerHelpers.js`

> "These are the filler prompt builders. `buildFillerPrompt()` fires first — continues the agent's initial narration. `buildFollowUpPrompt()` fires if the tool call is still running. Max 2 follow-ups."

**Open**: `Interceptor/main.py` — scroll to `_handle_forward_to_backend` (near the bottom)

> "When `forward_to_backend` is called: we check auth, inject voice context (`inject_voice_context`), proxy to Backend `/chat`, then format the response for voice — strip markdown, limit to 3 sentences, replace symbols with words (₹ → 'rupees'). The Realtime model speaks this back."

---

## 6. Cache Warming & Prefetch (2 min)

**Open**: `Interceptor/main.py` — scroll to `/new-session` and `_prefetch_user`

**Talk track**:
> "On every new session or login, we kick off a background prefetch. The Interceptor's ToolExecutor warms Supabase query caches — invoices, breakdowns, roaming, tickets, wallet. Simultaneously, we call Backend `/prefetch` to warm its in-memory cache too. This means the first real query is fast."

**Open**: `Backend/tools/billing_tools.py` — show the cache section (lines 50-75)

> "The Backend has its own 5-minute TTL in-memory cache. `get_user_invoices` also eagerly prefetches breakdowns for all invoices. So when the agent calls `get_user_invoices_breakdown` next, it's an instant cache hit."

---

## 7. Response Formatting Pipeline (2 min)

**Open**: `Interceptor/utils/formatters.py`

**Talk track**:
> "Two formatters, one per channel.
>
> `format_reply_for_chat()` is light-touch — collapse whitespace, structure payment option blocks so the confirmation question gets its own line.
>
> `format_reply_for_voice()` is aggressive — strip ALL markdown (bold, tables, headers, bullets), replace ₹ with 'rupees', % with 'percent', truncate to 3 sentences, hard cap at 300 chars. The result must sound natural when spoken aloud."

---

## 8. End-to-End Flow Summary (2 min)

**Talk track — no file needed, just summarize**:

### Chat Flow:
```
User types "show my invoices"
  → Frontend POST /chat to Interceptor
  → Interceptor: inject_chat_context() wraps message with [USER_ID], [CONTEXT: Web chat]
  → intent_detector: matches "get_user_invoices" → fast-path!
  → ToolExecutor: queries Supabase directly
  → Interceptor: sends data to Backend /chat/fast
  → Backend: single Gemini call to format → returns markdown table
  → Interceptor: format_reply_for_chat() → return to Frontend
  → Total: ~0.5-1s
```

### Voice Flow:
```
User says "Why is my bill so high?"
  → Frontend WebRTC → OpenAI Realtime model
  → Model says "Let me look into that..." then calls forward_to_backend
  → Frontend intercepts tool call → POST /voice/tool-call to Interceptor
  → Interceptor: inject_voice_context() → proxy to Backend /chat
  → Backend: full agent loop (Gemini → get_user_invoices → get_breakdown → Gemini)
  → Interceptor: format_reply_for_voice() → return to Frontend
  → Frontend sends result back to Realtime model → model speaks it
  → Meanwhile: filler prompts keep the conversation alive during latency
  → Total: ~3-8s (but feels instant due to fillers)
```

---

## Quick Reference: Key Files to Open During Demo

| Concept | File | Lines |
|---|---|---|
| Architecture overview | `Interceptor/main.py` | 1-40 (docstring) |
| Chat context injection | `Interceptor/utils/context_injection.py` | `inject_chat_context()` |
| Voice context injection | `Interceptor/utils/context_injection.py` | `inject_voice_context()` |
| Agent instructions (prompt) | `Backend/instructions.py` | Full file |
| Agent definition | `Backend/agent.py` | `root_agent` at bottom |
| Intent detection (fast-path) | `Interceptor/utils/intent_detector.py` | `detect_intent()` |
| Direct Supabase execution | `Interceptor/services/tool_executor.py` | `_dispatch()` |
| Fast-path LLM formatting | `Backend/main.py` | `/chat/fast` endpoint |
| Voice token + tools | `Interceptor/main.py` | `/voice/token` |
| Voice tool definitions | `Interceptor/utils/tools.py` | `VOICE_TOOLS` |
| WebRTC + tool call handling | `Frontend/src/components/VoiceInterface.jsx` | `handleRealtimeEvent` |
| Voice filler prompts | `Frontend/src/components/voiceFillerHelpers.js` | Full file |
| Voice system personality | `eleven_labs_prompts/system.md` | Full file |
| Response formatters | `Interceptor/utils/formatters.py` | Both functions |
| Cache warming | `Backend/tools/billing_tools.py` | `_query_cache` section |
