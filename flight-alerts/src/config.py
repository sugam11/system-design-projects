import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.environ["SERPAPI_KEY"]
DATABASE_URL = os.environ["DATABASE_URL"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

ROUTES_PATH = Path(__file__).resolve().parent.parent / "routes.json"
ROUTES = json.loads(ROUTES_PATH.read_text())

DEAL_THRESHOLD = 0.70  # alert if price < 70% of typical low (i.e. 30%+ off)
MIN_HISTORY_DAYS = 7  # don't alert until we have 7 days of our own data
ALERT_COOLDOWN_HOURS = 24  # don't re-alert same route+date within 24 hours
