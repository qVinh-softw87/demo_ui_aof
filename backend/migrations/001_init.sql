CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY,
    display_name TEXT,
    total_assets REAL NOT NULL DEFAULT 0,
    emergency_reserve REAL NOT NULL DEFAULT 0,
    near_term_liabilities REAL NOT NULL DEFAULT 0,
    risk_capacity TEXT NOT NULL DEFAULT 'MEDIUM',
    liquidity_need_months INTEGER NOT NULL DEFAULT 6,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS portfolios (
    portfolio_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    recommendation_id TEXT NOT NULL,
    legal_operating_mode TEXT NOT NULL,
    output_release_type TEXT NOT NULL,
    data_snapshot TEXT NOT NULL,
    model_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    portfolio_id TEXT,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    human_confirmed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id TEXT PRIMARY KEY,
    user_id TEXT,
    module_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    input_json TEXT,
    output_json TEXT,
    recommendation_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS asset_products (
    product_id TEXT PRIMARY KEY,
    asset_class TEXT NOT NULL,
    provider TEXT NOT NULL,
    product_name TEXT NOT NULL,
    source_registry_id TEXT NOT NULL,
    source_reference TEXT NOT NULL,
    data_timestamp TEXT NOT NULL,
    rights_status TEXT NOT NULL,
    value_provenance TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_asset_products_asset_class ON asset_products(asset_class);
CREATE INDEX IF NOT EXISTS idx_asset_products_rights_status ON asset_products(rights_status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_recommendation_id ON audit_logs(recommendation_id);
