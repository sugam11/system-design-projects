CREATE TABLE IF NOT EXISTS fares (
    id BIGSERIAL PRIMARY KEY,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_date DATE NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    stops INTEGER NOT NULL,
    duration_min INTEGER NOT NULL,
    airline TEXT,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (origin, destination, departure_date, price, stops, duration_min, airline)
);

CREATE INDEX IF NOT EXISTS idx_fares_route_fetched
    ON fares (origin, destination, fetched_at DESC);

CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_date DATE NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    median_price NUMERIC(10, 2) NOT NULL,
    pct_off NUMERIC(5, 2) NOT NULL,
    alerted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_route_date_alerted
    ON alerts (origin, destination, departure_date, alerted_at DESC);
