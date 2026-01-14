import os
from supabase import create_client

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY"),
)

def get_open_tickets(user_id: str):
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
    res = (
        supabase
        .table("outages")
        .select("*")
        .eq("area", area)
        .execute()
    )
    return res.data or []
