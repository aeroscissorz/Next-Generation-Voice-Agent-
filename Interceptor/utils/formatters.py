"""
Response Formatters
Channel-specific response formatting using Gemini AI
"""

import logging
from google import genai
from .config import config

logger = logging.getLogger("formatters")


def format_reply_for_chat(reply_text: str) -> str:
    """
    Format response for chat interface with markdown.
    
    Args:
        reply_text: Raw response from Backend
    
    Returns:
        Markdown-formatted response for chat UI
    """
    if not reply_text:
        return ""

    if not config.GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not set, returning unformatted text")
        return reply_text

    try:
        client = genai.Client(api_key=config.GOOGLE_API_KEY)
        prompt = f"""You are a formatting assistant for a customer support chat.
            Convert the plain response into clean markdown for chat UI.

            Rules:
            - Keep meaning exactly the same. Do not add or remove facts.
            - Use short paragraphs and line breaks for readability.
            - Use bullet points for lists/options.
            - Use **bold** for important values (amounts, dates, IDs, statuses).
            - If there are multiple structured items, use a markdown table.
            - Return only formatted markdown.

            Plain response:
            {reply_text}
            """
        response = client.models.generate_content(
            model=config.GOOGLE_GENAI_MODEL,
            contents=prompt
        )
        formatted = response.text if response and response.text else ""
        return formatted.strip() if formatted else reply_text
    except Exception as e:
        logger.error(f"Error formatting for chat: {e}")
        return reply_text


def format_reply_for_voice(reply_text: str) -> str:
    """
    Convert a backend reply into voice-friendly text (1-2 sentences, no symbols).
    
    Args:
        reply_text: Raw response from Backend
    
    Returns:
        Voice-friendly text suitable for TTS
    """
    if not reply_text:
        return ""

    if not config.GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not set, returning unformatted text")
        return reply_text

    try:
        client = genai.Client(api_key=config.GOOGLE_API_KEY)
        prompt = f"""You are a voice formatting assistant. Convert this customer support response
            into 1-2 short spoken sentences suitable for text-to-speech.

            Rules:
            - Extract only the most important information.
            - Use simple, spoken language.
            - No markdown, no bullet points, no special characters.
            - Say "dollar" not "$", say "percent" not "%".
            - Numbers should be spoken naturally (e.g., "fourteen hundred" not "1400").
            - Keep it brief — maximum 2 sentences.

            Response to convert:
            {reply_text}
            """
        response = client.models.generate_content(
            model=config.GOOGLE_GENAI_MODEL,
            contents=prompt
        )
        formatted = response.text if response and response.text else ""
        return formatted.strip() if formatted else reply_text
    except Exception as e:
        logger.error(f"Error formatting for voice: {e}")
        return reply_text


def format_reply_for_sms(reply_text: str) -> str:
    """
    Format response for SMS (160 character limit, plain text only).
    
    Args:
        reply_text: Raw response from Backend
    
    Returns:
        SMS-friendly text (max 160 chars)
    """
    if not reply_text:
        return ""

    if not config.GOOGLE_API_KEY:
        # Fallback: truncate to 160 chars
        return reply_text[:160]

    try:
        client = genai.Client(api_key=config.GOOGLE_API_KEY)
        prompt = f"""Convert this response to SMS format (160 characters max, plain text only).

            Rules:
            - Maximum 160 characters
            - No formatting, no symbols
            - Extract single most important piece of information
            - Use abbreviations if needed (e.g., "msg" for "message")

            Response to convert:
            {reply_text}
            """
        response = client.models.generate_content(
            model=config.GOOGLE_GENAI_MODEL,
            contents=prompt
        )
        formatted = response.text if response and response.text else ""
        # Ensure 160 char limit
        return (formatted.strip()[:160]) if formatted else reply_text[:160]
    except Exception as e:
        logger.error(f"Error formatting for SMS: {e}")
        return reply_text[:160]


def format_reply_for_whatsapp(reply_text: str) -> str:
    """
    Format response for WhatsApp (supports basic markdown, brief).
    
    Args:
        reply_text: Raw response from Backend
    
    Returns:
        WhatsApp-friendly text with basic formatting
    """
    if not reply_text:
        return ""

    if not config.GOOGLE_API_KEY:
        return reply_text

    try:
        client = genai.Client(api_key=config.GOOGLE_API_KEY)
        prompt = f"""Convert this response for WhatsApp format.

            Rules:
            - Keep brief (2-3 sentences max)
            - Use WhatsApp formatting: *bold*, _italic_
            - Be conversational and friendly
            - Use emojis sparingly if appropriate
            - No complex formatting

            Response to convert:
            {reply_text}
            """
        response = client.models.generate_content(
            model=config.GOOGLE_GENAI_MODEL,
            contents=prompt
        )
        formatted = response.text if response and response.text else ""
        return formatted.strip() if formatted else reply_text
    except Exception as e:
        logger.error(f"Error formatting for WhatsApp: {e}")
        return reply_text
