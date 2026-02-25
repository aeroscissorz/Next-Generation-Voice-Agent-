# Latency Optimization — Technical Deep Dive

## Executive Summary

We reduced average response times from **7–17 seconds** down to **3–5 seconds** for common queries by implementing a multi-layered optimization strategy. The core insight: for ~70% of user queries, we already know what data to fetch without asking the LLM. By pattern-matching the intent and fetching data directly, we eliminate an entire LLM round trip.

---

## Architecture Overview

```
┌──────────┐     ┌──────────────────────────────────────────────────┐     ┌──────────────┐
│          │     │              INTERCEPTOR                         │     │   BACKEND     │
│ Frontend │────▶│  Intent Detector ──▶ Tool Executor ──▶ Supabase  │────▶│  /chat/fast   │
│ (React)  │     │       │                                          │     │  (1 Gemini)   │
│          │◀────│       ▼ (no match)                               │     │               │
│          │     │  Normal Path ─────────────────────────────────── │────▶│  /chat        │
│          │     │                                                  │     │  (2 Gemini)   │
└──────────┘     └──────────────────────────────────────────────────┘     └──────────────┘
```

### Two Request Paths

| | Fast Path | Normal Path |
|---|---|---|
| **LLM calls** | 1 (formatting only) | 2 (intent + formatting) |
| **Data fetch** | Interceptor → Supabase direct | Gemini decides → Backend tools → Supabase |
| **Latency** | ~3–4s | ~7–9s |
| **Use case** | Simple data lookups, policy questions | Complaints, refunds, multi-step flows |

---

## Optimization 1: Fast-Path Intent Detection

> **Code**: `Interceptor/utils/intent_detector.py` — entire file

### Problem
Every user message went through the full Gemini agent loop:
1. **Gemini call #1**: Read message → decide which tool(s) to call (~2–3s)
2. **Tool execution**: Supabase queries (~0.3–0.5s)
3. **Gemini call #2**: Read tool results → generate response (~2–3s)

For "show my invoices", Gemini call #1 is wasted — we already know the answer is `get_user_invoices`.

### Solution
Regex-based intent detection in the Interceptor pattern-matches the user message before it ever reaches the LLM.

<!-- See Interceptor/utils/intent_detector.py:27-103 — detect_intent() function -->

```python
# Priority order (intent_detector.py:27):
# 1. Follow-up blocklist — lines 34-37 (FOLLOWUP_PATTERNS matched first)
# 2. Complaint/sentiment detection — line 39 (skip fast-path, needs empathy)
# 3. Policy/knowledge questions — lines 44-49 (fast-path via vector search)
# 4. Outage reports — lines 52-57 (only actual reports, not policy questions)
# 5. Refund/plan change skip — lines 59-64 (complex flows → normal agent)
# 6. Compound intents like "why was bill high" — lines 67-80 (bill_explain)
# 7. Simple intents like "show invoices" — lines 83-101 (single table lookups)
# 8. No match → return None → normal agent path
```

### Intent Categories

**Fast-path intents** (regex match → direct Supabase → 1 Gemini call):
| Intent | Trigger Examples | Data Fetched |
|--------|-----------------|--------------|
| `get_user_invoices` | "show my invoices", "bill details" | `invoices` table |
| `bill_explain` | "why was jan bill high", "bill breakdown" | `invoices` + `invoice_breakdown` + `roaming` |
| `outage_check` | "there was an outage in my area" | `invoices` (for area) + `outages` |
| `knowledge_search` | "what is your refund policy" | `company_knowledge` (vector search) |
| `get_payment_methods` | "show my payment methods" | `payment_methods` table |
| `check_roaming_status` | "check my roaming" | `roaming` table |
| `get_open_tickets` | "show my tickets" | `support_tickets` table |
| `check_wallet_amount_settlement` | "check my wallet balance" | `wallet_amount` table |

**Skip fast-path** (always go to normal agent):
| Category | Trigger Examples | Reason |
|----------|-----------------|--------|
| Follow-ups | "yes", "that one", "tell me more" | Need conversation context |
| Complaints | "I'm unhappy with my bill" | Need empathy + multi-turn |
| Refunds | "I want a refund" | Need confirmation + DB writes |
| Plan changes | "upgrade my plan" | Need confirmation + DB writes |

