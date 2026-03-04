"""
Dynamic Prompt Injection
Channel-specific context injection
"""

import logging

logger = logging.getLogger("context_injection")


def inject_chat_context(message: str, user_id: str, name: str = None) -> str:
    """Inject chat-specific context into the message."""
    name_context = f"[USER_NAME: {name}] " if name else ""
    context_prefix = f"""[USER_ID: {user_id}] {name_context}[CONTEXT: Web chat interface.

CRITICAL - USER IS ALREADY AUTHENTICATED:
- User ID: {user_id} is VERIFIED and CONFIRMED
- DO NOT ask for user ID confirmation
- Proceed DIRECTLY with their request using USER_ID: {user_id}
- Call the appropriate tools IMMEDIATELY

Response Format for Chat:
- Use markdown tables for structured data (invoices, breakdowns, roaming history)
- Use **bold** for important values (amounts, dates, statuses)
- For payment/overdue/wallet flows: present the summary info first, then put the confirmation question on its own line separated by a blank line
- For wallet + card split payments: show the breakdown clearly, e.g.:
  - **Wallet credit applied:** ₹700
  - **Remaining charged to Credit Card ending in 6677:** ₹700
  Then ask the confirmation question on a new line.
- For overdue bills: you MUST show the 3 consequences (late fees, service disconnection, account standing) in your first response. Show **Due date**, **Amount**, **Status** as bold key-value pairs, then list the consequences, then ask if they want to pay now. Do NOT skip the consequences or offer alternatives in the first message.
- For promise dates: show the program details clearly with bold formatting. Show **Program name**, **How it works**, **Benefits** (service stays active, no late fees, no collection), and **Maximum date** as bold key-value pairs. After setting, confirm with a bold summary showing the locked-in date.
- For payment confirmations: show a brief **Payment Summary** with amount and method before confirming
- Be thorough and include ALL relevant data returned by tools
- Always format dates in a human-friendly way: "March 7th, 2026" — never show raw "2026-03-07" format]

User message: """
    injected = context_prefix + message
    logger.info(f"[CHAT] user_id={user_id}, name={name}, original_len={len(message)}")
    return injected


def inject_voice_context(message: str, user_id: str, is_authenticated: bool = False, name: str = None) -> str:
    """Inject voice-specific context into the message."""
    name_context = f"[USER_NAME: {name}] " if name else ""

    if is_authenticated:
        context_prefix = f"""[USER_ID: {user_id}] {name_context}[CONTEXT: Voice call. User authenticated (ID: {user_id}).
Keep responses brief (1-3 sentences). No jargon.]

User message: """
    else:
        context_prefix = f"""[USER_ID: {user_id}] {name_context}[CONTEXT: Voice call. Authentication in progress.]

User message: """

    injected = context_prefix + message
    logger.info(f"[VOICE] user_id={user_id}, authenticated={is_authenticated}")
    return injected
