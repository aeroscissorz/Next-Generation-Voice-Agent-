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


def get_user_memory(user_id: str):
    supabase = get_supabase()
    response = (
        supabase
        .table("user_memory")
        .select("key, value")
        .eq("user_id", user_id)
        .execute()
    )

    if not response.data:
        return {}

    return {item["key"]: item["value"] for item in response.data}


def update_user_memory(user_id: str, key: str, value: str):
    supabase = get_supabase()
    supabase.table("user_memory").upsert({
        "user_id": user_id,
        "key": key,
        "value": value,
    }).execute()

    return {"status": "saved", "key": key, "value": value}
