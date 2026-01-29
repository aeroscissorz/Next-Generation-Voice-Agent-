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
    try:
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
    except Exception as e:
        print(f"Error fetching invoices: {e}")
        # Return mock data for demo purposes
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
    try:
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
    try:
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
                "amount": "300",
                "settled": "Yes",
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
                "amount": "1400",
                "settled_date": datetime.now().strftime("%Y-%m-%d"),
                "settled": "Yes"
            })
            .eq("user_id", user_id)
            .eq("invoice_id", invoice_id)
            .execute()
            .data
        )
    except Exception as e:
        print(f"Error updating wallet amount: {e}")
        return {"success": False, "error": str(e)}
