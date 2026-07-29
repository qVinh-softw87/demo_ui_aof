from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from backend.app.db.sqlite import get_connection, initialize_database


def save_source_result(
    *,
    source_id: str,
    display_name: str,
    category: str,
    source_url: str,
    cadence: str,
    status: str,
    attempted_at: datetime,
    observed_at: datetime | None,
    stale_after_seconds: int,
    observations: list[dict[str, Any]],
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    initialize_database()
    attempted_iso = attempted_at.isoformat()
    observed_iso = observed_at.isoformat() if observed_at else None
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO market_data_sources (
                source_id, display_name, category, source_url, cadence, status,
                last_attempt_at, last_success_at, observed_at, stale_after_seconds,
                record_count, last_error, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                display_name=excluded.display_name,
                category=excluded.category,
                source_url=excluded.source_url,
                cadence=excluded.cadence,
                status=excluded.status,
                last_attempt_at=excluded.last_attempt_at,
                last_success_at=CASE
                    WHEN excluded.status = 'CONNECTED' THEN excluded.last_success_at
                    ELSE market_data_sources.last_success_at
                END,
                observed_at=COALESCE(excluded.observed_at, market_data_sources.observed_at),
                stale_after_seconds=excluded.stale_after_seconds,
                record_count=CASE
                    WHEN excluded.status = 'CONNECTED' THEN excluded.record_count
                    ELSE market_data_sources.record_count
                END,
                last_error=excluded.last_error,
                metadata_json=COALESCE(excluded.metadata_json, market_data_sources.metadata_json),
                updated_at=datetime('now')
            """,
            (
                source_id,
                display_name,
                category,
                source_url,
                cadence,
                status,
                attempted_iso,
                attempted_iso if status == "CONNECTED" else None,
                observed_iso,
                stale_after_seconds,
                len(observations),
                error,
                json.dumps(metadata or {}, ensure_ascii=False, default=str),
            ),
        )
        for item in observations:
            item_observed = item.get("observed_at") or observed_at or attempted_at
            conn.execute(
                """
                INSERT INTO market_observations (
                    observation_id, source_id, series_key, category, label,
                    observed_at, fetched_at, value, unit, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, series_key, observed_at) DO UPDATE SET
                    fetched_at=excluded.fetched_at,
                    value=excluded.value,
                    unit=excluded.unit,
                    payload_json=excluded.payload_json
                """,
                (
                    str(uuid4()),
                    source_id,
                    item["series_key"],
                    item.get("category", category),
                    item["label"],
                    item_observed.isoformat(),
                    attempted_iso,
                    item.get("value"),
                    item["unit"],
                    json.dumps(item, ensure_ascii=False, default=str),
                ),
            )
        conn.commit()


def list_source_status() -> list[dict[str, Any]]:
    initialize_database()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT source_id, display_name, category, source_url, cadence, status,
                   last_attempt_at, last_success_at, observed_at,
                   stale_after_seconds, record_count, last_error, metadata_json
            FROM market_data_sources
            ORDER BY category, display_name
            """
        ).fetchall()
    return [
        {
            **dict(row),
            "metadata": json.loads(row["metadata_json"] or "{}"),
        }
        for row in rows
    ]


def latest_observations() -> list[dict[str, Any]]:
    initialize_database()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT source_id, series_key, category, label, observed_at,
                   fetched_at, value, unit, payload_json
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY source_id, series_key
                           ORDER BY observed_at DESC, fetched_at DESC
                       ) AS row_number
                FROM market_observations
            )
            WHERE row_number = 1
            ORDER BY category, source_id, series_key
            """
        ).fetchall()
    return [
        {
            **dict(row),
            "payload": json.loads(row["payload_json"]),
        }
        for row in rows
    ]
