"""
Billing Tools Module
====================
Supabase-backed tool functions for billing operations. These are registered
as callable tools on the LLM agent — Gemini can invoke them by name during
the agent loop.

Database Tables Used:
  - invoices           — user invoices (amount, status, overdue_date, promise_date, area)
  - invoice_breakdown  — line-item breakdown per invoice (service charges, data, roaming, etc.)
  - roaming            — per-month roaming status per user
  - wallet_amount      — wallet credits (used for outage refunds, settled during payment)

Caching Strategy:
  - In-memory dict cache (_query_cache) with 5-minute TTL
  - Keyed by "{table}:{id}" (e.g., "invoices:42", "breakdown:INV-001")
  - Max 200 entries; evicts oldest on overflow (FIFO)
  - get_user_invoices() also prefetches breakdowns for all invoices eagerly
  - Cache is warmed on login via the /prefetch endpoint

Error Handling:
  - All functions return fallback/mock data on Supabase errors so the agent
    can still respond (graceful degradation). In production, these fallbacks
    should be replaced with proper error propagation.
"""

import os
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
import time

load_dotenv(override=True)

# ─── Supabase Client (Lazy Singleton) ────────────────────────────────────────
_supabase = None

def get_supabase():
    """
    Lazy-initialize and return the Supabase client singleton.
    Reads SUPABASE_URL and SUPABASE_SERVICE_KEY from environment.
    Raises ValueError if either is missing.
    """
    global _supabase
    if _supabase is None:
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL or SUPABASE_SERVICE_KEY missing")

        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase


# ─── In-Memory Query Cache ───────────────────────────────────────────────────
# Simple TTL cache to avoid redundant Supabase queries within a conversation.
# The agent often calls get_user_invoices multiple times in a single flow
# (e.g., outage check → refund → payment), so caching saves ~200-500ms per hit.
_query_cache: dict[str, tuple[float, any]] = {}
QUERY_CACHE_TTL = 300  # 5 minutes — long enough for a full conversation

def _cache_get(key: str):
    """Return cached data if it exists and hasn't expired, else None."""
    if key in _query_cache:
        cached_time, data = _query_cache[key]
        if time.time() - cached_time < QUERY_CACHE_TTL:
            return data
    return None

def _cache_set(key: str, data):
    """Store data in cache. Evicts oldest entry if cache exceeds 200 items."""
    _query_cache[key] = (time.time(), data)
    if len(_query_cache) > 200:
        oldest = next(iter(_query_cache))
        del _query_cache[oldest]


# ─── Invoice Tools ───────────────────────────────────────────────────────────

def get_user_invoices(user_id: str):
    """
    Fetch all invoices for a user from the 'invoices' table.

    Returns a list of invoice dicts with fields like:
      invoice_id, user_id, amount, status, overdue_date, promise_date, area,
      is_eligible_promise_to_pay, etc.

    Side effect: Eagerly prefetches invoice breakdowns for all returned invoices
    and stores them in cache. This means a follow-up call to
    get_user_invoices_breakdown() will be an instant cache hit.

    Called by the agent for: bill overview, outage area lookup, overdue flow,
    payment flow, and most other billing-related queries.
    """
    cached = _cache_get(f"invoices:{user_id}")
    if cached is not None:
        return cached
    try:
        supabase = get_supabase()
        data = (
            supabase
            .table("invoices")
            .select("*")
            .eq("user_id", user_id)
            .execute()
            .data
            or []
        )
        _cache_set(f"invoices:{user_id}", data)

        # Prefetch breakdowns for all invoices so follow-up queries are instant
        for inv in data:
            inv_id = str(inv.get("invoice_id", ""))
            if inv_id and _cache_get(f"breakdown:{inv_id}") is None:
                try:
                    bd = (
                        supabase
                        .table("invoice_breakdown")
                        .select("*")
                        .eq("invoice_id", inv_id)
                        .execute()
                        .data or []
                    )
                    _cache_set(f"breakdown:{inv_id}", bd)
                    print(f"⚡ Prefetched breakdown for invoice {inv_id}")
                except Exception:
                    pass  # Non-critical — skip silently

        return data
    except Exception as e:
        print(f"Error fetching invoices: {e}")
        # Fallback mock data so the agent can still respond
        return [{
            "invoice_id": "INV-001",
            "user_id": user_id,
            "amount": 45.99,
            "status": "paid",
            "date": "2024-01-15"
        }]


