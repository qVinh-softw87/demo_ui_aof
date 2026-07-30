from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from backend.app.models import AssetClass, AssetProduct, UserFinancialProfile
from backend.app.services.eligibility import evaluate_product_eligibility


@dataclass(frozen=True)
class AgentResult:
    agent_name: str
    asset_class: AssetClass
    eligible_products: list[AssetProduct]
    rejected_products: list[AssetProduct]


class AssetAgent:
    """Deterministic asset module.

    Agents normalize and filter products; they never choose weights or amounts.
    """

    def __init__(self, name: str, asset_classes: set[AssetClass]) -> None:
        self.name = name
        self.asset_classes = asset_classes

    def run(
        self,
        products: list[AssetProduct],
        profile: UserFinancialProfile,
    ) -> AgentResult:
        scoped = [product for product in products if product.asset_class in self.asset_classes]
        eligible: list[AssetProduct] = []
        rejected: list[AssetProduct] = []
        for product in scoped:
            decision = evaluate_product_eligibility(product, profile)
            (eligible if decision.eligible else rejected).append(product)
        primary_class = sorted(self.asset_classes, key=str)[0]
        return AgentResult(self.name, primary_class, eligible, rejected)


class AssetAgentRegistry:
    def __init__(self) -> None:
        self.agents = [
            AssetAgent("CashAgent", {AssetClass.CASH}),
            AssetAgent("GoldAgent", {AssetClass.GOLD}),
            AssetAgent("SilverAgent", {AssetClass.SILVER}),
            AssetAgent("DepositAgent", {AssetClass.DEPOSIT}),
            AssetAgent("EquityAgent", {AssetClass.EQUITY, AssetClass.ETF}),
            AssetAgent(
                "BondAgent",
                {AssetClass.BOND_FUND, AssetClass.GOVERNMENT_BOND_REFERENCE},
            ),
        ]

    def run_all(
        self,
        products: list[AssetProduct],
        profile: UserFinancialProfile,
    ) -> tuple[list[AssetProduct], dict[str, list[AssetProduct]]]:
        eligible: dict[str, AssetProduct] = {}
        rejected_by_agent: dict[str, list[AssetProduct]] = defaultdict(list)
        for agent in self.agents:
            result = agent.run(products, profile)
            for product in result.eligible_products:
                eligible[product.product_id] = product
            rejected_by_agent[result.agent_name].extend(result.rejected_products)
        return list(eligible.values()), dict(rejected_by_agent)
