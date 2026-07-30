CREATE TABLE IF NOT EXISTS advisory_authorizations (
    user_id TEXT PRIMARY KEY,
    licensed_entity_verified INTEGER NOT NULL DEFAULT 0,
    advisory_contract_verified INTEGER NOT NULL DEFAULT 0,
    responsible_advisor_verified INTEGER NOT NULL DEFAULT 0,
    verified_by TEXT,
    verified_at TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES auth_users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_advisory_authorizations_verified_by
    ON advisory_authorizations(verified_by);
