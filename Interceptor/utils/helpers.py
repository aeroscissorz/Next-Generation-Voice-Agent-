"""
Utility Helper Functions
"""

import json
import logging
from typing import Any

logger = logging.getLogger("helpers")

USER_ID_MIN_LENGTH = 2
USER_ID_MAX_LENGTH = 2


def normalize_to_text(value: Any) -> str:
    """Normalize any value to a clean text string."""
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
    """Load system instructions from a markdown file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load system instructions from {file_path}: {e}")
        return "You are a helpful telecom voice assistant. Ask for numeric User ID first."


def extract_user_id_from_spoken(raw_user_id: str) -> str:
    """
    Extract numeric user ID from spoken input.
    Strips to digits only, validates length within [MIN, MAX].
    Returns empty string if invalid.
    """
    normalized = "".join(c for c in raw_user_id if c.isdigit())
    logger.info(f"extract_user_id_from_spoken: raw input='{raw_user_id}', normalized output='{normalized}'")

    digit_count = len(normalized)
    if digit_count < USER_ID_MIN_LENGTH or digit_count > USER_ID_MAX_LENGTH:
        logger.info(
            f"extract_user_id_from_spoken: rejected — digit count {digit_count} "
            f"outside allowed range [{USER_ID_MIN_LENGTH}, {USER_ID_MAX_LENGTH}]"
        )
        return ""

    return normalized
