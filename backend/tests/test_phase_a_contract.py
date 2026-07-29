from pathlib import Path

from backend.app.data.mock_asset_products import load_mock_asset_products
from backend.app.models import AllocationRuleType, AssetClass, RightsStatus, ValueProvenance


def test_mock_products_have_required_governance_fields() -> None:
    products = load_mock_asset_products(Path("backend/app/data"))

    assert products
    assert all(product.source_reference for product in products)
    assert all(product.data_timestamp for product in products)
    assert all(product.rights_status == RightsStatus.APPROVED for product in products)
    assert all(product.value_provenance in {ValueProvenance.MANUAL_VERIFIED, ValueProvenance.DERIVED} for product in products)


def test_amount_dependent_products_expose_segments() -> None:
    products = load_mock_asset_products(Path("backend/app/data"))
    amount_dependent = {
        AllocationRuleType.WHOLE_BALANCE_TIER,
        AllocationRuleType.MARGINAL_BAND,
        AllocationRuleType.PIECEWISE_COST,
    }

    assert all(
        product.allocation_segments
        for product in products
        if product.allocation_rule_type in amount_dependent
    )


def test_vn30_equities_are_loaded_from_snapshot_file() -> None:
    products = load_mock_asset_products(Path("backend/app/data"))
    vn30_equities = [product for product in products if product.asset_class == AssetClass.EQUITY]

    assert vn30_equities
    assert all(product.source_registry_id == "MOCK_VN30_SNAPSHOT_2026Q3" for product in vn30_equities)