### Key Design Decision: Priority Order
The regex checks run in a specific order to avoid false positives:
1. **Follow-ups first** — "yes" should never match a tool
2. **Complaints before data intents** — "I'm unhappy with my bills" should NOT match `get_user_invoices` (even though it contains "bills")
3. **Policy before outage** — "what is your outage policy" should NOT match `outage_check`
4. **Outage before bill_explain** — "why was I billed during an outage" should match `outage_check`, not `bill_explain`

---

## Optimization 2: Direct Supabase Queries from Interceptor

> **Code**: `Interceptor/services/tool_executor.py` — `ToolExecutor` class

### Problem
In the normal path, data fetching requires a full round trip:
```
Interceptor → Backend → Gemini (decides tool) → Backend tool function → Supabase → back up the chain
```

### Solution
`ToolExecutor` queries Supabase directly from the Interceptor, bypassing the Backend agent entirely for data reads.

<!-- See Interceptor/services/tool_executor.py:23-30 — class + execute() -->
<!-- See Interceptor/services/tool_executor.py:68-80 — _dispatch() entry point -->

```python
# tool_executor.py:23 — class definition
class ToolExecutor:
    def __init__(self, supabase: Client):
        self._sb = supabase

    # tool_executor.py:30 — execute() wraps _dispatch with error handling
    def execute(self, tool_name: str, args: dict) -> dict | list | None:
        return self._dispatch(tool_name, args)

    # tool_executor.py:68 — _dispatch() routes to per-tool handlers:
    #   get_user_invoices    — line 72  (also prefetches breakdowns, line 80-93)
    #   get_payment_methods  — line 95
    #   check_roaming_status — line 104
    #   get_open_tickets     — line 112
    #   check_wallet         — line 120
    #   bill_explain         — line 128 (invoices + breakdowns + roaming in one shot)
    #   outage_check         — line 150 (invoices for area → outages table)
    #   knowledge_search     — line 170 (OpenAI embedding → Supabase vector search)
```

The fetched data is then sent to `Backend /chat/fast` which makes a single Gemini call to format it into a human-readable response.

### Compound Intent Optimization
For `bill_explain` (`tool_executor.py:128`), instead of making 3 separate queries (invoices → breakdown → roaming) sequentially like the agent would, we fetch all three within a single `_dispatch` call. This saves ~0.5–1s of sequential DB round trips.

---

## Optimization 3: Prefetch on Login

> **Code**: `Interceptor/main.py:85-103` (trigger + background task), `Interceptor/services/tool_executor.py:42-66` (`prefetch_user_data`), `Backend/main.py:73-93` (`/prefetch` endpoint)

### Problem
Even with fast-path, the first query after login still hits Supabase cold — no cached data.

### Solution
When a user creates a new session (`POST /new-session`), a background task fires immediately:

<!-- See Interceptor/main.py:85-103 — new_session + _prefetch_user -->

```python
# Interceptor/main.py:85
@app.post("/new-session")
async def new_session(req: NewSessionRequest):
    result = await backend_proxy.new_session(req.user_id, req.name)
    asyncio.create_task(_prefetch_user(req.user_id))  # Fire and forget (line 92)
    return result

# Interceptor/main.py:95
async def _prefetch_user(user_id: str):
    _tool_executor.prefetch_user_data(user_id)  # Warm Interceptor cache (line 98)
    await backend_proxy.request("POST", "/prefetch", {"user_id": user_id})  # Warm Backend cache (line 100)
```

<!-- See Interceptor/services/tool_executor.py:42-66 — prefetch_user_data() fetches all tables -->
<!-- See Backend/main.py:73-93 — /prefetch endpoint calls billing_tools to warm cache -->

**What gets prefetched:**
| Data | Interceptor Cache | Backend Cache |
|------|------------------|---------------|
| Invoices | ✅ | ✅ |
| Invoice breakdowns (all) | ✅ | ✅ |
| Roaming status | ✅ | ✅ |
| Open tickets | ✅ | ✅ |
| Wallet balance | ✅ | ✅ |
| Payment methods | ✅ | ✅ |

This means by the time the user types their first message, all their data is already in memory on both services.

---

## Optimization 4: Multi-Layer Caching

### Backend Billing Cache
> **Code**: `Backend/tools/billing_tools.py:10-27` (cache infrastructure), `billing_tools.py:48-87` (invoice fetch + breakdown prefetch)

