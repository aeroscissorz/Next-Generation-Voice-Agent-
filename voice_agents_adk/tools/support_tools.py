from voice_agents_adk.tools.data_store import load_data

def get_open_tickets(user_id: str):
    data = load_data()
    return [
        ticket
        for ticket in data["support"]["tickets"]
        if ticket["user_id"] == user_id and ticket["status"] == "open"
    ]

def check_outage(area: str):
    data = load_data()
    return [
        outage
        for outage in data["support"]["outages"]
        if outage["area"].lower() == area.lower()
    ]
