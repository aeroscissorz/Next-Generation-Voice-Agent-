"""
Fast-Path Intent Detector
==========================
Pattern-matches user messages to known intents using regex, enabling the
Interceptor to skip the full Gemini agent loop for simple, predictable queries.

When a match is found, the Interceptor can:
  1. Fetch the data directly from Supabase via ToolExecutor
  2. Send it to Backend /chat/fast for a single LLM formatting call
  3. Return the response in ~0.5-1s instead of 3-8s

Priority Order (checked top to bottom):
  1. Follow-up blocklist — short contextual replies ("yes", "no", "tell me more")
     that need conversation history → always skip fast-path
  2. Complaint/sentiment — emotional messages that need the full agent's
     empathetic handling → always skip fast-path
  3. Policy/knowledge questions — routed to knowledge_search fast-path
  4. Outage reports — routed to outage_check fast-path (compound query)
  5. Refund/plan change requests — complex multi-step flows → skip fast-path
  6. Bill explanation — "why is my bill high?" → bill_explain fast-path
  7. Simple direct intents — "show my invoices", "check roaming" → single tool

Returns:
  - (tool_name, tool_args) if a fast-path match is found
  - None if the message should go through the full agent loop
"""

import re
import logging

logger = logging.getLogger("intent_detector")

# ─── Follow-Up Blocklist ─────────────────────────────────────────────────────
# Short replies that depend on conversation context (e.g., "yes" to a refund
# confirmation). These MUST go through the full agent loop because the agent
# needs the conversation history to understand what "yes" refers to.
FOLLOWUP_PATTERNS = [
    r"^\s*(yes|no|yeah|yep|nope|ok|okay|sure|please)\s*$",
    r"^\s*(that|this|it|the one|which one|same)\b",
    r"^\s*(tell me more|explain more|go on)\b",
]


