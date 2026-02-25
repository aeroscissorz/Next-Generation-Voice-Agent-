"""
Voice Tools Configuration
OpenAI Realtime API tool definitions
"""

VOICE_TOOLS = [
    {
        "type": "function",
        "name": "validate_user",
        "description": "Validate a user's identity by their User ID. Must be called before any support queries.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The user ID spoken by the caller"
                }
            },
            "required": ["user_id"]
        }
    },
    {
        "type": "function",
        "name": "forward_to_backend",
        "description": "Forward a user query to the backend support system for billing, invoices, payments, support tickets, outages, roaming, wallet, and account queries.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "A clear natural-language description of what the user needs"
                }
            },
            "required": ["message"]
        }
    }
]
