"""
Response Formatters
===================
Channel-specific response formatting for chat and voice outputs.

Two formatters:
  - format_reply_for_chat()  — Light cleanup for web chat (whitespace, payment option structure)
  - format_reply_for_voice() — Heavy transformation for voice (strip markdown, limit length,
                                replace symbols with words, cap at 1-3 sentences)

The chat formatter is intentionally light-touch — the Backend agent already
produces well-formatted markdown. The formatter just cleans up whitespace
and ensures payment/wallet option blocks are properly structured.

The voice formatter is aggressive — it strips ALL markdown, replaces symbols
with spoken words (₹ → "rupees", % → "percent"), and truncates to 3 sentences
or 300 characters, whichever is shorter.
"""

import re
import logging

logger = logging.getLogger("formatters")


def format_reply_for_chat(reply_text: str) -> str:
    """
    Format a Backend response for the web chat interface.
    
    Performs light cleanup:
      1. Strip leading/trailing whitespace
      2. Collapse multiple spaces to single space
      3. Collapse 3+ newlines to double newline
      4. Structure payment/wallet option blocks for readability
    
    The payment option formatter detects payment-context keywords and
    ensures the confirmation question appears on its own line (separated
    by a blank line from the info block).
    """
    if not reply_text:
        return ""
    text = reply_text.strip()
    text = re.sub(r' +', ' ', text)           # Collapse multiple spaces
    text = re.sub(r'\n{3,}', '\n\n', text)    # Collapse excessive newlines

    # Ensure payment/wallet option lines are properly structured
    text = _format_payment_options(text)

    return text


def _format_payment_options(text: str) -> str:
    """
    Restructure payment/wallet/overdue option blocks for better readability.
    
    Problem: The LLM sometimes outputs payment info and the confirmation
    question in a single dense paragraph. This function separates them
    so the question appears on its own line after a blank line.
    
    Detection: Looks for payment-context keywords (wallet credit, credit card,
    overdue, promise date, etc.) in the text.
    
    Restructuring: Splits sentences, identifies the trailing question
    (starts with "Would you", "Shall I", etc.), and puts it on its own line.
    
    Skips restructuring if:
      - Text already has markdown tables (|...|)
      - Text already has 5+ lines (already well-structured)
      - No payment-context keywords found
      - Only 1 sentence
      - No trailing question found
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

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) <= 1:
        return text

    # Separate trailing question from info sentences
    question_starters = ('would you', 'shall i', 'do you', 'would you like', 'can i')
    info_parts = []
    question_parts = []
    for s in sentences:
        if s.lower().startswith(question_starters):
            question_parts.append(s)
        else:
            info_parts.append(s)

    if not question_parts:
        return text  # No question to separate — nothing to restructure

    # Rebuild: info block + blank line + question on its own line
    info_block = ' '.join(info_parts).strip()
    question_block = ' '.join(question_parts).strip()
    return f"{info_block}\n\n{question_block}"


def format_reply_for_voice(reply_text: str) -> str:
    """
    Convert a Backend response to voice-friendly text.
    
    Transformations (in order):
      1. Strip all markdown formatting (bold, italic, underline, code, headers, lists, tables)
      2. Replace symbols with spoken words (₹ → rupees, % → percent, & → and, etc.)
      3. Collapse whitespace to single spaces
      4. Truncate to first 3 sentences
      5. Hard cap at 300 characters (breaks at word boundary)
    
    The result should sound natural when spoken by the OpenAI Realtime voice model.
    """
    if not reply_text:
        return ""

    text = reply_text

    # Strip markdown formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold** → bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)        # *italic* → italic
    text = re.sub(r'_([^_]+)_', r'\1', text)          # _underline_ → underline
    text = re.sub(r'`([^`]+)`', r'\1', text)          # `code` → code
    text = re.sub(r'#{1,6}\s*', '', text)              # ### headers → remove
    text = re.sub(r'[-*]\s+', '', text)                # - list items → remove bullets
    text = re.sub(r'\|[^\n]+\|', '', text)             # |table|rows| → remove

    # Replace symbols with spoken words
    text = text.replace('₹', ' rupees ')
    text = text.replace('$', ' dollars ')
    text = text.replace('%', ' percent ')
    text = text.replace('&', ' and ')
    text = text.replace('@', ' at ')
    text = text.replace('#', ' number ')

    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Take first 3 sentences only (voice responses should be brief)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    text = ' '.join(sentences[:3])

    # Hard cap at 300 characters (break at word boundary)
    if len(text) > 300:
        text = text[:300].rsplit(' ', 1)[0] + '.'

    return text
