# flight-alerts

A personal flight price alert tool. Runs as a Python cron job on Oracle ARM, polls Google Flights prices via SerpApi 3x per day, stores every fare in Neon (Postgres), and sends a Telegram message when any fare drops significantly below the typical range.

No web server. No Docker. Just a Python script invoked by cron.

---

## One-time setup

### 1. Clone and create a virtualenv

```bash
git clone git@github.com:sugam11/system-design-projects.git
cd system-design-projects/flight-alerts
./setup.sh
```

`setup.sh` creates `./venv`, installs `requirements.txt`, and bootstraps `.env` from `.env.example`. On Debian/Ubuntu it will install `python3.X-venv` via apt if missing.

### 2. Get your credentials

- **SerpApi** — sign up at [serpapi.com](https://serpapi.com), copy `SERPAPI_KEY` from your dashboard. Free tier: 250 queries/month.
- **Neon** — create a project at [neon.tech](https://neon.tech), copy the connection string into `DATABASE_URL`.
- **Telegram bot** — message `@BotFather` on Telegram, run `/newbot`, follow the prompts, copy the token into `TELEGRAM_BOT_TOKEN`.
- **Telegram chat ID** — send any message to your new bot, then open:
  ```
  https://api.telegram.org/bot<TOKEN>/getUpdates
  ```
  Look for `"chat":{"id": <YOUR_CHAT_ID>}` in the response. Copy that number into `TELEGRAM_CHAT_ID`.

Edit `.env` with all four values.

### 3. Initialize the database

The schema auto-applies on the first `main.py` run. To do it manually:

```bash
psql "$DATABASE_URL" -f schema.sql
```

### 4. Smoke test

```bash
./venv/bin/python src/main.py
```

You should see log lines about fares fetched and saved. Check Neon's SQL editor for rows in the `fares` table.

### 5. Install the cron entry

```bash
crontab -e
```

Add:

```
0 7,15,23 * * * /home/ubuntu/flight-alerts/venv/bin/python /home/ubuntu/flight-alerts/src/main.py >> /home/ubuntu/flight-alerts/run.log 2>&1
```

Runs at 7am, 3pm, 11pm server time. All output goes to `run.log`.

---

## Adding or changing routes

Edit [`src/config.py`](src/config.py). Each route is a dict:

```python
{
    "origin": "RDU",           # IATA code
    "destination": "SFO",      # IATA code
    "label": "RDU → SFO",      # human-readable, used in logs
    "trip_type": 2,            # 1 = round trip, 2 = one way
    "days_out_start": 7,       # search window start (days from today)
    "days_out_end": 90,        # search window end
    "date_step": 7,            # step size (every Nth day)
}
```

Stay within the SerpApi free tier. For 2 routes × 13 dates × 3 runs/day × 30 days ≈ 234 calls/month. The 250-call cap is tight — don't add more routes without tightening the date window.

---

## Operations

| Task | Command |
|------|---------|
| Tail the run log | `tail -f run.log` |
| Manually trigger a run | `./venv/bin/python src/main.py` |
| List alerts sent | `psql "$DATABASE_URL" -c "SELECT * FROM alerts_sent ORDER BY sent_at DESC LIMIT 20;"` |
| Show recent fares for a route | `psql "$DATABASE_URL" -c "SELECT departure_date, price, price_level FROM fares WHERE origin='RDU' AND destination='SFO' ORDER BY fetched_at DESC LIMIT 20;"` |
| List active cron jobs | `crontab -l` |

---

## How the deal detection works

Two-layer approach, whichever has data wins:

1. **SerpApi price insights** (preferred) — SerpApi returns a `typical_price_range` for the route/date. If the current price is below 70% of the low end of that range, it's a deal.
2. **Our own 30-day median** (fallback) — if SerpApi doesn't return insights, compute a median from our own `fares` history (requires ≥7 days of data for the route+date).

Alerts are deduped for 24h per route + departure_date via the `alerts_sent` table.

---

## Developer setup

Install [pre-commit](https://pre-commit.com/) once per clone so lint, format, and secret scanning run before every commit (the same checks run in CI):

```bash
pipx install pre-commit        # or: brew install pre-commit
pre-commit install             # from repo root
pre-commit run --all-files     # one-time sweep
```

The hooks cover:
- `ruff` — lint + format (Python syntax, imports, style)
- `bandit` — Python security scan
- `gitleaks` — secret scanning (API keys, tokens)
- `detect-private-key`, `check-ast`, `check-yaml`, trailing whitespace, etc.

## Files

```
flight-alerts/
├── src/
│   ├── main.py              # orchestrator
│   ├── config.py            # routes + thresholds
│   ├── serpapi_client.py    # SerpApi calls
│   ├── db.py                # Neon reads/writes
│   ├── analyzer.py          # two-layer deal detection
│   └── notifier.py          # Telegram formatting + send
├── schema.sql               # fares + alerts_sent
├── .env.example             # template
├── requirements.txt
├── setup.sh                 # one-shot local setup
└── README.md
```
