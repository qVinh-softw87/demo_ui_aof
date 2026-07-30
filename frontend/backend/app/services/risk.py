from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from backend.app.models import (
    AssetClass,
    ProductAllocation,
    RiskCapacity,
    RiskMetrics,
    StressResult,
)


RISK_CEILINGS: dict[RiskCapacity, float] = {
    RiskCapacity.LOW: 0.085,
    RiskCapacity.MEDIUM: 0.145,
    RiskCapacity.HIGH: 0.220,
}


def _correlation(left: AssetClass, right: AssetClass) -> float:
    if left == right:
        return 1.0
    growth = {AssetClass.EQUITY, AssetClass.ETF}
    metals = {AssetClass.GOLD, AssetClass.SILVER}
    defensive = {AssetClass.CASH, AssetClass.DEPOSIT, AssetClass.BOND_FUND}
    if left in growth and right in growth:
        return 0.82
    if left in metals and right in metals:
        return 0.58
    if left in defensive and right in defensive:
        return 0.24
    if (left in growth and right in metals) or (right in growth and left in metals):
        return 0.08
    if (left in growth and right in defensive) or (right in growth and left in defensive):
        return 0.12
    return 0.15


def calculate_risk_metrics(
    allocations: list[ProductAllocation],
    capital: int,
    risk_capacity: RiskCapacity,
) -> RiskMetrics:
    if not allocations or capital <= 0:
        ceiling = RISK_CEILINGS[risk_capacity]
        return RiskMetrics(
            annualized_volatility=0,
            var_95_amount=0,
            cvar_95_amount=0,
            sharpe_ratio=None,
            concentration_hhi=0,
            largest_asset_class_weight=0,
            liquidity_score=100,
            risk_ceiling=ceiling,
            within_risk_ceiling=True,
            stress_tests=[],
        )

    weights = np.array([item.amount / capital for item in allocations], dtype=float)
    vols = np.array(
        [
            {
                AssetClass.CASH: 0.0,
                AssetClass.DEPOSIT: 0.005,
                AssetClass.BOND_FUND: 0.045,
                AssetClass.GOLD: 0.18,
                AssetClass.SILVER: 0.28,
                AssetClass.EQUITY: 0.32,
                AssetClass.ETF: 0.22,
            }.get(item.asset_class, 0.10)
            for item in allocations
        ],
        dtype=float,
    )
    covariance = np.zeros((len(allocations), len(allocations)), dtype=float)
    for i, left in enumerate(allocations):
        for j, right in enumerate(allocations):
            covariance[i, j] = (
                vols[i] * vols[j] * _correlation(left.asset_class, right.asset_class)
            )
    volatility = float(math.sqrt(max(0.0, weights @ covariance @ weights)))
    expected_rate = sum(item.expected_return_amount for item in allocations) / capital
    sharpe = (expected_rate - 0.025) / volatility if volatility > 0 else None

    class_weights: dict[AssetClass, float] = defaultdict(float)
    for item in allocations:
        class_weights[item.asset_class] += item.amount / capital
    hhi = sum(weight * weight for weight in class_weights.values())
    largest = max(class_weights.values(), default=0)
    liquidity = sum(item.liquidity_score * item.amount for item in allocations) / capital
    var_amount = round(1.645 * volatility * capital)
    cvar_amount = round(2.063 * volatility * capital)
    ceiling = RISK_CEILINGS[risk_capacity]

    equity_weight = sum(
        weight
        for asset_class, weight in class_weights.items()
        if asset_class in {AssetClass.EQUITY, AssetClass.ETF}
    )
    metals_weight = sum(
        weight
        for asset_class, weight in class_weights.items()
        if asset_class in {AssetClass.GOLD, AssetClass.SILVER}
    )
    bond_weight = class_weights.get(AssetClass.BOND_FUND, 0)
    return RiskMetrics(
        annualized_volatility=round(volatility, 6),
        var_95_amount=var_amount,
        cvar_95_amount=cvar_amount,
        sharpe_ratio=round(sharpe, 4) if sharpe is not None else None,
        concentration_hhi=round(hhi, 6),
        largest_asset_class_weight=round(largest, 6),
        liquidity_score=round(liquidity, 2),
        risk_ceiling=ceiling,
        within_risk_ceiling=volatility <= ceiling + 1e-9,
        stress_tests=[
            StressResult(
                scenario_name="Thị trường cổ phiếu giảm mạnh",
                estimated_change_amount=round(-0.22 * equity_weight * capital),
                estimated_change_pct=round(-0.22 * equity_weight, 6),
                assumptions="Nhóm cổ phiếu/ETF giảm 22%; các nhóm khác giữ nguyên.",
            ),
            StressResult(
                scenario_name="Lãi suất tăng 2 điểm phần trăm",
                estimated_change_amount=round(-0.06 * bond_weight * capital),
                estimated_change_pct=round(-0.06 * bond_weight, 6),
                assumptions="Quỹ trái phiếu giảm 6% theo cú sốc duration đơn giản.",
            ),
            StressResult(
                scenario_name="Kim loại quý điều chỉnh",
                estimated_change_amount=round(-0.15 * metals_weight * capital),
                estimated_change_pct=round(-0.15 * metals_weight, 6),
                assumptions="Vàng/bạc giảm 15%; chưa tính thay đổi spread.",
            ),
        ],
    )
