# flight-alerts

Cron job that polls Amadeus every 8 hours, stores fares in Neon (Postgres), and sends a Telegram alert when any fare drops >30% below the 30-day median for that route.

## Setup

1. Create a Neon project and get a `DATABASE_URL`.
2. Register an Amadeus developer app (`AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`).
3. Create a Telegram bot via `@BotFather` and get `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`.
4. Copy `.env.example` to `.env` and fill in values.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Schema is auto-applied on each run, or apply manually:

```bash
psql "$DATABASE_URL" -f schema.sql
```

## Run

```bash
python src/main.py
```

## Cron (Oracle ARM)

```
0 7,15,23 * * * /home/ubuntu/flight-alerts/venv/bin/python /home/ubuntu/flight-alerts/src/main.py
```
