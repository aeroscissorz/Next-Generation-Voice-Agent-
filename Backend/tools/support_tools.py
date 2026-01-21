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


def get_open_tickets(user_id: str):
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


def check_outage(area: str):
    supabase = get_supabase()
    res = (
        supabase
        .table("outages")
        .select("*")
        .eq("area", area)
        .execute()
    )
    return res.data or []
