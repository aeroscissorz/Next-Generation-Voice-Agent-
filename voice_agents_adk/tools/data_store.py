import json
from pathlib import Path

DATA_FILE = Path(__file__).parent.parent / "data" / "mock_data.json"

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)
