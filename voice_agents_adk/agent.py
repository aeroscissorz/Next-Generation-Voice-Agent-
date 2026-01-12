import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent

from voice_agents_adk.instructions import (
    ROOT_INSTRUCTION,
    SUPPORT_INSTRUCTION,
    BILLING_INSTRUCTION,
)

load_dotenv()

MODEL_NAME = os.environ.get("GOOGLE_GENAI_MODEL")

support_agent = LlmAgent(
    name="Support_Agent",
    model=MODEL_NAME,
    instruction=SUPPORT_INSTRUCTION,
)

billing_agent = LlmAgent(
    name="Billing_Agent",
    model=MODEL_NAME,
    instruction=BILLING_INSTRUCTION,
)


root_agent = LlmAgent(
    name="Root_Agent",
    model=MODEL_NAME,
    instruction=ROOT_INSTRUCTION,
    sub_agents=[support_agent, billing_agent]
)
