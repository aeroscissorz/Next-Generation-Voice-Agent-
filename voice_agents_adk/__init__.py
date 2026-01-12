"""Marketing Agents SDK - Voice-enabled multi-agent routing system."""

from voice_agents_adk.agent import (
    root_agent,
    support_agent,
    billing_agent,
    MODEL_NAME,
)
from voice_agents_adk.instructions import (
    ROOT_INSTRUCTION,
    SUPPORT_INSTRUCTION,
    BILLING_INSTRUCTION,
)

__version__ = "0.1.0"

__all__ = [
    "root_agent",
    "support_agent",
    "billing_agent",
    "MODEL_NAME",
    "ROOT_INSTRUCTION",
    "SUPPORT_INSTRUCTION",
    "BILLING_INSTRUCTION",
]
