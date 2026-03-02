"""
Fast-path Intent Detector
Pattern-matches common queries to skip LLM round trips.
Returns (tool_name, tool_args) or None.

Priority order:
1. Compound intents (e.g. "why is bill high" → invoices + breakdowns)
2. Follow-up blocklist (short contextual replies)
3. Simple intents (e.g. "show invoices")
"""

import re
import logging

logger = logging.getLogger("intent_detector")

# Short follow-ups that need conversation context — no tool data helps
FOLLOWUP_PATTERNS = [
    r"^\s*(yes|no|yeah|yep|nope|ok|okay|sure|please)\s*$",
    r"^\s*(that|this|it|the one|which one|same)\b",
    r"^\s*(tell me more|explain more|go on)\b",
]


def detect_intent(message: str, user_id: str):
    """
    Match user message to a known intent.
    Returns (tool_name, tool_args) or None.
    """
    msg = message.lower().strip()

    # 1. Short follow-ups — always skip
    for pattern in FOLLOWUP_PATTERNS:
        if re.search(pattern, msg):
            logger.info(f"Skipping fast-path (follow-up): '{message[:50]}'")
            return None

    # 2. Complex multi-tool queries — use fast-path with pre-fetched data

    # Complaints / sentiment — need full agent for conversational handling
    if re.search(r"\b(unhappy|upset|angry|frustrated|disappointed|complain|dispute|wrong|unfair|ridiculous|terrible|horrible|worst)\b", msg):
        logger.info(f"Skipping fast-path (complaint/sentiment): '{message[:50]}'")
        return None

    # Policy / knowledge / general questions — fast-path via knowledge_search
    if re.search(r"\b(policy|policies|rules?|terms|conditions|eligib|what happens|how does|what is your|what are your|do you|can i|am i|is there a|tell me about)\b", msg):
        logger.info(f"⚡ Fast-path match: 'knowledge_search' for: '{message[:50]}'")
        return "knowledge_search", {"user_id": user_id, "query": message}

    if re.search(r"\b(how (do|can|to)|what (do|should|if)|when (can|do|will))\b", msg):
        logger.info(f"⚡ Fast-path match: 'knowledge_search' for: '{message[:50]}'")
        return "knowledge_search", {"user_id": user_id, "query": message}

    # Outage — only match when user is *reporting* an outage, not asking about policy
    if re.search(r"\b(there was|i had|experiencing|we had|was there|any)\b.*(outage|down|network issue|service (down|issue|problem))", msg) \
       or re.search(r"\b(outage|network issue|service (down|issue|problem)).*(in my|my area|billed|charged|why)", msg) \
       or re.search(r"\b(service|internet|network) is (down|not working)\b", msg):
        logger.info(f"⚡ Fast-path match: 'outage_check' for: '{message[:50]}'")
        return "outage_check", {"user_id": user_id}

    if re.search(r"\b(refund|credit|compensat|adjust)\b", msg):
        logger.info(f"Skipping fast-path (complex query - refund): '{message[:50]}'")
        return None

    if re.search(r"\b(upgrade|downgrade|change.*(plan|package)|switch.*(plan|package))\b", msg):
        logger.info(f"Skipping fast-path (complex query - plan change): '{message[:50]}'")
        return None

    # 2. Compound intents — "why is bill high", "bill breakdown", etc.
    #    These need invoices + breakdowns, handled as "bill_explain"

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

    # 3. Simple direct intents
    simple_intents = [
        # Invoices
        (r"\b(show|get|see|view|check|give|my|the).*(invoice|invoices|bill|bills|billing|statement)",
         "get_user_invoices", {"user_id": user_id}),
        (r"^(invoice|invoices|bill details|billing)\s*$",
         "get_user_invoices", {"user_id": user_id}),
        # Roaming
        (r"\b(show|get|see|view|check|my|the).*(roaming|roam)",
         "check_roaming_status", {"user_id": user_id}),
        (r"^(roaming status|roaming)\s*$",
         "check_roaming_status", {"user_id": user_id}),
        # Tickets
        (r"\b(show|get|see|view|check|my|open).*(ticket|tickets)",
         "get_open_tickets", {"user_id": user_id}),
        # Wallet
        (r"\b(show|get|see|view|check|my|the).*(wallet|balance|credit)",
         "check_wallet_amount_settlement", {"user_id": user_id}),
    ]

    for pattern, tool_name, tool_args in simple_intents:
        if re.search(pattern, msg):
            logger.info(f"⚡ Fast-path match: '{tool_name}' for: '{message[:50]}'")
            return tool_name, tool_args

    return None
