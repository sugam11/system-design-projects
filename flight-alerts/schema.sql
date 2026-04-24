CREATE TABLE IF NOT EXISTS fares (
    id              SERIAL PRIMARY KEY,
    origin          TEXT NOT NULL,
    destination     TEXT NOT NULL,
    departure_date  DATE NOT NULL,
    price           NUMERIC NOT NULL,
    price_level     TEXT,
    typical_low     NUMERIC,
    typical_high    NUMERIC,
    airline         TEXT,
    stops           INTEGER,
    duration_min    INTEGER,
    fetched_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerts_sent (
    id              SERIAL PRIMARY KEY,
    origin          TEXT NOT NULL,
    destination     TEXT NOT NULL,
    departure_date  DATE NOT NULL,
    price           NUMERIC NOT NULL,
    sent_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fares_route_date
    ON fares (origin, destination, departure_date, fetched_at);
