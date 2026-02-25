import os
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
import time

load_dotenv(override=True)

_supabase = None
_query_cache: dict[str, tuple[float, any]] = {}
QUERY_CACHE_TTL = 300  # 5 minutes for billing data

def _cache_get(key: str):
    """Get from cache if not expired."""
    if key in _query_cache:
        cached_time, data = _query_cache[key]
        if time.time() - cached_time < QUERY_CACHE_TTL:
            return data
    return None

def _cache_set(key: str, data):
    """Store in cache."""
    _query_cache[key] = (time.time(), data)
    if len(_query_cache) > 200:
        oldest = next(iter(_query_cache))
        del _query_cache[oldest]

_supabase = None

def get_supabase():
    global _supabase
    if _supabase is None:
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL or SUPABASE_SERVICE_KEY missing")

        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase


def get_user_invoices(user_id: str):
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
                    pass  # Non-critical, skip silently

        return data
    except Exception as e:
        print(f"Error fetching invoices: {e}")
        return [{
            "invoice_id": "INV-001",
            "user_id": user_id,
            "amount": 45.99,
            "status": "paid",
            "date": "2024-01-15"
        }]


def get_payment_methods(user_id: str):
    try:
        supabase = get_supabase()
        res = (
            supabase
            .table("payment_methods")
            .select("methods")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        return res.data["methods"] if res.data else []
    except Exception as e:
        print(f"Error fetching payment methods: {e}")
        # Return mock data
        return ["Credit Card ending in 1234", "PayPal"]


def get_user_invoices_breakdown(invoice_id: str):
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
        # Return mock breakdown
        return [{
            "item": "Monthly Service",
            "amount": 35.99,
            "invoice_id": invoice_id
        }, {
            "item": "Data Overage",
            "amount": 10.00,
            "invoice_id": invoice_id
        }]


def check_roaming_status(user_id: str):
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


def check_wallet_amount_settlement(user_id: str, invoice_id: str):
    try:
        supabase = get_supabase()
        return (
            supabase
            .table("wallet_amount")
            .select("*")
            .eq("user_id", user_id)
            .eq("invoice_id", invoice_id)
            .execute()
            .data
            or []
        )
    except Exception as e:
        print(f"Error checking wallet settlement: {e}")
        return []


def create_wallet_entry(user_id: str, invoice_id: str):
    try:
        supabase = get_supabase()
        return (
            supabase
            .table("wallet_amount")
            .insert({
                "user_id": user_id,
                "amount": "700",
                "settled": "No",
                "settled_date": datetime.now().strftime("%Y-%m-%d"),
                "id":1,
                "invoice_id": invoice_id
            })
            .execute()
            .data
        )
    except Exception as e:
        print(f"Error creating wallet entry: {e}")
        return {"success": False, "error": str(e)}


def update_wallet_amount(user_id: str, invoice_id: str):
    try:
        supabase = get_supabase()
        return (
            supabase
            .table("wallet_amount")
            .update({
                "amount": "700",
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
