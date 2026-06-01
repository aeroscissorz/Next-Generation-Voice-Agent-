"""
Utility Helper Functions
========================
Shared utility functions used across the Interceptor service.

Functions:
  - normalize_to_text()           — Convert any value (dict, list, None) to a clean string
  - load_system_instructions()    — Load voice system prompt from a markdown file
  - extract_user_id_from_spoken() — Extract numeric digits from spoken user ID input

Constants:
  - USER_ID_MIN_LENGTH / USER_ID_MAX_LENGTH — Valid user ID length range (both set to 2)
    These are used by both extract_user_id_from_spoken() and VoiceAuthService.validate_user_id()
"""

import json
import logging
from typing import Any

logger = logging.getLogger("helpers")

# ─── User ID Length Constraints ──────────────────────────────────────────────
# Valid user IDs must be exactly 2 digits (e.g., "42").
# Used by extract_user_id_from_spoken() for pre-validation before DB lookup,
# and by VoiceAuthService.validate_user_id() for the same check.
USER_ID_MIN_LENGTH = 2
USER_ID_MAX_LENGTH = 2


def normalize_to_text(value: Any) -> str:
    """
    Normalize any value to a clean text string.
    
    Handles:
      - None → ""
      - str → stripped string
      - dict/list → JSON string (for debugging/logging)
      - anything else → str() conversion
    
    Used throughout the Interceptor to safely extract text from Backend
    responses that might be dicts, lists, or None.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value).strip()
    return str(value).strip()


def load_system_instructions(file_path: str) -> str:
    """
    Load voice system instructions from a markdown file.
    
    The file (eleven_labs_prompts/system.md) contains the personality,
    tone, and flow rules for the OpenAI Realtime voice model.
    
    Falls back to a minimal default prompt if the file can't be read.
    
    Args:
        file_path: Absolute or relative path to the markdown file
    
    Returns:
        The file contents as a string, or a fallback prompt on error
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load system instructions from {file_path}: {e}")
        return "You are a helpful telecom voice assistant. Ask for numeric User ID first."


def extract_user_id_from_spoken(raw_user_id: str) -> str:
    """
    Extract a numeric user ID from spoken input.
    
    Speech recognition may produce various formats:
      - "42" (already numeric)
      - "forty two" (word form — handled upstream by the Realtime model)
      - "4 2" (spaced digits)
      - "my ID is 42" (with surrounding text)
    
    This function:
      1. Strips all non-digit characters
      2. Validates the digit count is within [USER_ID_MIN_LENGTH, USER_ID_MAX_LENGTH]
      3. Returns the normalized digit string, or "" if invalid
    
    Args:
        raw_user_id: Raw string from speech recognition
    
    Returns:
        Normalized numeric string (e.g., "42") or "" if invalid
    """
    # Strip everything except digits
    normalized = "".join(c for c in raw_user_id if c.isdigit())
    logger.info(f"extract_user_id_from_spoken: raw input='{raw_user_id}', normalized output='{normalized}'")

    # Validate length
    digit_count = len(normalized)
    if digit_count < USER_ID_MIN_LENGTH or digit_count > USER_ID_MAX_LENGTH:
        logger.info(
            f"extract_user_id_from_spoken: rejected — digit count {digit_count} "
            f"outside allowed range [{USER_ID_MIN_LENGTH}, {USER_ID_MAX_LENGTH}]"
        )
        return ""

    return normalized