def detect_intent(message: str, user_id: str):
    """
    Match a user message to a known intent for fast-path execution.
    
    Args:
        message: Raw user message text
        user_id: User identifier (passed through to tool args)
    
    Returns:
        Tuple of (tool_name, tool_args) if fast-path match found, else None.
        tool_name maps to a ToolExecutor._dispatch() handler.
    """
    msg = message.lower().strip()

    # ─── 1. Short follow-ups — always skip fast-path ─────────────────
    # These need conversation context to be meaningful
    for pattern in FOLLOWUP_PATTERNS:
        if re.search(pattern, msg):
            logger.info(f"Skipping fast-path (follow-up): '{message[:50]}'")
            return None

    # ─── 2. Complaints / sentiment — need full agent for empathy ─────
    # The agent's instruction has detailed empathy triggers for these
    if re.search(r"\b(unhappy|upset|angry|frustrated|disappointed|complain|dispute|wrong|unfair|ridiculous|terrible|horrible|worst)\b", msg):
        logger.info(f"Skipping fast-path (complaint/sentiment): '{message[:50]}'")
        return None

    # ─── 3. Policy / knowledge questions — fast-path via RAG ─────────
    # These can be answered with a knowledge base search + single LLM call
    if re.search(r"\b(policy|policies|rules?|terms|conditions|eligib|what happens|how does|what is your|what are your|do you|can i|am i|is there a|tell me about)\b", msg):
        logger.info(f"⚡ Fast-path match: 'knowledge_search' for: '{message[:50]}'")
        return "knowledge_search", {"user_id": user_id, "query": message}

    if re.search(r"\b(how (do|can|to)|what (do|should|if)|when (can|do|will))\b", msg):
        logger.info(f"⚡ Fast-path match: 'knowledge_search' for: '{message[:50]}'")
        return "knowledge_search", {"user_id": user_id, "query": message}

    # ─── 4. Outage reports — compound fast-path (invoices + outages) ──
    # Only matches when user is *reporting* an outage, not asking about policy
    if re.search(r"\b(there was|i had|experiencing|we had|was there|any)\b.*(outage|down|network issue|service (down|issue|problem))", msg) \
       or re.search(r"\b(outage|network issue|service (down|issue|problem)).*(in my|my area|billed|charged|why)", msg) \
       or re.search(r"\b(service|internet|network) is (down|not working)\b", msg):
        logger.info(f"⚡ Fast-path match: 'outage_check' for: '{message[:50]}'")
        return "outage_check", {"user_id": user_id}

    # ─── 5. Complex multi-step flows — always skip fast-path ─────────
    # Refunds need the full outage refund flow (confirmation, wallet check, etc.)
    if re.search(r"\b(refund|credit|compensat|adjust)\b", msg):
        logger.info(f"Skipping fast-path (complex query - refund): '{message[:50]}'")
        return None

    # Plan changes need the full agent for confirmation and policy checks
    if re.search(r"\b(upgrade|downgrade|change.*(plan|package)|switch.*(plan|package))\b", msg):
        logger.info(f"Skipping fast-path (complex query - plan change): '{message[:50]}'")
        return None

    # ─── 6. Bill explanation — compound fast-path ────────────────────
    # "Why is my bill high?" needs invoices + breakdowns + roaming data

    # Catch implicit bill references: "why was jan high", "why is december so expensive"
    MONTHS = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    if re.search(rf"\b(why|how come).*{MONTHS}.*(high|increase|more|expensive)", msg):
        logger.info(f"⚡ Fast-path match: 'bill_explain' (month ref) for: '{message[:50]}'")
        return "bill_explain", {"user_id": user_id}

    if re.search(r"\b(why|how come).*(bill|invoice|charge).*(high|increase|more|expensive)", msg):
        logger.info(f"⚡ Fast-path match: 'bill_explain' for: '{message[:50]}'")
        return "bill_explain", {"user_id": user_id}

    if re.search(r"\b(bill|invoice|charge).*(high|increase|more|expensive)", msg):
        logger.info(f"⚡ Fast-path match: 'bill_explain' for: '{message[:50]}'")
        return "bill_explain", {"user_id": user_id}

    if re.search(r"\b(breakdown|break down).*(bill|invoice|charge)", msg):
        logger.info(f"⚡ Fast-path match: 'bill_explain' for: '{message[:50]}'")
        return "bill_explain", {"user_id": user_id}

    if re.search(r"\b(bill|invoice).*(breakdown|break down)", msg):
        logger.info(f"⚡ Fast-path match: 'bill_explain' for: '{message[:50]}'")
        return "bill_explain", {"user_id": user_id}

    # ─── 7. Simple direct intents — single table query ───────────────
    # These map 1:1 to a Supabase table query
    simple_intents = [
        # Invoices — "show my invoices", "get my bills", etc.
        (r"\b(show|get|see|view|check|give|my|the).*(invoice|invoices|bill|bills|billing|statement)",
         "get_user_invoices", {"user_id": user_id}),
        (r"^(invoice|invoices|bill details|billing)\s*$",
         "get_user_invoices", {"user_id": user_id}),
        # Roaming — "check my roaming", "roaming status"
        (r"\b(show|get|see|view|check|my|the).*(roaming|roam)",
         "check_roaming_status", {"user_id": user_id}),
        (r"^(roaming status|roaming)\s*$",
         "check_roaming_status", {"user_id": user_id}),
        # Tickets — "show my tickets", "open tickets"
        (r"\b(show|get|see|view|check|my|open).*(ticket|tickets)",
         "get_open_tickets", {"user_id": user_id}),
        # Wallet — "check my wallet", "wallet balance"
        (r"\b(show|get|see|view|check|my|the).*(wallet|balance|credit)",
         "check_wallet_amount_settlement", {"user_id": user_id}),
    ]

    for pattern, tool_name, tool_args in simple_intents:
        if re.search(pattern, msg):
            logger.info(f"⚡ Fast-path match: '{tool_name}' for: '{message[:50]}'")
            return tool_name, tool_args

    # No match — message goes through the full agent loop
    return None
