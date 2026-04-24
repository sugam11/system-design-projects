import os
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.environ["SERPAPI_KEY"]
DATABASE_URL = os.environ["DATABASE_URL"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

ROUTES = [
    {
        "origin": "RDU",
        "destination": "SFO",
        "label": "RDU → SFO",
        "trip_type": 2,        # 1 = round trip, 2 = one way
        "days_out_start": 7,   # search departures starting 7 days from now
        "days_out_end": 90,    # up to 90 days out
        "date_step": 7,        # check every 7th day in that window
    },
]

DEAL_THRESHOLD = 0.70        # alert if price < 70% of typical low (i.e. 30%+ off)
MIN_HISTORY_DAYS = 7         # don't alert until we have 7 days of our own data
ALERT_COOLDOWN_HOURS = 24    # don't re-alert same route+date within 24 hours