- **Type**: In-memory dict with TTL
- **TTL**: 300 seconds (5 minutes) — `billing_tools.py:11`
- **Max entries**: 200 (LRU eviction) — `billing_tools.py:25`
- **Scope**: Per-query key (e.g., `invoices:42`, `breakdown:101`)

<!-- See Backend/tools/billing_tools.py:10-27 — _query_cache, _cache_get, _cache_set -->

```python
# billing_tools.py:10
_query_cache: dict[str, tuple[float, any]] = {}
QUERY_CACHE_TTL = 300  # line 11

# billing_tools.py:13 — _cache_get: returns cached data if within TTL
# billing_tools.py:21 — _cache_set: stores data + evicts oldest if >200 entries
```

### Breakdown Prefetch on Invoice Fetch
<!-- See Backend/tools/billing_tools.py:66-82 — prefetch loop inside get_user_invoices -->

When `get_user_invoices` is called (`billing_tools.py:48`), it also prefetches breakdowns for ALL invoices (lines 66-82):
```python
# billing_tools.py:66
for inv in data:
    inv_id = str(inv.get("invoice_id", ""))
    if inv_id and _cache_get(f"breakdown:{inv_id}") is None:
        bd = supabase.table("invoice_breakdown").select("*").eq("invoice_id", inv_id).execute().data
        _cache_set(f"breakdown:{inv_id}", bd)
```
This means "why was jan bill high" after "show my invoices" has zero DB latency for the breakdown lookup.

### Knowledge Embedding Cache
> **Code**: `Backend/tools/knowledge_tools.py:20-22` (cache declarations), `knowledge_tools.py:25-50` (`get_embedding` with cache), `knowledge_tools.py:53-97` (`search_company_knowledge` with result cache)

<!-- See Backend/tools/knowledge_tools.py:20-22 — _embedding_cache, _search_cache, SEARCH_CACHE_TTL -->
<!-- See Backend/tools/knowledge_tools.py:18 — _http_client (persistent connection reuse) -->

- **Embedding cache** (`knowledge_tools.py:20`): OpenAI `text-embedding-3-small` results cached in memory (max 500 entries, eviction at line 48)
- **Search result cache** (`knowledge_tools.py:21`): Vector search results cached for 5 minutes (max 200 entries, eviction at line 82)
- **Persistent HTTP client** (`knowledge_tools.py:18`): `httpx.Client(timeout=10.0)` — reuses TCP connections to OpenAI
- **Keyword fallback** (`knowledge_tools.py:87-95`): If vector search returns nothing, falls back to `ILIKE` text search

Also mirrored in `Interceptor/services/tool_executor.py:19-20` — `_embedding_cache` for the fast-path knowledge search handler (line 170).

### Cache Hit Timeline
```
Login → prefetch fires → all data cached (background, ~1s)
Query 1: "show invoices" → fast-path → cache HIT (0ms DB) → 1 Gemini call → ~3s
Query 2: "why was jan bill high" → fast-path → cache HIT (0ms DB) → 1 Gemini call → ~3s
Query 3: "what is your refund policy" → fast-path → embedding cached → vector search → 1 Gemini call → ~3s
Query 4: "what is your refund policy" (repeat) → fast-path → embedding + search both cached → 1 Gemini call → ~2.5s
```

---

## Optimization 5: Flattened Agent Architecture

> **Code**: `Backend/agent.py:31-50` (single `LlmAgent`), `Backend/instructions.py:1-65` (`UNIFIED_INSTRUCTION`)

### Before
Multi-agent hierarchy with routing overhead:
```
Router Agent → Billing Agent → Tool calls
             → Support Agent → Tool calls
             → Knowledge Agent → Tool calls
```
Each routing decision = 1 extra LLM call.

### After
Single `LlmAgent` with all tools:

<!-- See Backend/agent.py:31-50 — root_agent definition with all 12 tools -->

```python
# agent.py:31
root_agent = LlmAgent(
    name="Support_Agent",
    model=MODEL_NAME,                    # gemini-2.5-flash-lite (from env)
    instruction=UNIFIED_INSTRUCTION,     # instructions.py:1 — single instruction set
    tools=[
        get_user_invoices, get_payment_methods, get_user_invoices_breakdown,
        check_roaming_status, check_roaming_status_monthwise, update_roaming_status_monthwise,
        check_wallet_amount_settlement, update_wallet_amount, create_wallet_entry,
        get_open_tickets, check_outage, search_company_knowledge,
    ],
)
```
One agent, one instruction set, no routing overhead.

