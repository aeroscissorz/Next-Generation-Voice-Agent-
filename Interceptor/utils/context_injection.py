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
- Use markdown tables for structured data
- Use **bold** for important values
- Include ALL data returned by tools
- Be thorough and complete]

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
