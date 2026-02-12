"""
Voice Tools Configuration
OpenAI Realtime API tool definitions for voice interactions
"""

from typing import List, Dict, Any


def get_voice_tools() -> List[Dict[str, Any]]:
    """
    Get voice tools configuration for OpenAI Realtime API.
    
    Returns:
        List of tool definitions
    """
    return [
        {
            "type": "function",
            "name": "validate_user",
            "description": "Validate a user's identity by their User ID. Must be called before any support queries are allowed.",
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
            "description": "Forward a user query to the backend support system. Use for billing, invoices, payments, support tickets, outages, roaming, wallet, and all account queries.",
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


# Voice tools constant for backward compatibility
VOICE_TOOLS = get_voice_tools()


def add_custom_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a custom tool definition.
    
    Args:
        name: Tool name
        description: Tool description
        parameters: Tool parameters (JSON schema)
    
    Returns:
        Tool definition dictionary
    
    Example:
        >>> tool = add_custom_tool(
        ...     name="check_weather",
        ...     description="Check weather for a location",
        ...     parameters={
        ...         "type": "object",
        ...         "properties": {
        ...             "location": {"type": "string"}
        ...         },
        ...         "required": ["location"]
        ...     }
        ... )
    """
    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": parameters
    }


def get_tool_names() -> List[str]:
    """
    Get list of available tool names.
    
    Returns:
        List of tool names
    """
    return [tool["name"] for tool in VOICE_TOOLS]


def get_tool_by_name(name: str) -> Dict[str, Any]:
    """
    Get tool definition by name.
    
    Args:
        name: Tool name
    
    Returns:
        Tool definition or None if not found
    """
    for tool in VOICE_TOOLS:
        if tool["name"] == name:
            return tool
    return None
