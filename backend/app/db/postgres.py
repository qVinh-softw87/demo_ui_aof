from __future__ import annotations

import json
import os
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

from backend.app.core.config import get_settings
from backend.app.models import AssetProduct

class PostgresConnectionWrapper:
    def __init__(self, conn):
        self.conn = conn

    def _prepare(self, query: str) -> str:
        q = query.replace("?", "%s")
        q = q.replace("datetime('now')", "CURRENT_TIMESTAMP")
        return q

    def execute(self, query: str, params=None):
        query = self._prepare(query)
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)
        return cursor

    def executemany(self, query: str, params_list):
        query = self._prepare(query)
        cursor = self.conn.cursor()
        cursor.executemany(query, params_list)
        return cursor
        
    def executescript(self, script: str):
        script = self._prepare(script)
        cursor = self.conn.cursor()
        cursor.execute(script)
        
    def commit(self):
        self.conn.commit()
        
    def rollback(self):
        self.conn.rollback()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()

def get_connection(db_path: Path | None = None) -> PostgresConnectionWrapper:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required for PostgreSQL")
        
    database_url = database_url.strip()
    if database_url.startswith("DATABASE_URL="):
        database_url = database_url[len("DATABASE_URL="):]
    database_url = database_url.strip('"').strip("'")
    
    conn = psycopg2.connect(database_url)
    conn.autocommit = False
    return PostgresConnectionWrapper(conn)

def initialize_database(db_path: Path | None = None) -> None:
    settings = get_settings()
    migrations_dir = settings.project_root / "backend" / "migrations"
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_name TEXT PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
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
                "INSERT INTO schema_migrations (migration_name) VALUES (%s)",
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (product_id) DO UPDATE SET
                asset_class=EXCLUDED.asset_class,
                provider=EXCLUDED.provider,
                product_name=EXCLUDED.product_name,
                source_registry_id=EXCLUDED.source_registry_id,
                source_reference=EXCLUDED.source_reference,
                data_timestamp=EXCLUDED.data_timestamp,
                rights_status=EXCLUDED.rights_status,
                value_provenance=EXCLUDED.value_provenance,
                verification_status=EXCLUDED.verification_status,
                payload_json=EXCLUDED.payload_json,
                updated_at=CURRENT_TIMESTAMP
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
        filters.append("asset_class = %s")
        params.append(asset_class)
    if approved_only:
        filters.append("rights_status = 'APPROVED'")

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    query = f"SELECT payload_json FROM asset_products {where_clause} ORDER BY asset_class, provider, product_name"

    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [row["payload_json"] if isinstance(row["payload_json"], dict) else json.loads(row["payload_json"]) for row in rows]

def fetch_asset_product(product_id: str, db_path: Path | None = None) -> dict | None:
    initialize_database(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT payload_json FROM asset_products WHERE product_id = %s",
            (product_id,),
        ).fetchone()
    if not row:
        return None
    return row["payload_json"] if isinstance(row["payload_json"], dict) else json.loads(row["payload_json"])

def restrict_mock_products(
    asset_classes: set[str],
    db_path: Path | None = None,
) -> int:
    if not asset_classes:
        return 0
    initialize_database(db_path)
    placeholders = ",".join("%s" for _ in asset_classes)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT product_id, payload_json
            FROM asset_products
            WHERE source_registry_id LIKE 'MOCK%%'
              AND asset_class IN ({placeholders})
            """,
            tuple(sorted(asset_classes)),
        ).fetchall()
        for row in rows:
            payload = row["payload_json"] if isinstance(row["payload_json"], dict) else json.loads(row["payload_json"])
            payload["rights_status"] = "RESTRICTED"
            conn.execute(
                """
                UPDATE asset_products
                SET rights_status = 'RESTRICTED',
                    payload_json = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE product_id = %s
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
    if not source_registry_ids:
        return 0
    initialize_database(db_path)
    placeholders = ",".join("%s" for _ in source_registry_ids)
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
            payload = row["payload_json"] if isinstance(row["payload_json"], dict) else json.loads(row["payload_json"])
            payload["rights_status"] = "RESTRICTED"
            conn.execute(
                """
                UPDATE asset_products
                SET rights_status = 'RESTRICTED',
                    payload_json = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE product_id = %s
                """,
                (
                    json.dumps(payload, ensure_ascii=False, default=str),
                    row["product_id"],
                ),
            )
        conn.commit()
    return len(rows)
