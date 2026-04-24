import logging
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values

from config import ALERT_DEDUPE_HOURS, DATABASE_URL, MEDIAN_WINDOW_DAYS

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


def insert_fares(fares: list[dict]) -> int:
    if not fares:
        return 0
    rows = [
        (
            f["origin"],
            f["destination"],
            f["departure_date"],
            f["price"],
            f["stops"],
            f["duration_min"],
            f["airline"],
        )
        for f in fares
    ]
    with connect() as conn, conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO fares
                (origin, destination, departure_date, price, stops, duration_min, airline)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            rows,
        )
        return cur.rowcount


def get_median_price(origin: str, destination: str, days: int = MEDIAN_WINDOW_DAYS) -> tuple[float | None, int]:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median,
                COUNT(DISTINCT fetched_at::date) AS day_count
            FROM fares
            WHERE origin = %s
              AND destination = %s
              AND fetched_at >= NOW() - (%s || ' days')::interval
            """,
            (origin, destination, days),
        )
        row = cur.fetchone()
        if not row or row[0] is None:
            return None, 0
        return float(row[0]), int(row[1])


def was_recently_alerted(origin: str, destination: str, departure_date, hours: int = ALERT_DEDUPE_HOURS) -> bool:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM alerts
            WHERE origin = %s
              AND destination = %s
              AND departure_date = %s
              AND alerted_at >= NOW() - (%s || ' hours')::interval
            LIMIT 1
            """,
            (origin, destination, departure_date, hours),
        )
        return cur.fetchone() is not None


def record_alert(origin: str, destination: str, departure_date, price: float, median_price: float, pct_off: float) -> None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO alerts (origin, destination, departure_date, price, median_price, pct_off)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (origin, destination, departure_date, price, median_price, pct_off),
        )