---

## Optimization 6: Fast-Path Gemini Call with Retry

> **Code**: `Backend/main.py:312-370` (`/chat/fast` endpoint), `Backend/main.py:316-330` (`FAST_FORMAT_PROMPT`)

### `/chat/fast` Endpoint
Single Gemini call with pre-fetched data. No tool-use loop — just prompt + data → response.

<!-- See Backend/main.py:316 — FAST_FORMAT_PROMPT template -->
<!-- See Backend/main.py:338 — chat_fast() handler -->

```python
# Backend/main.py:316
FAST_FORMAT_PROMPT = """You are a telecom customer support agent. Be concise — 2-3 sentences max.
User message: {message}
Data (JSON): {tool_data}
Rules: ..."""

# Backend/main.py:338
@app.post("/chat/fast")
async def chat_fast(req: FastChatRequest):
    prompt = FAST_FORMAT_PROMPT.format(message=req.message, tool_data=json.dumps(req.tool_data))
    response = _gemini_client.models.generate_content(model=_FAST_MODEL, contents=prompt)
    return {"reply": response.text}
```

### Retry with Backoff
<!-- See Backend/main.py:349-361 — 3-attempt retry loop with 0.5s * attempt backoff -->

Handles Gemini 503/UNAVAILABLE errors (capacity spikes):
```python
# Backend/main.py:349
for attempt in range(3):
    try:
        response = _gemini_client.models.generate_content(...)
        break
    except Exception as e:
        if "503" in str(e) or "UNAVAILABLE" in str(e):
            await asyncio.sleep(0.5 * (attempt + 1))  # 0.5s, 1s, 1.5s
            continue
        raise
```
If all 3 attempts fail, returns `fast_path_error: True` (line 366) so the Interceptor falls back to the normal agent path.

---

## Optimization 7: Fast-Path Context Carry-Over

> **Code**: `Interceptor/main.py:72-74` (`_fast_path_history` declaration), `Interceptor/main.py:130-137` (accumulate on fast-path success in `/chat`), `Interceptor/main.py:147-158` (inject on normal-path fallback in `/chat`), `Interceptor/main.py:206-213` (same for `/chat/stream`), `Interceptor/main.py:223-234` (inject for `/chat/stream`)

### Problem
Fast-path responses bypass the Gemini agent session. When a follow-up goes through the normal agent, it has no context of what was discussed.

Example:
1. "show my invoices" → fast-path → "You have 2 invoices..."
2. "the 1400 one" → normal agent → "I don't know what you're referring to"

### Solution
The Interceptor accumulates fast-path exchanges in `_fast_path_history` (per user, max 5 exchanges). When a follow-up goes through the normal path, the history is injected as context:

<!-- See Interceptor/main.py:72-74 — _fast_path_history dict + _MAX_HISTORY -->

```python
# Interceptor/main.py:72
_fast_path_history: dict[str, list] = {}
_MAX_HISTORY = 5  # Keep last 5 exchanges

# On fast-path success (main.py:130):
_fast_path_history.setdefault(req.user_id, []).append({
    "user_msg": req.message,
    "agent_reply": raw_reply,
})

# On normal-path fallback (main.py:147):
history = _fast_path_history.pop(req.user_id, None)
if history:
    context_prefix = "[CONVERSATION SO FAR]\n"
    for ex in history:
        context_prefix += f"User: {ex['user_msg']}\nAgent: {ex['agent_reply']}\n"
    context_prefix += "[END CONVERSATION]\n"
    enhanced_message = inject_chat_context(context_prefix + req.message, ...)
```

This gives the normal agent full conversation context even though the earlier exchanges were handled by the fast-path.

---

## Optimization 8: Model Selection

Using `gemini-2.5-flash-lite` — configured via `GOOGLE_GENAI_MODEL` env var.
- Backend agent: `Backend/agent.py:29` — `MODEL_NAME = os.environ.get("GOOGLE_GENAI_MODEL")`
- Fast-path: `Backend/main.py:314` — `_FAST_MODEL = os.environ.get("GOOGLE_GENAI_MODEL", "gemini-2.5-flash-lite")`

