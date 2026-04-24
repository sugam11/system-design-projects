import os
from dotenv import load_dotenv

load_dotenv()

AMADEUS_CLIENT_ID = os.environ["AMADEUS_CLIENT_ID"]
AMADEUS_CLIENT_SECRET = os.environ["AMADEUS_CLIENT_SECRET"]
AMADEUS_ENV = os.getenv("AMADEUS_ENV", "test")

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

DATABASE_URL = os.environ["DATABASE_URL"]

ROUTES = [
    {
        "origin": "SFO",
        "destination": "NRT",
        "search_days_out": [7, 14, 30, 45, 60, 75, 90],
        "max_results": 20,
    },
    {
        "origin": "SFO",
        "destination": "LHR",
        "search_days_out": [7, 14, 30, 45, 60, 75, 90],
        "max_results": 20,
    },
]

DEAL_THRESHOLD = 0.70
MIN_HISTORY_DAYS = 7
MEDIAN_WINDOW_DAYS = 30
ALERT_DEDUPE_HOURS = 24
