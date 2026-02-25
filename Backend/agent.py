import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent

from instructions import UNIFIED_INSTRUCTION

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

from tools.support_tools import (
    get_open_tickets,
    check_outage,
)

from tools.knowledge_tools import search_company_knowledge

load_dotenv()

MODEL_NAME = os.environ.get("GOOGLE_GENAI_MODEL")

root_agent = LlmAgent(
    name="Support_Agent",
    model=MODEL_NAME,
    instruction=UNIFIED_INSTRUCTION,
    tools=[
        # Billing
        get_user_invoices,
        get_payment_methods,
        get_user_invoices_breakdown,
        check_roaming_status,
        check_roaming_status_monthwise,
        update_roaming_status_monthwise,
        check_wallet_amount_settlement,
        update_wallet_amount,
        create_wallet_entry,
        # Support
        get_open_tickets,
        check_outage,
        # Knowledge
        search_company_knowledge,
    ],
)
