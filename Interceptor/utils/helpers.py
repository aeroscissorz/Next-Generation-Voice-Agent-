"""
Utility Helper Functions
Common utility functions used across the Interceptor
"""

import json
from typing import Any


def normalize_to_text(value: Any) -> str:
    """
    Normalize any value to a clean text string.
    
    Args:
        value: Any value (str, dict, list, None, etc.)
    
    Returns:
        Normalized string representation
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
    Load system instructions from a markdown file.
    
    Args:
        file_path: Path to the instructions file
    
    Returns:
        File contents as string, or fallback instructions on error
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        import logging
        logger = logging.getLogger("helpers")
        logger.error(f"Failed to load system instructions from {file_path}: {e}")
        
        # Fallback to minimal instruction set
        return """You are a helpful telecom voice assistant. 
        Strictly handle telecom support and billing only. 
        Ask for numeric User ID first. 
        Always say a filler before calling tools.
        """


def extract_user_id_from_spoken(raw_user_id: str) -> str:
    """
    Extract numeric user ID from spoken input.
    Handles cases like "1 0 1" -> "101", "forty two" -> "42" (if already converted by STT)
    
    Args:
        raw_user_id: Raw user ID from speech recognition
    
    Returns:
        Normalized numeric user ID
    """
    # Remove spaces, dashes, and non-alphanumeric characters
    normalized = "".join(c for c in raw_user_id if c.isalnum())
    return normalized


def is_numeric_id(user_id: str) -> bool:
    """
    Check if a user ID is numeric.
    
    Args:
        user_id: User ID to check
    
    Returns:
        True if numeric, False otherwise
    """
    return user_id.strip().isdigit()
