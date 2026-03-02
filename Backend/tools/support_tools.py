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
        # Return mock data
        return [{
            "ticket_id": "TKT-001",
            "user_id": user_id,
            "subject": "Account access issue",
            "status": "open",
            "created_at": "2024-01-20"
        }]


def check_outage(area: str):
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
        # Return no outages
        return []
    

def is_user_service_active(user_id: str):
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
        # Return no outages
        return []


