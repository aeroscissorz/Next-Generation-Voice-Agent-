"""
Voice Tools Configuration
=========================
Defines the tool schemas sent to the OpenAI Realtime API when creating
a voice session. These tools are callable by the Realtime model during
a WebRTC voice conversation.

Tools:
  1. validate_user — Authenticate the caller by their spoken User ID.
     Must be called before any support queries. The Realtime model asks
     the caller for their ID, then calls this tool. The Interceptor
     validates against Supabase and returns success/failure.

  2. forward_to_backend — Forward a support query to the Backend agent.
     After authentication, the Realtime model calls this for any billing,
     invoice, payment, outage, roaming, or account query. The Interceptor
     injects voice context and proxies to the Backend's full agent loop.

The Frontend intercepts these tool calls from the WebRTC connection and
POSTs them to the Interceptor's /voice/tool-call endpoint.
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
