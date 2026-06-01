"""
Voice Authentication Service
=============================
Manages authentication state for voice callers. In the voice flow, users
must provide their User ID at the start of each call. This service:

  1. Validates the spoken User ID against the 'users_voice' table in Supabase
  2. Tracks authentication state per session (email → authenticated boolean)
  3. Maps email-based user IDs to validated customer IDs (e.g., "user@email.com" → "42")

Authentication Flow:
  1. User starts a voice call → Frontend gets ephemeral token from /voice/token
  2. OpenAI Realtime model asks for User ID → user speaks it
  3. Realtime model calls validate_user tool → Frontend POSTs to /voice/tool-call
  4. This service validates the ID against Supabase
  5. If valid: user is marked as authenticated for the rest of the call
  6. Subsequent forward_to_backend calls use the validated customer_id

State is in-memory (lost on restart). Auth is reset on each new /voice/token request.
"""

import logging
from typing import Dict, Optional
from supabase import Client

from utils.helpers import USER_ID_MIN_LENGTH, USER_ID_MAX_LENGTH

logger = logging.getLogger("voice_auth")


class VoiceAuthService:
    """
    Manages voice authentication state.
    
    State is stored in two in-memory dicts:
      - _auth_state: email → bool (is this user authenticated?)
      - _customer_id: email → str (what's their validated customer ID?)
    
    The email comes from the Frontend's auth system (Supabase Auth).
    The customer_id comes from the 'users_voice' table after validation.
    """
    
    def __init__(self, supabase_client: Optional[Client] = None):
        self.supabase = supabase_client
        
        # Session auth state — keyed by user_id (email from frontend)
        self._auth_state: Dict[str, bool] = {}
        
        # Maps email → validated customer ID (e.g., "user@email.com" → "42")
        self._customer_id: Dict[str, str] = {}
    
    def is_authenticated(self, user_id: str) -> bool:
        """Check if a voice caller is authenticated for this session."""
        return self._auth_state.get(user_id, False)
    
    def get_customer_id(self, user_id: str) -> Optional[str]:
        """
        Get the validated customer ID for an authenticated user.
        Returns None if the user hasn't been authenticated yet.
        This ID is used for all Backend tool calls (instead of the email).
        """
        return self._customer_id.get(user_id)
    
    def set_authenticated(self, user_id: str, customer_id: str) -> None:
        """
        Mark a user as authenticated after successful validation.
        Stores both the auth flag and the customer_id mapping.
        """
        self._auth_state[user_id] = True
        self._customer_id[user_id] = customer_id
        logger.info(f"User authenticated: {user_id} -> customer_id: {customer_id}")
    
    def reset_auth(self, user_id: str) -> None:
        """
        Reset authentication state for a user.
        Called when a new voice session starts (/voice/token) to ensure
        the user must re-authenticate on each new call.
        """
        self._auth_state[user_id] = False
        self._customer_id.pop(user_id, None)
        logger.info(f"Auth reset for user: {user_id}")
    
    async def validate_user_id(self, spoken_user_id: str) -> tuple[bool, Optional[str], str]:
        """
        Validate a spoken User ID against the Supabase 'users_voice' table.

        Validation steps:
          1. Check that Supabase client is available
          2. Verify the ID is numeric (digits only)
          3. Verify length is within [USER_ID_MIN_LENGTH, USER_ID_MAX_LENGTH]
          4. Query 'users_voice' table for a matching user_id
          5. Return (authenticated, customer_id, message)

        Args:
            spoken_user_id: Normalized numeric string from speech recognition

        Returns:
            Tuple of (authenticated: bool, customer_id: Optional[str], message: str)
            - On success: (True, "42", "Thanks! I've confirmed your account...")
            - On failure: (False, None, "I heard 99, but I couldn't find that ID...")
        """
        # Log received ID and its length for debugging
        logger.info(f"validate_user_id: received user_id='{spoken_user_id}', length={len(spoken_user_id)}")

        if not self.supabase:
            logger.error("Supabase not initialized; cannot validate user")
            logger.info("validate_user_id: outcome=failure, reason=supabase_not_initialized")
            return (
                False, 
                None, 
                "System error: Validation service unavailable"
            )

        # Ensure ID is numeric (speech recognition might produce "forty two" → already normalized)
        if not spoken_user_id.isdigit():
            logger.info(f"validate_user_id: outcome=failure, reason=not_numeric, user_id='{spoken_user_id}'")
            return (
                False,
                None,
                f"Invalid User ID format. I heard {spoken_user_id}, but IDs must be numeric."
            )

        # Length validation before hitting the database
        id_length = len(spoken_user_id)
        if id_length < USER_ID_MIN_LENGTH or id_length > USER_ID_MAX_LENGTH:
            msg = (
                f"User ID must be between {USER_ID_MIN_LENGTH} and {USER_ID_MAX_LENGTH} digits. "
                f"I heard {spoken_user_id} which is {id_length} digits."
            )
            logger.info(f"validate_user_id: outcome=failure, reason=invalid_length, length={id_length}")
            return (False, None, msg)

        try:
            # Query Supabase 'users_voice' table for the spoken ID
            response = self.supabase.table("users_voice")\
                .select("user_id")\
                .eq("user_id", spoken_user_id)\
                .execute()

            # Check if user was found
            if not response.data or len(response.data) == 0:
                logger.info(f"validate_user_id: outcome=failure, reason=not_found_in_db, user_id='{spoken_user_id}'")
                return (
                    False,
                    None,
                    f"I heard {spoken_user_id}, but I couldn't find that ID. Could you try saying it digit by digit?"
                )

            # User found — extract the validated ID
            db_user_id = str(response.data[0]['user_id'])
            logger.info(f"validate_user_id: outcome=success, user_id='{db_user_id}'")

            return (
                True,
                db_user_id,
                "Thanks! I've confirmed your account. How can I help you today?"
            )

        except Exception as exc:
            logger.exception("validate_user DB query failed")
            logger.info(f"validate_user_id: outcome=failure, reason=db_exception")
            return (
                False,
                None,
                "I'm having trouble verifying your ID right now. Please try again."
            )


# Singleton instance — initialized in main.py after Supabase client is created
voice_auth_service: Optional[VoiceAuthService] = None


def init_voice_auth_service(supabase_client: Optional[Client]) -> VoiceAuthService:
    """
    Initialize the voice auth service singleton with a Supabase client.
    Called once at startup from main.py.
    """
    global voice_auth_service
    voice_auth_service = VoiceAuthService(supabase_client)
    return voice_auth_service
