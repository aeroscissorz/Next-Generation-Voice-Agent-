import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent

from instructions import UNIFIED_INSTRUCTION

from tools.billing_tools import (
    get_user_invoices,
    get_user_invoices_breakdown,
    check_roaming_status,
    check_roaming_status_monthwise,
    update_roaming_status_monthwise,
    check_wallet_amount_settlement,
    update_wallet_amount,
    create_wallet_entry,
    make_payment,
    set_promise_date,
    get_bill_overdue_date,
    set_settle_wallet_amount,
    get_promise_date
)

from tools.support_tools import (
    get_open_tickets,
    check_outage,
    is_user_service_active
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
        make_payment,
        set_promise_date,
        get_bill_overdue_date,
        is_user_service_active,
        set_settle_wallet_amount,
        get_promise_date
    ],
)
