"""
Dynamic Prompt Injection
Channel-specific context injection for optimized Backend responses
"""


def inject_chat_context(message: str, user_id: str) -> str:
    """
    Inject chat-specific context into the message.
    Chat users are already authenticated via Supabase, so we can be more direct.
    
    Args:
        message: Original user message
        user_id: User identifier (email)
    
    Returns:
        Enhanced message with chat context
    """
    context_prefix = f"""[CONTEXT: User is authenticated via web interface. User ID: {user_id} is verified. 
You can proceed directly with their request without asking for identification.
User expects detailed, formatted responses with all relevant information.]

User message: """
    return context_prefix + message


def inject_voice_context(message: str, user_id: str, is_authenticated: bool = False) -> str:
    """
    Inject voice-specific context into the message.
    Voice users go through a 3-step authentication process.
    
    Args:
        message: Original user message
        user_id: User identifier (validated customer ID)
        is_authenticated: Whether user has been authenticated via voice
    
    Returns:
        Enhanced message with voice context
    """
    if is_authenticated:
        context_prefix = f"""[CONTEXT: Voice call. User has been authenticated (User ID: {user_id} verified via voice).
Keep responses brief and conversational (1-3 sentences max).
Focus on the most important information only.
Avoid technical jargon unless necessary.]

User message: """
    else:
        context_prefix = f"""[CONTEXT: Voice call. User authentication in progress.
This is part of the voice authentication flow.
Keep responses brief and focused on verification.]

User message: """
    
    return context_prefix + message


def inject_sms_context(message: str, user_id: str) -> str:
    """
    Inject SMS-specific context into the message.
    SMS requires extremely brief responses due to character limits.
    
    Args:
        message: Original user message
        user_id: User identifier
    
    Returns:
        Enhanced message with SMS context
    """
    context_prefix = f"""[CONTEXT: SMS message. User ID: {user_id}.
Keep responses extremely brief (160 characters max).
Use plain text only, no formatting.
Focus on single most important piece of information.]

User message: """
    return context_prefix + message


def inject_whatsapp_context(message: str, user_id: str) -> str:
    """
    Inject WhatsApp-specific context into the message.
    WhatsApp allows richer formatting but still prefers brevity.
    
    Args:
        message: Original user message
        user_id: User identifier
    
    Returns:
        Enhanced message with WhatsApp context
    """
    context_prefix = f"""[CONTEXT: WhatsApp message. User ID: {user_id}.
Keep responses brief (2-3 sentences).
You can use basic formatting (*bold*, _italic_).
Be conversational and friendly.]

User message: """
    return context_prefix + message
