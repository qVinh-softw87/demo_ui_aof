from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.data.mock_asset_products import load_mock_asset_products
from backend.app.db.sqlite import (
    fetch_asset_product,
    initialize_database,
    restrict_mock_products,
    upsert_asset_products,
)
from backend.app.main import app
from backend.app.services.orchestrator import synchronize_mock_product_definitions


def test_same_origin_api_health_alias() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["app_version"]
    assert payload["llm_provider"]


def test_sample_profile_can_create_a_complete_recommendation() -> None:
    with TestClient(app) as client:
        sample = client.get("/api/v1/demo/default-request")
        assert sample.status_code == 200

        response = client.post("/api/v1/recommendations", json=sample.json())

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["released_output"]["output_release_type"] != "BLOCKED"
    assert len(payload["released_output"]["scenarios"]) == 3
    assert all(
        scenario["allocations"]
        for scenario in payload["released_output"]["scenarios"]
    )


def test_mock_product_sync_repairs_stale_rows_without_reenabling_restricted_sources(
    tmp_path,
) -> None:
    settings = get_settings()
    original_db_path = settings.db_path
    settings.db_path = tmp_path / "mock-sync.sqlite3"
    initialize_database()
    try:
        canonical = {
            product.product_id: product
            for product in load_mock_asset_products(settings.data_dir)
        }
        ring = canonical["gold-ring-mock"]
        stale_ring = ring.model_copy(
            update={
                "buy_price": ring.buy_price * 10,
                "sell_price": ring.sell_price * 10,
            }
        )
        upsert_asset_products([stale_ring])

        assert synchronize_mock_product_definitions() == 1
        repaired = fetch_asset_product(ring.product_id)
        assert repaired is not None
        assert repaired["buy_price"] == ring.buy_price
        assert synchronize_mock_product_definitions() == 0

        restrict_mock_products({"GOLD"})
        assert synchronize_mock_product_definitions() == 0
        restricted = fetch_asset_product(ring.product_id)
        assert restricted is not None
        assert restricted["rights_status"] == "RESTRICTED"
    finally:
        settings.db_path = original_db_path
