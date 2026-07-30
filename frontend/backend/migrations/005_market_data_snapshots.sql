CREATE TABLE IF NOT EXISTS market_data_sources (
    source_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    category TEXT NOT NULL,
    source_url TEXT NOT NULL,
    cadence TEXT NOT NULL,
    status TEXT NOT NULL,
    last_attempt_at TEXT NOT NULL,
    last_success_at TEXT,
    observed_at TEXT,
    stale_after_seconds INTEGER NOT NULL,
    record_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS market_observations (
    observation_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    series_key TEXT NOT NULL,
    category TEXT NOT NULL,
    label TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    value REAL,
    unit TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source_id, series_key, observed_at),
    FOREIGN KEY (source_id) REFERENCES market_data_sources(source_id)
);

CREATE INDEX IF NOT EXISTS idx_market_sources_status
    ON market_data_sources(status);
CREATE INDEX IF NOT EXISTS idx_market_observations_series
    ON market_observations(source_id, series_key, observed_at DESC);
