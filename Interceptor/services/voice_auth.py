"""
Voice Authentication Service
Manages voice authentication state and user validation
"""

import logging
from typing import Dict, Optional
from supabase import Client

logger = logging.getLogger("voice_auth")


class VoiceAuthService:
    """Manages voice authentication state"""
    
    def __init__(self, supabase_client: Optional[Client] = None):
        self.supabase = supabase_client
        
        # Session auth state - keyed by user_id (email from frontend)
        self._auth_state: Dict[str, bool] = {}
        
        # Maps email -> validated customer ID (e.g. "42")
        self._customer_id: Dict[str, str] = {}
    
    def is_authenticated(self, user_id: str) -> bool:
        """
        Check if user is authenticated.
        
        Args:
            user_id: User identifier (email)
        
        Returns:
            True if authenticated, False otherwise
        """
        return self._auth_state.get(user_id, False)
    
    def get_customer_id(self, user_id: str) -> Optional[str]:
        """
        Get validated customer ID for user.
        
        Args:
            user_id: User identifier (email)
        
        Returns:
            Customer ID if authenticated, None otherwise
        """
        return self._customer_id.get(user_id)
    
    def set_authenticated(self, user_id: str, customer_id: str) -> None:
        """
        Mark user as authenticated.
        
        Args:
            user_id: User identifier (email)
            customer_id: Validated customer ID
        """
        self._auth_state[user_id] = True
        self._customer_id[user_id] = customer_id
        logger.info(f"User authenticated: {user_id} -> customer_id: {customer_id}")
    
    def reset_auth(self, user_id: str) -> None:
        """
        Reset authentication state for user.
        
        Args:
            user_id: User identifier (email)
        """
        self._auth_state[user_id] = False
        self._customer_id.pop(user_id, None)
        logger.info(f"Auth reset for user: {user_id}")
    
    async def validate_user_id(self, spoken_user_id: str) -> tuple[bool, Optional[str], str]:
        """
        Validate user ID against Supabase database.
        
        Args:
            spoken_user_id: User ID from speech recognition
        
        Returns:
            Tuple of (authenticated, customer_id, message)
        """
        if not self.supabase:
            logger.error("Supabase not initialized; cannot validate user")
            return (
                False, 
                None, 
                "System error: Validation service unavailable"
            )
        
        # Ensure ID is numeric
        if not spoken_user_id.isdigit():
            logger.info(f"Validation failed: User ID '{spoken_user_id}' is not numeric")
            return (
                False,
                None,
                f"Invalid User ID format. I heard {spoken_user_id}, but IDs must be numeric."
            )
        
        try:
            # Check if ID exists in 'users_voice' table
            response = self.supabase.table("users_voice")\
                .select("user_id")\
                .eq("user_id", spoken_user_id)\
                .execute()
            
            # Check if user found
            if not response.data or len(response.data) == 0:
                logger.info(f"Validation failed for user_id={spoken_user_id} (not found in DB)")
                return (
                    False,
                    None,
                    f"I heard {spoken_user_id}, but I couldn't find that ID. Could you try saying it digit by digit?"
                )
            
            # User found
            db_user_id = str(response.data[0]['user_id'])
            logger.info(f"User validated successfully: {db_user_id}")
            
            return (
                True,
                db_user_id,
                "Thanks! I've confirmed your account. How can I help you today?"
            )
            
        except Exception as exc:
            logger.exception("validate_user DB query failed")
            return (
                False,
                None,
                "I'm having trouble verifying your ID right now. Please try again."
            )


# Singleton instance will be created in main.py after Supabase client is initialized
voice_auth_service: Optional[VoiceAuthService] = None


def init_voice_auth_service(supabase_client: Optional[Client]) -> VoiceAuthService:
    """
    Initialize voice auth service with Supabase client.
    
    Args:
        supabase_client: Supabase client instance
    
    Returns:
        VoiceAuthService instance
    """
    global voice_auth_service
    voice_auth_service = VoiceAuthService(supabase_client)
    return voice_auth_service
