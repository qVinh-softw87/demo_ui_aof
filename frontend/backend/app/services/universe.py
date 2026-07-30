from __future__ import annotations

from collections import Counter

from backend.app.agents import AssetAgentRegistry
from backend.app.models import (
    AssetProduct,
    EligibilityDecision,
    UniverseSummary,
    UserFinancialProfile,
)
from backend.app.services.eligibility import evaluate_product_eligibility


def build_product_universe(
    products: list[AssetProduct],
    profile: UserFinancialProfile,
) -> tuple[list[AssetProduct], UniverseSummary]:
    registry = AssetAgentRegistry()
    eligible, _ = registry.run_all(products, profile)
    decisions: list[EligibilityDecision] = [
        evaluate_product_eligibility(product, profile) for product in products
    ]
    counts = Counter(str(product.asset_class) for product in eligible)
    return eligible, UniverseSummary(
        eligible_count=len(eligible),
        rejected_count=sum(not decision.eligible for decision in decisions),
        eligible_by_asset_class=dict(sorted(counts.items())),
        decisions=decisions,
    )
