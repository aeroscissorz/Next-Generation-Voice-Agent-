import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent


try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
    MODEL_NAME = os.environ.get("GOOGLE_GENAI_MODEL","gemini-3-flash-preview")
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is missing from environment variables!")
except ImportError :
    print("Warning: python-dotenv is not installed. Ensured API key is set")
    MODEL_NAME = "gemini-3-flash-preview"

from voice_agents_adk.instructions import (
    ROOT_INSTRUCTION,
    SUPPORT_INSTRUCTION,
    BILLING_INSTRUCTION,
)

from voice_agents_adk.tools.billing_tools import (
    get_user_invoices,
    get_payment_methods,
    get_user_invoices_breakdown,
    check_roaming_status,
    check_roaming_status_monthwise,
    update_roaming_status_monthwise,
    check_wallet_amount_settlement,
    update_wallet_amount,
    create_wallet_entry,
    #get_wallet_amount_Not_Settled
)

from voice_agents_adk.tools.memory_tools import (
    get_user_memory,
    update_user_memory,
)

from voice_agents_adk.tools.support_tools import (
    get_open_tickets,
    check_outage,
)

from voice_agents_adk.tools.knowledge_tools import search_company_knowledge



support_agent = LlmAgent(
    name="Support_Agent",
    model=MODEL_NAME,
    instruction=SUPPORT_INSTRUCTION,
    tools=[get_open_tickets, check_outage, search_company_knowledge, get_user_memory, update_user_memory],

)

billing_agent = LlmAgent(
    name="Billing_Agent",
    model=MODEL_NAME,
    instruction=BILLING_INSTRUCTION,
    tools=[get_user_invoices, get_payment_methods, search_company_knowledge, get_user_memory, update_user_memory,
    get_user_invoices_breakdown,
    check_roaming_status,
    check_roaming_status_monthwise,
    update_roaming_status_monthwise,
   # get_wallet_amount_Not_Settled,
   # get_wallet_amount_Already_Settled,
   check_wallet_amount_settlement,
    update_wallet_amount,
    create_wallet_entry],

)


root_agent = LlmAgent(
    name="Root_Agent",
    model=MODEL_NAME,
    instruction=ROOT_INSTRUCTION,
    sub_agents=[support_agent, billing_agent]
)
