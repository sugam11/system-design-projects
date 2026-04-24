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

Run the interactive configurator:

```bash
./venv/bin/python configure.py
```

It lets you list, add, and delete routes, and shows a budget estimate for 1x/2x/3x-per-day cron cadence against the 250-call SerpApi free tier. All routes are persisted to [`routes.json`](routes.json) — you can also edit that file by hand.

Each route:

| Field | Meaning |
|---|---|
| `origin` / `destination` | 3-letter IATA codes |
| `label` | Human-readable, used in logs and alerts |
| `trip_type` | `1` = round trip, `2` = one way |
| `days_out_start` / `days_out_end` | Search window (days from today) |
| `date_step` | Check every Nth day in that window |
| `max_stops` | `0` = nonstop only, `1`, `2`, or `null` for no limit (filters at the SerpApi layer) |

**Budget note:** 1 route × 13 dates × 3 runs/day × 30 days ≈ 1170 calls/month — well over the 250 free tier. `configure.py` warns you. Tighten the window or reduce cron cadence to fit.

---

## Operations

| Task | Command |
|------|---------|
| Tail the run log | `tail -f run.log` |
| Manually trigger a run | `./venv/bin/python src/main.py` |
| Update routes | `./venv/bin/python configure.py` |
| List alerts sent | `psql "$DATABASE_URL" -c "SELECT * FROM alerts_sent ORDER BY sent_at DESC LIMIT 20;"` |
| Show recent fares for a route | `psql "$DATABASE_URL" -c "SELECT departure_date, price, price_level FROM fares WHERE origin='RDU' AND destination='SFO' ORDER BY fetched_at DESC LIMIT 20;"` |
| SerpApi calls this month | `psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM serp_api_calls WHERE called_at >= date_trunc('month', NOW());"` |
| Mine a field from raw SerpApi responses | `psql "$DATABASE_URL" -c "SELECT response->'price_insights'->'lowest_price' FROM serp_api_calls WHERE status='ok' ORDER BY called_at DESC LIMIT 5;"` |
| List active cron jobs | `crontab -l` |

---

## Raw SerpApi archive

Every call (success, empty, or error) is logged to the `serp_api_calls` table with the full response stored as JSONB. This gives you:

- An authoritative API-call counter, independent of whether the fare parsing succeeded
- A retroactive source for any field we don't currently project into `fares` — e.g. layover airports, fare class, baggage info, carbon emissions — accessible via `response->'...'` queries
- A debugging paper trail when SerpApi returns something unexpected

Storage: responses run ~50–200 KB each. At the free tier's 250 calls/month, that's ~50 MB/month. Neon free tier is 0.5 GB, so you're good for ~10 months before you need to either upgrade or prune old rows with `DELETE FROM serp_api_calls WHERE called_at < NOW() - INTERVAL '90 days';`.

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
│   ├── config.py            # thresholds + routes.json loader
│   ├── serpapi_client.py    # SerpApi calls (logs every call)
│   ├── db.py                # Neon reads/writes
│   ├── analyzer.py          # two-layer deal detection
│   └── notifier.py          # Telegram formatting + send
├── routes.json              # active routes (edited via configure.py)
├── configure.py             # interactive route manager
├── schema.sql               # fares + alerts_sent + serp_api_calls
├── .env.example             # template
├── requirements.txt
├── setup.sh                 # one-shot local setup
└── README.md
```