def get_user_invoices_breakdown(invoice_id: str):
    """
    Fetch detailed line items for a specific invoice from 'invoice_breakdown' table.

    Returns a list of line-item dicts (e.g., Monthly Service, Data Overage, Roaming).
    The agent uses this when the user asks "why is my bill so high?" or
    "show me the breakdown for invoice X".

    IMPORTANT: The breakdown already includes ALL charges (including roaming).
    The agent instruction explicitly forbids adding roaming charges from other tools.
    """
    cached = _cache_get(f"breakdown:{invoice_id}")
    if cached is not None:
        return cached
    try:
        supabase = get_supabase()
        data = (
            supabase
            .table("invoice_breakdown")
            .select("*")
            .eq("invoice_id", invoice_id)
            .execute()
            .data
            or []
        )
        _cache_set(f"breakdown:{invoice_id}", data)
        return data
    except Exception as e:
        print(f"Error fetching invoice breakdown: {e}")
        # Fallback mock data
        return [{
            "item": "Monthly Service",
            "amount": 35.99,
            "invoice_id": invoice_id
        }, {
            "item": "Data Overage",
            "amount": 10.00,
            "invoice_id": invoice_id
        }]


# ─── Roaming Tools ───────────────────────────────────────────────────────────

def check_roaming_status(user_id: str):
    """
    Check the current roaming status for a user (all months).
    Returns a list of roaming records from the 'roaming' table.
    Only called when the user explicitly asks about roaming — NOT during bill breakdowns.
    """
    cached = _cache_get(f"roaming:{user_id}")
    if cached is not None:
        return cached
    try:
        supabase = get_supabase()
        data = (
            supabase
            .table("roaming")
            .select("*")
            .eq("user_id", user_id)
            .execute()
            .data
            or []
        )
        _cache_set(f"roaming:{user_id}", data)
        return data
    except Exception as e:
        print(f"Error checking roaming status: {e}")
        return []


def check_roaming_status_monthwise(user_id: str, month: str, year: str):
    """
    Check roaming status for a specific month and year.
    Used when the user asks about roaming for a particular billing period.
    Not cached (specific month queries are rare).
    """
    try:
        supabase = get_supabase()
        return (
            supabase
            .table("roaming")
            .select("*")
            .eq("user_id", user_id)
            .eq("month", month)
            .eq("year", year)
            .execute()
            .data
            or []
        )
    except Exception as e:
        print(f"Error checking roaming status monthwise: {e}")
        return []


def update_roaming_status_monthwise(user_id: str, month: str, year: str):
    """
    Disable roaming for a specific month/year by setting roaming_status to "No".
    The agent calls this for current + next month when the user asks to disable roaming.
    This is a WRITE operation — modifies the 'roaming' table.
    """
    try:
        supabase = get_supabase()
        return (
            supabase
            .table("roaming")
            .update({"roaming_status": "No"})
            .eq("user_id", user_id)
            .eq("month", month)
            .eq("year", year)
            .execute()
            .data
        )
    except Exception as e:
        print(f"Error updating roaming status: {e}")
        return {"success": False, "error": str(e)}


# ─── Wallet Tools ────────────────────────────────────────────────────────────
# The wallet stores credits (e.g., outage refunds) that can be applied to future payments.
# Wallet entries have a "settled" flag — "No" means the credit hasn't been used yet.

def check_wallet_amount_settlement(user_id: str):
    """
    Check for unsettled wallet credits for a user.
    Returns a list of wallet entries where settled="No".

    Used in two flows:
      1. Outage refund — to check if a credit already exists before creating a new one
      2. Payment flow — to offer the user the option to apply wallet credit to their bill
    """
    try:
        supabase = get_supabase()
        return (
            supabase
            .table("wallet_amount")
            .select("*")
            .eq("user_id", user_id)
            .eq("settled", "No")
            .execute()
            .data
            or []
        )
    except Exception as e:
        print(f"Error checking wallet settlement: {e}")
        return []


def create_wallet_entry(user_id: str, invoice_id: str, amount: str):
    """
    Create a new wallet credit entry (e.g., for an outage refund).
    Inserts into the 'wallet_amount' table with settled="No".

    Called during the outage refund flow when no existing unsettled entry exists.
    The amount is the calculated refund: (outage_days / days_in_month) × invoice_amount.
    """
    try:
        supabase = get_supabase()
        return (
            supabase
            .table("wallet_amount")
            .insert({
                "user_id": user_id,
                "amount": amount,
                "settled": "No",
                "settled_date": datetime.now().strftime("%Y-%m-%d"),
                "id": 1,
                "invoice_id": invoice_id
            })
            .execute()
            .data
        )
    except Exception as e:
        print(f"Error creating wallet entry: {e}")
        return {"success": False, "error": str(e)}


def update_wallet_amount(user_id: str, invoice_id: str, amount: str):
    """
    Update an existing wallet credit entry with a new amount.
    Used during the outage refund flow when an unsettled entry already exists
    for this user+invoice — updates the amount rather than creating a duplicate.
    """
    try:
        supabase = get_supabase()
        return (
            supabase
            .table("wallet_amount")
            .update({
                "amount": amount,
                "settled_date": datetime.now().strftime("%Y-%m-%d"),
                "settled": "No"
            })
            .eq("user_id", user_id)
            .eq("invoice_id", invoice_id)
            .execute()
            .data
        )
    except Exception as e:
        print(f"Error updating wallet amount: {e}")
        return {"success": False, "error": str(e)}


