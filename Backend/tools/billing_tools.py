import os
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime

load_dotenv(override=True)

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
    supabase = get_supabase()
    return (
        supabase
        .table("invoices")
        .select("*")
        .eq("user_id", user_id)
        .execute()
        .data
        or []
    )


def get_payment_methods(user_id: str):
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


def get_user_invoices_breakdown(invoice_id: str):
    supabase = get_supabase()
    return (
        supabase
        .table("invoice_breakdown")
        .select("*")
        .eq("invoice_id", invoice_id)
        .execute()
        .data
        or []
    )


def check_roaming_status(user_id: str):
    supabase = get_supabase()
    return (
        supabase
        .table("roaming")
        .select("*")
        .eq("user_id", user_id)
        .execute()
        .data
        or []
    )


def check_roaming_status_monthwise(user_id: str, month: str, year: str):
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


def update_roaming_status_monthwise(user_id: str, month: str, year: str):
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


def check_wallet_amount_settlement(user_id: str, invoice_id: str):
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


def create_wallet_entry(user_id: str, invoice_id: str):
    supabase = get_supabase()
    return (
        supabase
        .table("wallet_amount")
        .insert({
            "user_id": user_id,
            "amount": "300",
            "settled": "Yes",
            "invoice_id": invoice_id
        })
        .execute()
        .data
    )


def update_wallet_amount(user_id: str, invoice_id: str):
    supabase = get_supabase()
    return (
        supabase
        .table("wallet_amount")
        .update({
            "amount": "1400",
            "settled_date": datetime.now().strftime("%Y-%m-%d"),
            "settled": "Yes"
        })
        .eq("user_id", user_id)
        .eq("invoice_id", invoice_id)
        .execute()
        .data
    )
