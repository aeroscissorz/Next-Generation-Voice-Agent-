import os
from supabase import create_client
from datetime import datetime

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY"),
)

def get_user_invoices(user_id: str):
    res = (
        supabase
        .table("invoices")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    return res.data or []

def get_user_invoices_breakdown(invoice_id: str):
    res = (
        supabase
        .table("invoice_breakdown")
        .select("*")
        .eq("invoice_id", invoice_id)
        .execute()
    )
    return res.data or []

def check_roaming_status(user_id: str):
    res = (
        supabase
        .table("roaming")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    return res.data or []

def check_roaming_status_monthwise(user_id: str,month: str, year:str):
    res = (
        supabase
        .table("roaming")
        .select("*")
        .eq("user_id", user_id)
        .eq("month", month)
        .eq("year", year)
        .execute()
    )
    return res.data or []

def update_roaming_status_monthwise(user_id: str,month: str, year:str):
    res = (
        supabase
        .table("roaming")
        .update({"roaming_status": "No"}) 
        .eq("user_id", user_id)
        .eq("month", month)
        .eq("year", year)
        .execute()
    )
    return res.data 

def get_payment_methods(user_id: str):
    res = (
        supabase
        .table("payment_methods")
        .select("methods")
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    return res.data["methods"] if res.data else []


def check_wallet_amount_settlement(user_id: str,invoice_id: str):
    res = (
        supabase
        .table("wallet_amount")
        .select("*")
        .eq("user_id", user_id)
        .eq("invoice_id", invoice_id)
        .execute()
    )
    return res.data or []

def get_wallet_amount_Already_Settled(user_id: str):
    res = (
        supabase
        .table("wallet_amount")
        .select("*")
        .eq("user_id", user_id)
        .eq("settled", "Yes")
        .execute()
    )
    return res.data or []

def create_wallet_entry(user_id: str,invoice_id: str):
    res = (
        supabase
        .table("wallet_amount")
        .insert({
            "user_id": user_id,
            "amount": "300",
            "settled": "Yes",
            "invoice_id":invoice_id
        })
        .execute()
    )
    return res.data

def update_wallet_amount(user_id: str,invoice_id: str):
    res = (
        supabase
        .table("wallet_amount")
        .update({
            "amount": "1400",
            "settled_date": datetime.now().strftime("%Y-%m-%d"),  # Sets the current date
            "settled": "Yes"
        }) 
        .eq("user_id", user_id)        # Filter: which user
        .eq("invoice_id", invoice_id)  # Filter: specific invoice
        .execute()
    )
    return res.data