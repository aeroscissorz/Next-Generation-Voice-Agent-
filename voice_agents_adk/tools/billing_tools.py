import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv(override=True)

_supabase = None

def get_supabase():
    global _supabase
    if _supabase is None:
        _supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_KEY"),
        )
    return _supabase


def get_user_invoices(user_id: str):
    supabase = get_supabase()
    res = (
        supabase
        .table("invoices")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    return res.data or []


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
