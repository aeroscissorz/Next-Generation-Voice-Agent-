"""
Agent Definition Module
=======================
Defines the root LLM agent using Google's Agent Development Kit (ADK).

Architecture:
  - This is the core AI agent that powers the telecom customer support system.
  - Uses Google Gemini as the underlying LLM (model name loaded from env).
  - The agent is configured with a unified instruction prompt (from instructions.py)
    and a set of callable tools (from tools/ directory).
  - The agent is stateless per-request; session state is managed by the Runner
    in main.py via InMemorySessionService.

Tool Categories:
  1. Billing Tools   — invoice lookup, breakdowns, roaming, wallet, payments, promise dates
  2. Support Tools   — open tickets, outage checks, service status
  3. Knowledge Tools — semantic search over company policy docs (RAG via pgvector)

The agent decides which tools to call based on the user's message and the
instruction prompt's decision tree (e.g., outage refund flow, bill overdue flow).
"""

import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent

# Unified instruction prompt — contains all business logic, tone guidelines,
# and multi-step flow definitions (outage refund, bill overdue, payment, etc.)
from instructions import UNIFIED_INSTRUCTION

# --- Billing Tools ---
# Each function maps to a Supabase query; the agent calls them by name.
from tools.billing_tools import (
    get_user_invoices,              # Fetch all invoices for a user
    get_user_invoices_breakdown,    # Detailed line items for a specific invoice
    check_roaming_status,           # Current roaming status (all months)
    check_roaming_status_monthwise, # Roaming status for a specific month/year
    update_roaming_status_monthwise,# Disable roaming for a specific month/year
    check_wallet_amount_settlement, # Check unsettled wallet credits
    update_wallet_amount,           # Update an existing wallet credit entry
    create_wallet_entry,            # Create a new wallet credit (e.g., outage refund)
    make_payment,                   # Process payment — marks invoice as Paid
    set_promise_date,               # Set a "Promise to Pay" date on an invoice
    get_bill_overdue_date,          # Get the overdue date for a specific invoice
    set_settle_wallet_amount,       # Mark wallet credits as settled (used during payment)
    get_promise_date                # Retrieve the current promise date for an invoice
)

# --- Support Tools ---
from tools.support_tools import (
    get_open_tickets,       # List open support tickets for a user
    check_outage,           # Check outage records for a geographic area
    is_user_service_active  # Check if user's subscription service is active
)

# --- Knowledge Tools (RAG) ---
from tools.knowledge_tools import search_company_knowledge  # Semantic search over company KB

load_dotenv()

# Model name is configurable via environment variable (e.g., "gemini-2.5-flash")
MODEL_NAME = os.environ.get("GOOGLE_GENAI_MODEL")

# ─── Root Agent ───────────────────────────────────────────────────────────────
# This is the single agent instance used by the Runner in main.py.
# ADK's LlmAgent handles:
#   - Sending the instruction + conversation history + tool definitions to Gemini
#   - Parsing Gemini's tool-call requests and executing the matching Python functions
#   - Feeding tool results back to Gemini for the next reasoning step
#   - Returning the final text response when Gemini decides it's done
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
        # Knowledge (RAG)
        search_company_knowledge,
        # Payment & Promise
        make_payment,
        set_promise_date,
        get_bill_overdue_date,
        is_user_service_active,
        set_settle_wallet_amount,
        get_promise_date
    ],
)
