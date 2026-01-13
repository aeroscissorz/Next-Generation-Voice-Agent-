import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent

from voice_agents_adk.instructions import (
    ROOT_INSTRUCTION,
    SUPPORT_INSTRUCTION,
    BILLING_INSTRUCTION,
)

from voice_agents_adk.tools.billing_tools import (
    get_user_invoices,
    get_payment_methods,
)

from voice_agents_adk.tools.support_tools import (
    get_open_tickets,
    check_outage,
)

load_dotenv()

MODEL_NAME = os.environ.get("GOOGLE_GENAI_MODEL")

support_agent = LlmAgent(
    name="Support_Agent",
    model=MODEL_NAME,
    instruction=SUPPORT_INSTRUCTION,
    tools=[get_open_tickets, check_outage],

)

billing_agent = LlmAgent(
    name="Billing_Agent",
    model=MODEL_NAME,
    instruction=BILLING_INSTRUCTION,
    tools=[get_user_invoices, get_payment_methods],

)


root_agent = LlmAgent(
    name="Root_Agent",
    model=MODEL_NAME,
    instruction=ROOT_INSTRUCTION,
    sub_agents=[support_agent, billing_agent]
)