def set_settle_wallet_amount(user_id: str):
    """
    Mark all wallet credits for a user as settled (settled="Yes").
    Called during the payment flow AFTER make_payment succeeds,
    when the user chose to apply their wallet credit to the bill.
    """
    try:
        supabase = get_supabase()
        return (
            supabase
            .table("wallet_amount")
            .update({
                "settled_date": datetime.now().strftime("%Y-%m-%d"),
                "settled": "Yes"
            })
            .eq("user_id", user_id)
            .execute()
            .data
        )
    except Exception as e:
        print(f"Error updating wallet amount: {e}")
        return {"success": False, "error": str(e)}


# ─── Payment Tools ───────────────────────────────────────────────────────────

def make_payment(user_id: str, invoice_id: str):
    """
    Process payment for an invoice — marks it as "Paid" and clears
    overdue_date and promise_date fields.

    This is the final step in the payment flow. The agent only calls this
    after receiving explicit user confirmation ("yes", "go ahead", etc.).

    IMPORTANT: The agent instruction requires a 2-step confirmation:
      1. Ask about wallet credit usage
      2. Show payment breakdown and ask "Shall I go ahead?"
    Only after both confirmations does the agent call this function.
    """
    try:
        supabase = get_supabase()
        return (
            supabase
            .table("invoices")
            .update({
                "status": "Paid",
                "overdue_date": None,
                "promise_date": None
                })
            .eq("user_id", user_id)
            .eq("invoice_id", invoice_id)
            .execute()
            .data
        )
    except Exception as e:
        print(f"Error updating paid status of invoice: {e}")
        return {"success": False, "error": str(e)}
    

# ─── Promise-to-Pay Tools ───────────────────────────────────────────────────

def set_promise_date(user_id: str, invoice_id: str, promise_date):
    """
    Set a "Promise to Pay" date on an invoice.

    Business Rules:
      - The promise date must be within 7 days of the invoice's overdue_date
      - If the date exceeds the 7-day window, returns an error with the max allowed date
      - The agent relays this error to the user and asks them to pick a new date

    Date Handling:
      - Accepts string or datetime input
      - Normalizes to "YYYY-MM-DD" format using dateutil.parser
      - Validates against overdue_date + 7 days before writing to DB

    Called during:
      - Initial Promise to Pay setup (user can't pay today)
      - Promise date extension (user wants to move their existing date)
    """
    try:
        from dateutil import parser as dateparser
        from datetime import timedelta

        # Normalise to "YYYY-MM-DD" regardless of input type/format
        if isinstance(promise_date, str):
            date_str = dateparser.parse(promise_date).strftime("%Y-%m-%d")
        else:
            date_str = promise_date.strftime("%Y-%m-%d")

        # Enforce: promise date must not exceed overdue_date + 7 days
        supabase = get_supabase()
        invoice = (
            supabase.table("invoices")
            .select("overdue_date")
            .eq("invoice_id", invoice_id)
            .single()
            .execute()
            .data
        )
        if invoice and invoice.get("overdue_date"):
            due = dateparser.parse(str(invoice["overdue_date"])).date()
            max_date = due + timedelta(days=7)
            promise = dateparser.parse(date_str).date()
            if promise > max_date:
                # Return a structured error so the agent can relay the max date
                return {
                    "success": False,
                    "error": f"Promise date cannot be later than {max_date.strftime('%B %-d, %Y')} (7 days from your due date of {due.strftime('%B %-d, %Y')}). Please choose a date on or before {max_date.strftime('%B %-d, %Y')}."
                }

        # Write the promise date to the invoice
        return (
            supabase.table("invoices")
            .update({"promise_date": date_str})
            .eq("user_id", user_id)
            .eq("invoice_id", invoice_id)
            .execute()
            .data
        )
    except Exception as e:
        print(f"Error updating promise date of invoice: {e}")
        return {"success": False, "error": str(e)}
    

def get_bill_overdue_date(user_id: str, invoice_id: str):
    """
    Get the overdue date for a specific invoice.
    Used by the agent to determine the 7-day window for Promise to Pay.
    """
    try:
        supabase = get_supabase()
        return (
            supabase
            .table("invoices")
            .select("overdue_date")
            .eq("user_id", user_id)
            .eq("invoice_id", invoice_id)
            .execute()
            .data
            or []
        )
    except Exception as e:
        print(f"Error checking check_bill_overdue_date: {e}")
        return []


def get_promise_date(user_id: str, invoice_id: str):
    """
    Retrieve the current promise date for a specific invoice.
    Used in the Promise Date Extension sub-flow to determine the
    current date before calculating the new extended date.
    """
    try:
        supabase = get_supabase()
        return (
            supabase
            .table("invoices")
            .select("promise_date")
            .eq("user_id", user_id)
            .eq("invoice_id", invoice_id)
            .execute()
            .data
            or []
        )
    except Exception as e:
        print(f"Error checking get_promise_date: {e}")
        return []