Optimized for speed over capability. For a customer support agent that mostly formats data into readable text, this is the right trade-off.

---

## Latency Breakdown Comparison

### Before (Normal Path Only)
```
User message                                    0ms
├─ Interceptor context injection                ~5ms
├─ Backend receives message                     ~10ms
├─ Gemini call #1 (decide tool)                 ~2500ms
├─ Tool execution (Supabase)                    ~300ms
├─ Gemini call #2 (format response)             ~2500ms
├─ Interceptor formatting                       ~5ms
└─ Frontend renders                             ~10ms
                                        TOTAL: ~5300ms (best case)
                                               ~9000ms (with knowledge search)
                                               ~17000ms (multi-tool flows)
```

### After (Fast Path)
```
User message                                    0ms
├─ Intent detection (regex)                     ~1ms
├─ Direct Supabase query (cached)               ~0-50ms
├─ Backend /chat/fast (1 Gemini call)           ~2500ms
├─ Interceptor formatting                       ~5ms
└─ Frontend renders                             ~10ms
                                        TOTAL: ~2600ms (cached)
                                               ~3500ms (cold, with DB query)
```

### After (Normal Path with Prefetch)
```
User message                                    0ms
├─ Interceptor context injection                ~5ms
├─ Backend receives message                     ~10ms
├─ Gemini call #1 (decide tool)                 ~2500ms
├─ Tool execution (cached from prefetch)        ~0-10ms
├─ Gemini call #2 (format response)             ~2500ms
├─ Interceptor formatting                       ~5ms
└─ Frontend renders                             ~10ms
                                        TOTAL: ~5030ms (vs ~5300ms before)
```

---

## Files Modified

| File | What Changed | Key Lines |
|------|-------------|-----------|
| `Interceptor/utils/intent_detector.py` | New file — regex-based intent detection with priority ordering | `detect_intent()` :27-103, `FOLLOWUP_PATTERNS` :18-22 |
| `Interceptor/services/tool_executor.py` | New file — direct Supabase queries + knowledge vector search | `ToolExecutor` :23, `_dispatch()` :68, `prefetch_user_data()` :42, `knowledge_search` :170 |
| `Interceptor/main.py` | Fast-path routing in `/chat` and `/chat/stream`, prefetch on login, context carry-over | `/chat` fast-path :108-143, `/chat/stream` fast-path :183-220, `_prefetch_user` :95, `_fast_path_history` :72 |
| `Backend/main.py` | `/chat/fast` endpoint, `/prefetch` endpoint, retry with backoff | `/chat/fast` :338, `FAST_FORMAT_PROMPT` :316, retry :349-361, `/prefetch` :73 |
| `Backend/tools/billing_tools.py` | In-memory cache (5min TTL), breakdown prefetch on invoice fetch | `_cache_get` :13, `_cache_set` :21, `get_user_invoices` :48, breakdown prefetch :66-82 |
| `Backend/tools/knowledge_tools.py` | Embedding cache, search result cache, persistent HTTP client | `_embedding_cache` :20, `_search_cache` :21, `get_embedding()` :25, `search_company_knowledge()` :53, `_http_client` :18 |
| `Backend/agent.py` | Flattened to single agent (was multi-agent) | `root_agent` :31-50 |
| `Backend/instructions.py` | Unified instruction set for single agent | `UNIFIED_INSTRUCTION` :1-65 |

---

## Trade-offs and Limitations

1. **Regex brittleness** — Intent detection relies on pattern matching. Novel phrasings may miss the fast-path and fall through to the normal agent (which still works, just slower). This is a safe fallback — worst case is the old latency, not a broken response.

2. **Stateless fast-path** — Fast-path responses don't enter the Gemini agent's session history. We mitigate this with `_fast_path_history` context injection, but it's a text-based workaround, not native session state.

3. **Cache staleness** — 5-minute TTL means data changes (e.g., new invoice, roaming toggle) won't reflect for up to 5 minutes. Acceptable for a support chat where billing data changes infrequently.

4. **Memory usage** — All caches are in-memory (no Redis/external store). For a single-user demo this is fine. For production, would need distributed caching.

5. **Single Gemini model** — No fallback model if the primary is unavailable. The retry handles transient 503s, but a sustained outage would degrade to error responses.
