from __future__ import annotations

from dataclasses import dataclass

from backend.app.core.config import get_settings
from backend.app.models import ComplexityBreakdown, ProductAllocation


@dataclass(frozen=True)
class ComplexityConfig:
    version: str
    provider_weight: int
    product_weight: int
    fragment_weight: int
    maturity_weight: int
    fragment_threshold_pct: float
    normalization_raw: int
    warning_threshold: float
    small_capital_threshold: int
    small_capital_multiplier: float
    objective_scale: int
    resolve_boost: float


def get_complexity_config() -> ComplexityConfig:
    settings = get_settings()
    return ComplexityConfig(
        version=settings.complexity_config_version,
        provider_weight=settings.complexity_provider_weight,
        product_weight=settings.complexity_product_weight,
        fragment_weight=settings.complexity_fragment_weight,
        maturity_weight=settings.complexity_maturity_weight,
        fragment_threshold_pct=settings.complexity_fragment_threshold_pct,
        normalization_raw=settings.complexity_normalization_raw,
        warning_threshold=settings.complexity_warning_threshold,
        small_capital_threshold=settings.complexity_small_capital_threshold,
        small_capital_multiplier=settings.complexity_small_capital_multiplier,
        objective_scale=settings.complexity_objective_scale,
        resolve_boost=settings.complexity_resolve_boost,
    )


def raw_complexity_score(
    *,
    provider_count: int,
    product_count: int,
    fragment_count: int,
    maturity_count: int,
    config: ComplexityConfig,
) -> int:
    return (
        config.provider_weight * provider_count
        + config.product_weight * product_count
        + config.fragment_weight * fragment_count
        + config.maturity_weight * maturity_count
    )


def calculate_operational_complexity(
    allocations: list[ProductAllocation],
    investable_capital: int,
    maturity_days_by_product: dict[str, int],
    *,
    config: ComplexityConfig | None = None,
) -> tuple[float, ComplexityBreakdown, bool]:
    """Calculate the score only from optimizer output, never from LLM prose."""

    cfg = config or get_complexity_config()
    positive = [item for item in allocations if item.amount > 0]
    providers = {
        item.provider
        for item in positive
        if item.provider and item.asset_class.value != "CASH"
    }
    products = {item.product_id for item in positive}
    fragment_cutoff = investable_capital * cfg.fragment_threshold_pct
    fragments = [item for item in positive if item.amount < fragment_cutoff]
    maturities = {
        maturity_days_by_product.get(item.product_id, 0)
        for item in positive
        if maturity_days_by_product.get(item.product_id, 0) > 0
    }
    smallest = min((item.amount for item in positive), default=0)
    breakdown = ComplexityBreakdown(
        distinct_provider_count=len(providers),
        distinct_product_count=len(products),
        fragment_product_count=len(fragments),
        distinct_maturity_count=len(maturities),
        smallest_allocation_amount=smallest,
        smallest_allocation_pct=(
            round(smallest / investable_capital, 8)
            if investable_capital > 0 and smallest > 0
            else 0
        ),
    )
    raw = raw_complexity_score(
        provider_count=breakdown.distinct_provider_count,
        product_count=breakdown.distinct_product_count,
        fragment_count=breakdown.fragment_product_count,
        maturity_count=breakdown.distinct_maturity_count,
        config=cfg,
    )
    score = round(min(100.0, raw / max(1, cfg.normalization_raw) * 100), 2)
    warning = (
        investable_capital <= cfg.small_capital_threshold
        and score >= cfg.warning_threshold
    )
    return score, breakdown, warning


def explain_complexity_payload(payload: dict, legal_mode: str) -> str:
    """Deterministic guard used before any LLM explanation is attempted."""

    score = payload.get("operational_complexity_score")
    breakdown = payload.get("complexity_breakdown")
    if score is None or not isinstance(breakdown, dict):
        return (
            "Thiếu operational_complexity_score hoặc complexity_breakdown từ "
            "Master Optimizer; Explanation Agent không được tự ước lượng."
        )
    required = {
        "distinct_provider_count",
        "distinct_product_count",
        "fragment_product_count",
        "distinct_maturity_count",
    }
    if not required.issubset(breakdown):
        return (
            "Thiếu thành phần complexity_breakdown từ Master Optimizer; "
            "Explanation Agent không được tự suy diễn mức bất tiện."
        )
    comparison_prefix = (
        "Thông tin so sánh COMPARE_ONLY: "
        if legal_mode == "RESEARCH_EDUCATION"
        else "Đánh đổi vận hành: "
    )
    return (
        f"{comparison_prefix}độ phức tạp {score}/100, gồm "
        f"{breakdown['distinct_product_count']} sản phẩm tại "
        f"{breakdown['distinct_provider_count']} tổ chức, "
        f"{breakdown['fragment_product_count']} phần phân bổ vụn và "
        f"{breakdown['distinct_maturity_count']} kỳ hạn cần theo dõi."
    )