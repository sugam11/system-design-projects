import logging
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, execute_values

from config import ALERT_COOLDOWN_HOURS, DATABASE_URL

log = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"


@contextmanager
def connect():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema() -> None:
    sql = SCHEMA_PATH.read_text()
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql)


def save_fares(fares: list[dict]) -> int:
    if not fares:
        return 0
    rows = [
        (
            f["origin"],
            f["destination"],
            f["departure_date"],
            f["price"],
            f.get("price_level"),
            f.get("typical_low"),
            f.get("typical_high"),
            f.get("airline"),
            f.get("stops"),
            f.get("duration_min"),
        )
        for f in fares
    ]
    with connect() as conn, conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO fares
                (origin, destination, departure_date, price, price_level,
                 typical_low, typical_high, airline, stops, duration_min)
            VALUES %s
            """,
            rows,
        )
        return cur.rowcount


def get_median_price(origin: str, destination: str, departure_date) -> tuple[float | None, int]:
    """Returns (median_price, distinct_day_count) for a given route+date over last 30 days."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median,
                COUNT(DISTINCT fetched_at::date) AS day_count
            FROM fares
            WHERE origin = %s
              AND destination = %s
              AND departure_date = %s
              AND fetched_at > NOW() - INTERVAL '30 days'
            """,
            (origin, destination, departure_date),
        )
        row = cur.fetchone()
        if not row or row[0] is None:
            return None, 0
        return float(row[0]), int(row[1])


def was_recently_alerted(
    origin: str, destination: str, departure_date, hours: int = ALERT_COOLDOWN_HOURS
) -> bool:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM alerts_sent
            WHERE origin = %s
              AND destination = %s
              AND departure_date = %s
              AND sent_at > NOW() - (%s || ' hours')::interval
            LIMIT 1
            """,
            (origin, destination, departure_date, hours),
        )
        return cur.fetchone() is not None


def log_api_call(
    origin: str,
    destination: str,
    outbound_date,
    trip_type: int,
    route_label: str,
    status: str,
    response: dict | None = None,
    error_message: str | None = None,
) -> None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO serp_api_calls
                (route_label, origin, destination, outbound_date, trip_type,
                 status, error_message, response)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                route_label,
                origin,
                destination,
                outbound_date,
                trip_type,
                status,
                error_message,
                Json(response) if response is not None else None,
            ),
        )


def count_api_calls_this_month() -> int:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM serp_api_calls
            WHERE called_at >= date_trunc('month', NOW())
            """
        )
        return int(cur.fetchone()[0])


def record_alert(origin: str, destination: str, departure_date, price: float) -> None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO alerts_sent (origin, destination, departure_date, price)
            VALUES (%s, %s, %s, %s)
            """,
            (origin, destination, departure_date, price),
        )
