from voice_agents_adk.tools.data_store import load_data

def get_user_invoices(user_id: str):
    data = load_data()
    return [
        invoice
        for invoice in data["billing"]["invoices"]
        if invoice["user_id"] == user_id
    ]

def get_payment_methods(user_id: str):
    data = load_data()
    return data["billing"]["payment_methods"].get(user_id, [])
