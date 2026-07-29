from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.models import AssetProduct


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    settings = get_settings()
    resolved_path = db_path or settings.db_path
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(resolved_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def initialize_database(db_path: Path | None = None) -> None:
    settings = get_settings()
    migrations_dir = settings.project_root / "backend" / "migrations"
    with get_connection(db_path) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        applied = {
            row["migration_name"]
            for row in conn.execute(
                "SELECT migration_name FROM schema_migrations"
            ).fetchall()
        }
        for migration in sorted(migrations_dir.glob("*.sql")):
            if migration.name in applied:
                continue
            conn.executescript(migration.read_text(encoding="utf-8"))
            conn.execute(
                "INSERT INTO schema_migrations (migration_name) VALUES (?)",
                (migration.name,),
            )
        conn.commit()


def upsert_asset_products(products: list[AssetProduct], db_path: Path | None = None) -> int:
    initialize_database(db_path)
    with get_connection(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO asset_products (
                product_id, asset_class, provider, product_name, source_registry_id,
                source_reference, data_timestamp, rights_status, value_provenance,
                verification_status, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(product_id) DO UPDATE SET
                asset_class=excluded.asset_class,
                provider=excluded.provider,
                product_name=excluded.product_name,
                source_registry_id=excluded.source_registry_id,
                source_reference=excluded.source_reference,
                data_timestamp=excluded.data_timestamp,
                rights_status=excluded.rights_status,
                value_provenance=excluded.value_provenance,
                verification_status=excluded.verification_status,
                payload_json=excluded.payload_json,
                updated_at=datetime('now')
            """,
            [
                (
                    product.product_id,
                    product.asset_class,
                    product.provider,
                    product.product_name,
                    product.source_registry_id,
                    product.source_reference,
                    product.data_timestamp.isoformat(),
                    product.rights_status,
                    product.value_provenance,
                    product.verification_status,
                    product.model_dump_json(),
                )
                for product in products
            ],
        )
        conn.commit()
    return len(products)


def fetch_asset_products(
    *,
    asset_class: str | None = None,
    approved_only: bool = True,
    db_path: Path | None = None,
) -> list[dict]:
    initialize_database(db_path)
    filters: list[str] = []
    params: list[str] = []
    if asset_class:
        filters.append("asset_class = ?")
        params.append(asset_class)
    if approved_only:
        filters.append("rights_status = 'APPROVED'")

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    query = f"SELECT payload_json FROM asset_products {where_clause} ORDER BY asset_class, provider, product_name"

    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [json.loads(row["payload_json"]) for row in rows]


def fetch_asset_product(product_id: str, db_path: Path | None = None) -> dict | None:
    initialize_database(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT payload_json FROM asset_products WHERE product_id = ?",
            (product_id,),
        ).fetchone()
    return json.loads(row["payload_json"]) if row else None


def restrict_mock_products(
    asset_classes: set[str],
    db_path: Path | None = None,
) -> int:
    """Keep mock rows for audit while excluding replaced classes from optimization."""

    if not asset_classes:
        return 0
    initialize_database(db_path)
    placeholders = ",".join("?" for _ in asset_classes)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT product_id, payload_json
            FROM asset_products
            WHERE source_registry_id LIKE 'MOCK%'
              AND asset_class IN ({placeholders})
            """,
            tuple(sorted(asset_classes)),
        ).fetchall()
        for row in rows:
            payload = json.loads(row["payload_json"])
            payload["rights_status"] = "RESTRICTED"
            conn.execute(
                """
                UPDATE asset_products
                SET rights_status = 'RESTRICTED',
                    payload_json = ?,
                    updated_at = datetime('now')
                WHERE product_id = ?
                """,
                (
                    json.dumps(payload, ensure_ascii=False, default=str),
                    row["product_id"],
                ),
            )
        conn.commit()
    return len(rows)


def restrict_products_by_source(
    source_registry_ids: set[str],
    db_path: Path | None = None,
) -> int:
    """Retain superseded products for audit while removing them from optimization."""

    if not source_registry_ids:
        return 0
    initialize_database(db_path)
    placeholders = ",".join("?" for _ in source_registry_ids)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT product_id, payload_json
            FROM asset_products
            WHERE source_registry_id IN ({placeholders})
            """,
            tuple(sorted(source_registry_ids)),
        ).fetchall()
        for row in rows:
            payload = json.loads(row["payload_json"])
            payload["rights_status"] = "RESTRICTED"
            conn.execute(
                """
                UPDATE asset_products
                SET rights_status = 'RESTRICTED',
                    payload_json = ?,
                    updated_at = datetime('now')
                WHERE product_id = ?
                """,
                (
                    json.dumps(payload, ensure_ascii=False, default=str),
                    row["product_id"],
                ),
            )
        conn.commit()
    return len(rows)
