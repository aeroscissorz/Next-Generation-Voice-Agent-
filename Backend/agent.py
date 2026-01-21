import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent

from instructions import (
    ROOT_INSTRUCTION,
    SUPPORT_INSTRUCTION,
    BILLING_INSTRUCTION,
)

from tools.billing_tools import (
    get_user_invoices,
    get_payment_methods,
    get_user_invoices_breakdown,
    check_roaming_status,
    check_roaming_status_monthwise,
    update_roaming_status_monthwise,
    check_wallet_amount_settlement,
    update_wallet_amount,
    create_wallet_entry,
)

from tools.memory_tools import (
    get_user_memory,
    update_user_memory,
)

from tools.support_tools import (
    get_open_tickets,
    check_outage,
)

from tools.knowledge_tools import search_company_knowledge


load_dotenv()

MODEL_NAME = os.environ.get("GOOGLE_GENAI_MODEL")

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
    tools=[get_user_invoices, get_payment_methods, search_company_knowledge, get_user_memory, update_user_memory,get_user_invoices_breakdown,
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
