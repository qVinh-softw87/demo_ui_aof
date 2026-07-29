CREATE TABLE IF NOT EXISTS recommendation_runs (
    recommendation_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    request_json TEXT NOT NULL,
    full_output_json TEXT NOT NULL,
    released_output_json TEXT NOT NULL,
    explanation_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
);

CREATE TABLE IF NOT EXISTS chat_messages (
    message_id TEXT PRIMARY KEY,
    recommendation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (recommendation_id) REFERENCES recommendation_runs(recommendation_id)
);

CREATE TABLE IF NOT EXISTS confirmations (
    confirmation_id TEXT PRIMARY KEY,
    recommendation_id TEXT NOT NULL,
    scenario_id TEXT NOT NULL,
    confirmed INTEGER NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (recommendation_id) REFERENCES recommendation_runs(recommendation_id)
);

CREATE INDEX IF NOT EXISTS idx_recommendation_runs_user_id
    ON recommendation_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_recommendation_id
    ON chat_messages(recommendation_id);
CREATE INDEX IF NOT EXISTS idx_confirmations_recommendation_id
    ON confirmations(recommendation_id);
