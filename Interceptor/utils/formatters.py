"""
Response Formatters
Channel-specific response formatting
"""

import re
import logging

logger = logging.getLogger("formatters")


def format_reply_for_chat(reply_text: str) -> str:
    """Format response for chat interface. Simple cleanup, no LLM."""
    if not reply_text:
        return ""
    text = reply_text.strip()
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def format_reply_for_voice(reply_text: str) -> str:
    """Convert backend reply to voice-friendly text (1-3 sentences, no symbols)."""
    if not reply_text:
        return ""

    text = reply_text

    # Remove markdown
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'[-*]\s+', '', text)
    text = re.sub(r'\|[^\n]+\|', '', text)

    # Replace symbols with words
    text = text.replace('$', ' dollars ')
    text = text.replace('%', ' percent ')
    text = text.replace('&', ' and ')
    text = text.replace('@', ' at ')
    text = text.replace('#', ' number ')

    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Take first 3 sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    text = ' '.join(sentences[:3])

    # Limit length
    if len(text) > 300:
        text = text[:300].rsplit(' ', 1)[0] + '.'

    return text
