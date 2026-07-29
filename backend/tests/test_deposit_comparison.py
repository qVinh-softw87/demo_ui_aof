from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings
from backend.app.db.sqlite import initialize_database, upsert_asset_products
from backend.app.services.deposit_comparison import (
    compare_deposits,
    extract_deposit_query,
)
from backend.app.services.market_data import _bank_deposit_product


def test_deposit_comparison_enforces_amount_and_customer_segment(tmp_path) -> None:
    settings = get_settings()
    original_db_path = settings.db_path
    settings.db_path = tmp_path / "deposit-test.sqlite3"
    initialize_database()
    observed_at = datetime(2026, 7, 29, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    source_url = "https://example.test/rates"
    rates = {"MBBank": 6.3, "Techcombank": 6.9, "VPBank": 6.0}
    try:
        upsert_asset_products(
            [
                _bank_deposit_product(
                    bank=bank,
                    tenor_months=12,
                    rate=rate,
                    observed_at=observed_at,
                    source_url=source_url,
                )
                for bank, rate in rates.items()
            ]
        )

        retail = compare_deposits(
            amount=100_000_000,
            tenor_months=12,
            customer_segment="retail",
        )
        retail_rows = {row["provider"]: row for row in retail["comparisons"]}
        assert retail_rows["MBBank"]["eligible"] is True
        assert retail_rows["VPBank"]["eligible"] is True
        assert retail_rows["Techcombank"]["eligible"] is False
        assert retail_rows["MBBank"]["projected_interest"] == 6_300_000

        private = compare_deposits(
            amount=3_000_000_000,
            tenor_months=12,
            customer_segment="private",
        )
        private_rows = {row["provider"]: row for row in private["comparisons"]}
        assert private_rows["Techcombank"]["eligible"] is True
        assert private_rows["MBBank"]["eligible"] is False
        assert private_rows["VPBank"]["eligible"] is False
    finally:
        settings.db_path = original_db_path


def test_chat_query_extracts_amount_tenor_and_segment() -> None:
    assert extract_deposit_query(
        "So sánh gửi 250 triệu trong 6 tháng cho khách hàng ưu tiên",
        default_amount=100_000_000,
        default_segment="retail",
    ) == (250_000_000, 6, "priority")
