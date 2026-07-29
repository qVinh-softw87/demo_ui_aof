from __future__ import annotations

from pathlib import Path

from backend.app.data.mock_asset_products import load_mock_asset_products
from backend.app.main import default_planning_request
from backend.app.models import AssetClass
from backend.app.services.eligibility import evaluate_product_eligibility
from backend.app.services.universe import build_product_universe


def test_reference_curve_is_excluded_with_reason_code() -> None:
    products = load_mock_asset_products(Path("backend/app/data"))
    profile = default_planning_request().profile
    reference = next(
        product
        for product in products
        if product.asset_class == AssetClass.GOVERNMENT_BOND_REFERENCE
    )
    decision = evaluate_product_eligibility(reference, profile)
    assert not decision.eligible
    assert "REFERENCE_DATA_NOT_INVESTIBLE" in decision.reason_codes


def test_asset_agents_preserve_amount_dependent_segments() -> None:
    products = load_mock_asset_products(Path("backend/app/data"))
    eligible, summary = build_product_universe(
        products,
        default_planning_request().profile,
    )
    deposits = [item for item in eligible if item.asset_class == AssetClass.DEPOSIT]
    assert deposits
    assert all(item.allocation_segments for item in deposits)
    assert summary.eligible_by_asset_class["DEPOSIT"] == len(deposits)
