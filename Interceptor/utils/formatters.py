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

    # Ensure payment/wallet option lines are bolded if not already
    # e.g. lines starting with "Option 1" or "1." or "- " get light formatting
    text = _format_payment_options(text)

    return text


def _format_payment_options(text: str) -> str:
    """
    If the reply contains payment/wallet/overdue option lines, ensure they
    render as a clean structured block rather than a wall of prose.
    Detects patterns like:
      - "Option 1: ..." / "Option 2: ..."
      - "1. ..." / "2. ..."  (numbered options in payment context)
      - Inline "Would you like to..." after a summary line
    """
    # Already has markdown structure — leave it alone
    if re.search(r'\|.*\|', text) or text.count('\n') > 4:
        return text

    # Detect payment/overdue context keywords
    payment_keywords = [
        'wallet credit', 'wallet balance', 'credit card', 'ending in',
        'overdue', 'promise date', 'pay now', 'payment', 'remaining',
        'charged to', 'process your payment', 'bill of ₹', 'amount of ₹',
    ]
    lower = text.lower()
    is_payment_context = any(kw in lower for kw in payment_keywords)

    if not is_payment_context:
        return text

    # Split into sentences and reflow as a clean block
    # If there's a question at the end, keep it on its own line
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) <= 1:
        return text

    # Separate the trailing question from the info sentences
    question_starters = ('would you', 'shall i', 'do you', 'would you like', 'can i')
    info_parts = []
    question_parts = []
    for s in sentences:
        if s.lower().startswith(question_starters):
            question_parts.append(s)
        else:
            info_parts.append(s)

    if not question_parts:
        return text  # Nothing to restructure

    # Rebuild: info block + blank line + question
    info_block = ' '.join(info_parts).strip()
    question_block = ' '.join(question_parts).strip()
    return f"{info_block}\n\n{question_block}"


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
