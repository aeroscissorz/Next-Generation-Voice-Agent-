"""
Support Tools Module
====================
Supabase-backed tool functions for customer support operations.
These are registered as callable tools on the LLM agent.

Database Tables Used:
  - support_tickets  — open/closed support tickets per user
  - outages          — outage records keyed by geographic area
  - user_services    — subscription service status per user

These tools are simpler than billing tools (no caching, no write operations
except through the agent's billing tools for refund processing).
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv(override=True)

# ─── Supabase Client (Lazy Singleton) ────────────────────────────────────────
_supabase = None

def get_supabase():
    """
    Lazy-initialize and return the Supabase client singleton.
    Separate from billing_tools' client — each module manages its own connection.
    """
    global _supabase
    if _supabase is None:
        _supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_KEY"),
        )
    return _supabase


def get_open_tickets(user_id: str):
    """
    Fetch all open support tickets for a user.
    Filters by status="open" in the 'support_tickets' table.

    Business rule: Open tickets must be resolved before processing
    outage compensation (enforced by the agent instruction, not here).

    Returns mock data on error so the agent can still respond.
    """
    try:
        supabase = get_supabase()
        res = (
            supabase
            .table("support_tickets")
            .select("*")
            .eq("user_id", user_id)
            .eq("status", "open")
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"Error fetching support tickets: {e}")
        # Fallback mock data for graceful degradation
        return [{
            "ticket_id": "TKT-001",
            "user_id": user_id,
            "subject": "Account access issue",
            "status": "open",
            "created_at": "2024-01-20"
        }]


def check_outage(area: str):
    """
    Check for outage records in a specific geographic area.
    Queries the 'outages' table filtered by area name.

    The agent gets the area from the user's invoice data (not from the user directly).
    Flow: get_user_invoices → extract area → check_outage(area)

    Returns outage records with dates, duration, and area info.
    Used in the Outage Refund Flow to determine if a refund is warranted.
    """
    try:
        supabase = get_supabase()
        res = (
            supabase
            .table("outages")
            .select("*")
            .eq("area", area)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"Error checking outages: {e}")
        return []
    

def is_user_service_active(user_id: str):
    """
    Check if the user's subscription service is currently active.
    Queries the 'user_services' table for the is_subscription_service_active flag.

    Used by the agent to verify service status before certain operations
    (e.g., confirming service is still active during overdue bill discussions).
    """
    try:
        supabase = get_supabase()
        res = (
            supabase
            .table("user_services")
            .select("is_subscription_service_active")
            .eq("user_id", user_id)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"Error checking is_user_service_active: {e}")
        return []
