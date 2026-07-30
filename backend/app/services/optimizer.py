from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
from math import ceil

from ortools.sat.python import cp_model

from backend.app.models import (
    AllocationRuleType,
    AssetClass,
    AssetClassAllocation,
    AssetProduct,
    BoundedResolveTrace,
    FinancialPlan,
    InfeasibilityReport,
    PortfolioScenario,
    ProductAllocation,
    ResolveIteration,
    RiskCapacity,
    RoundingRule,
    ScenarioStyle,
    UserFinancialProfile,
)
from backend.app.services.complexity import (
    calculate_operational_complexity,
    get_complexity_config,
)
from backend.app.services.risk import RISK_CEILINGS, calculate_risk_metrics


MONEY_UNIT = 1_000
REFERENCE_ONLY_CLASSES = {AssetClass.GOVERNMENT_BOND_REFERENCE}
GROWTH_CLASSES = {AssetClass.EQUITY, AssetClass.ETF}


@dataclass(frozen=True)
class ScenarioConfig:
    style: ScenarioStyle
    name: str
    objective_description: str
    return_weight: int
    liquidity_weight: int
    risk_penalty_weight: int
    cost_penalty_weight: int
    risk_budget_fraction: float
    min_liquidity_score: int
    min_growth_weight: dict[RiskCapacity, float]
    max_growth_weight: dict[RiskCapacity, float]
    min_gold_weight: dict[RiskCapacity, float]
    min_bond_fund_weight: dict[RiskCapacity, float]


SCENARIO_CONFIGS = [
    ScenarioConfig(
        style=ScenarioStyle.CAPITAL_PRESERVATION,
        name="Đệm an toàn",
        objective_description="Ưu tiên thanh khoản và ổn định vốn trong risk ceiling.",
        return_weight=5,
        liquidity_weight=7,
        risk_penalty_weight=3,
        cost_penalty_weight=7,
        risk_budget_fraction=0.68,
        min_liquidity_score=82,
        min_growth_weight={
            RiskCapacity.LOW: 0.00,
            RiskCapacity.MEDIUM: 0.00,
            RiskCapacity.HIGH: 0.03,
        },
        max_growth_weight={
            RiskCapacity.LOW: 0.05,
            RiskCapacity.MEDIUM: 0.10,
            RiskCapacity.HIGH: 0.18,
        },
        min_gold_weight={
            RiskCapacity.LOW: 0.00,
            RiskCapacity.MEDIUM: 0.02,
            RiskCapacity.HIGH: 0.02,
        },
        min_bond_fund_weight={
            RiskCapacity.LOW: 0.03,
            RiskCapacity.MEDIUM: 0.03,
            RiskCapacity.HIGH: 0.03,
        },
    ),
    ScenarioConfig(
        style=ScenarioStyle.BALANCED,
        name="Cân bằng",
        objective_description="Cân bằng lợi nhuận kỳ vọng, thanh khoản và biến động.",
        return_weight=8,
        liquidity_weight=3,
        risk_penalty_weight=1,
        cost_penalty_weight=7,
        risk_budget_fraction=0.86,
        min_liquidity_score=70,
        min_growth_weight={
            RiskCapacity.LOW: 0.02,
            RiskCapacity.MEDIUM: 0.10,
            RiskCapacity.HIGH: 0.20,
        },
        max_growth_weight={
            RiskCapacity.LOW: 0.10,
            RiskCapacity.MEDIUM: 0.28,
            RiskCapacity.HIGH: 0.40,
        },
        min_gold_weight={
            RiskCapacity.LOW: 0.02,
            RiskCapacity.MEDIUM: 0.04,
            RiskCapacity.HIGH: 0.05,
        },
        min_bond_fund_weight={
            RiskCapacity.LOW: 0.04,
            RiskCapacity.MEDIUM: 0.04,
            RiskCapacity.HIGH: 0.04,
        },
    ),
    ScenarioConfig(
        style=ScenarioStyle.GROWTH,
        name="Tăng trưởng có kiểm soát",
        objective_description="Tìm kiếm tăng trưởng cao hơn nhưng không vượt risk ceiling.",
        return_weight=10,
        liquidity_weight=1,
        risk_penalty_weight=1,
        cost_penalty_weight=6,
        risk_budget_fraction=1.00,
        min_liquidity_score=58,
        min_growth_weight={
            RiskCapacity.LOW: 0.04,
            RiskCapacity.MEDIUM: 0.32,
            RiskCapacity.HIGH: 0.35,
        },
        max_growth_weight={
            RiskCapacity.LOW: 0.12,
            RiskCapacity.MEDIUM: 0.52,
            RiskCapacity.HIGH: 0.72,
        },
        min_gold_weight={
            RiskCapacity.LOW: 0.02,
            RiskCapacity.MEDIUM: 0.04,
            RiskCapacity.HIGH: 0.05,
        },
        min_bond_fund_weight={
            RiskCapacity.LOW: 0.00,
            RiskCapacity.MEDIUM: 0.00,
            RiskCapacity.HIGH: 0.00,
        },
    ),
]


def _rounding_step(product: AssetProduct) -> int:
    if product.allocation_rule_type == AllocationRuleType.DISCRETE_UNIT:
        lot_size = 100 if product.rounding_rule == RoundingRule.BOARD_LOT_100 else 1
        unit_value = (
            product.buy_price * lot_size
            if product.buy_price and product.buy_price > 0
            else product.minimum_investment
        )
        return max(MONEY_UNIT, round(unit_value / MONEY_UNIT) * MONEY_UNIT)
    return {
        RoundingRule.NONE: MONEY_UNIT,
        RoundingRule.VND_1K: 1_000,
        RoundingRule.VND_10K: 10_000,
        RoundingRule.VND_100K: 100_000,
        RoundingRule.VND_1M: 1_000_000,
        RoundingRule.WHOLE_UNIT: max(MONEY_UNIT, round(product.minimum_investment)),
        RoundingRule.BOARD_LOT_100: max(MONEY_UNIT, round(product.minimum_investment)),
    }[product.rounding_rule]


def _class_max_weight(
    asset_class: AssetClass,
    profile: UserFinancialProfile,
) -> float:
    equity_cap = {
        RiskCapacity.LOW: 0.12,
        RiskCapacity.MEDIUM: 0.38,
        RiskCapacity.HIGH: 0.58,
    }[profile.risk_capacity]
    if profile.horizon_months < 24:
        equity_cap *= 0.55
    elif profile.horizon_months < 60:
        equity_cap *= 0.82
    return {
        AssetClass.CASH: 1.00,
        AssetClass.DEPOSIT: 0.85,
        AssetClass.BOND_FUND: 0.55,
        AssetClass.GOLD: 0.25,
        AssetClass.SILVER: 0.08,
        AssetClass.EQUITY: equity_cap,
        AssetClass.ETF: equity_cap,
    }.get(asset_class, 0.0)


def _rate_and_segment(product: AssetProduct, amount: int) -> tuple[float, float, str | None]:
    if product.allocation_segments:
        for segment in product.allocation_segments:
            if amount < segment.lower_bound:
                continue
            if segment.upper_bound is not None and amount >= segment.upper_bound:
                continue
            return (
                segment.return_rate if segment.return_rate is not None else product.expected_return,
                segment.cost,
                segment.condition,
            )
    return product.expected_return, product.transaction_cost, None


def _add_product_variables(
    model: cp_model.CpModel,
    product: AssetProduct,
    capital_units: int,
    profile: UserFinancialProfile,
) -> tuple[cp_model.IntVar, cp_model.IntVar]:
    active = model.new_bool_var(f"active__{product.product_id}")
    amount = model.new_int_var(0, capital_units, f"amount__{product.product_id}")

    step_units = max(1, round(_rounding_step(product) / MONEY_UNIT))
    quantity = model.new_int_var(0, capital_units // step_units, f"qty__{product.product_id}")
    model.add(amount == quantity * step_units)

    minimum_units = max(1, ceil(product.minimum_investment / MONEY_UNIT))
    hinted_cap = capital_units
    if product.max_weight_hint is not None:
        hinted_cap = max(0, int(capital_units * product.max_weight_hint))
    if product.asset_class == AssetClass.CASH:
        hinted_cap = max(hinted_cap, round(profile.liquidity_need / MONEY_UNIT))
    if product.maximum_investment is not None:
        hinted_cap = min(hinted_cap, int(product.maximum_investment / MONEY_UNIT))
    maximum_units = min(capital_units, hinted_cap)

    model.add(amount >= minimum_units * active)
    model.add(amount <= maximum_units * active)
    return amount, active


def _solve_one(
    products: list[AssetProduct],
    profile: UserFinancialProfile,
    financial_plan: FinancialPlan,
    config: ScenarioConfig,
    recommendation_id: str,
    *,
    complexity_multiplier: float = 1.0,
    complexity_resolve_count: int = 0,
) -> PortfolioScenario | None:
    started = time.perf_counter()
    capital = financial_plan.investable_capital
    capital_units = capital // MONEY_UNIT
    if capital_units <= 0:
        return None

    model = cp_model.CpModel()
    complexity_config = get_complexity_config()
    amounts: dict[str, cp_model.IntVar] = {}
    actives: dict[str, cp_model.IntVar] = {}
    fragments: dict[str, cp_model.IntVar] = {}
    objective_terms: list[cp_model.LinearExpr] = []

    for product in products:
        if product.asset_class in REFERENCE_ONLY_CLASSES:
            continue
        amount, active = _add_product_variables(
            model,
            product,
            capital_units,
            profile,
        )
        amounts[product.product_id] = amount
        actives[product.product_id] = active
        fragment = model.new_bool_var(f"fragment__{product.product_id}")
        fragments[product.product_id] = fragment
        fragment_cutoff_units = max(
            1, int(capital_units * complexity_config.fragment_threshold_pct)
        )
        model.add(fragment <= active)
        model.add(amount >= fragment_cutoff_units * (active - fragment))
        model.add(
            amount
            <= (fragment_cutoff_units - 1)
            + capital_units * (1 - fragment)
        )

        return_bps = round(product.expected_return * 10_000)
        volatility_bps = round(product.volatility * 10_000)
        cost_bps = round(product.transaction_cost * 10_000)
        score = (
            return_bps * config.return_weight
            + product.liquidity_score * config.liquidity_weight
            - volatility_bps * config.risk_penalty_weight
            - cost_bps * config.cost_penalty_weight
        )

        if product.allocation_segments:
            segment_amounts: list[cp_model.IntVar] = []
            segment_actives: list[cp_model.IntVar] = []
            for index, segment in enumerate(product.allocation_segments):
                seg_active = model.new_bool_var(f"segment_active__{product.product_id}__{index}")
                seg_amount = model.new_int_var(
                    0,
                    capital_units,
                    f"segment_amount__{product.product_id}__{index}",
                )
                lower = max(
                    round(product.minimum_investment / MONEY_UNIT),
                    round(segment.lower_bound / MONEY_UNIT),
                )
                upper = capital_units
                if segment.upper_bound is not None:
                    upper = min(upper, max(0, int(segment.upper_bound / MONEY_UNIT) - 1))
                if lower > upper:
                    model.add(seg_active == 0)
                    model.add(seg_amount == 0)
                else:
                    model.add(seg_amount >= lower * seg_active)
                    model.add(seg_amount <= upper * seg_active)
                segment_amounts.append(seg_amount)
                segment_actives.append(seg_active)
                segment_return_bps = round(
                    (segment.return_rate or product.expected_return) * 10_000
                )
                segment_cost_bps = round(segment.cost * 10_000)
                segment_score = (
                    segment_return_bps * config.return_weight
                    + product.liquidity_score * config.liquidity_weight
                    - volatility_bps * config.risk_penalty_weight
                    - segment_cost_bps * config.cost_penalty_weight
                )
                objective_terms.append(seg_amount * segment_score)
            model.add(amount == sum(segment_amounts))
            model.add(sum(segment_actives) == active)
        else:
            objective_terms.append(amount * score)

    if not amounts:
        return None

    model.add(sum(amounts.values()) == capital_units)

    by_class: dict[AssetClass, list[cp_model.IntVar]] = defaultdict(list)
    for product in products:
        if product.product_id in amounts:
            by_class[product.asset_class].append(amounts[product.product_id])

    for asset_class, class_amounts in by_class.items():
        max_weight = _class_max_weight(asset_class, profile)
        model.add(sum(class_amounts) <= int(capital_units * max_weight))

    # A linear return-minus-risk score does not capture gold's diversification role.
    # Apply a small strategic floor only when a whole physical unit fits the caps.
    gold_floor_applied = False
    requested_gold_floor = config.min_gold_weight[profile.risk_capacity]
    if profile.horizon_months >= 12 and requested_gold_floor > 0:
        feasible_gold_amounts: list[cp_model.IntVar] = []
        class_cap_units = int(
            capital_units * _class_max_weight(AssetClass.GOLD, profile)
        )
        for product in products:
            if product.asset_class != AssetClass.GOLD or product.product_id not in amounts:
                continue
            product_cap_units = class_cap_units
            if product.max_weight_hint is not None:
                product_cap_units = min(
                    product_cap_units,
                    int(capital_units * product.max_weight_hint),
                )
            minimum_units = max(1, ceil(product.minimum_investment / MONEY_UNIT))
            if minimum_units <= product_cap_units:
                feasible_gold_amounts.append(amounts[product.product_id])
        if feasible_gold_amounts:
            model.add(sum(feasible_gold_amounts) >= int(capital_units * requested_gold_floor))
            gold_floor_applied = True

    # A modest fixed-income floor keeps at least one long-horizon scenario from
    # collapsing into deposits only. It is enabled only when the user's stated
    # convenience limits can support a genuinely diversified implementation.
    bond_floor_applied = False
    requested_bond_floor = config.min_bond_fund_weight[profile.risk_capacity]
    if (
        profile.horizon_months >= 12
        and profile.max_financial_apps >= 3
        and profile.max_product_count >= 4
        and requested_bond_floor > 0
    ):
        feasible_bond_amounts: list[cp_model.IntVar] = []
        class_cap_units = int(
            capital_units * _class_max_weight(AssetClass.BOND_FUND, profile)
        )
        for product in products:
            if (
                product.asset_class != AssetClass.BOND_FUND
                or product.product_id not in amounts
            ):
                continue
            product_cap_units = class_cap_units
            if product.max_weight_hint is not None:
                product_cap_units = min(
                    product_cap_units,
                    int(capital_units * product.max_weight_hint),
                )
            minimum_units = max(1, ceil(product.minimum_investment / MONEY_UNIT))
            if minimum_units <= product_cap_units:
                feasible_bond_amounts.append(amounts[product.product_id])
        if feasible_bond_amounts:
            model.add(
                sum(feasible_bond_amounts)
                >= int(capital_units * requested_bond_floor)
            )
            bond_floor_applied = True

    cash_amounts = by_class.get(AssetClass.CASH, [])
    if cash_amounts and financial_plan.immediate_liquidity_bucket > 0:
        model.add(
            sum(cash_amounts)
            >= round(financial_plan.immediate_liquidity_bucket / MONEY_UNIT)
        )

    growth_amounts = [
        amount
        for asset_class in GROWTH_CLASSES
        for amount in by_class.get(asset_class, [])
    ]
    min_growth = config.min_growth_weight[profile.risk_capacity]
    if profile.horizon_months < 12:
        min_growth = 0
    if growth_amounts and min_growth > 0:
        model.add(sum(growth_amounts) >= int(capital_units * min_growth))
    if growth_amounts:
        max_growth = config.max_growth_weight[profile.risk_capacity]
        model.add(sum(growth_amounts) <= int(capital_units * max_growth))
    equity_amounts = by_class.get(AssetClass.EQUITY, [])
    if config.style == ScenarioStyle.GROWTH and equity_amounts:
        model.add(sum(equity_amounts) >= int(capital_units * 0.04))

    risk_budget_bps = round(
        RISK_CEILINGS[profile.risk_capacity]
        * config.risk_budget_fraction
        * 10_000
    )
    model.add(
        sum(
            amounts[product.product_id] * round(product.volatility * 10_000)
            for product in products
            if product.product_id in amounts
        )
        <= risk_budget_bps * capital_units
    )
    model.add(
        sum(
            amounts[product.product_id] * product.liquidity_score
            for product in products
            if product.product_id in amounts
        )
        >= config.min_liquidity_score * capital_units
    )

    # Hard complexity budgets remain gates; the weighted terms below add the
    # continuous fourth objective required by Appendix D.
    model.add(sum(actives.values()) <= profile.max_product_count)

    provider_actives: dict[str, cp_model.IntVar] = {}
    products_by_provider: dict[str, list[cp_model.IntVar]] = defaultdict(list)
    for product in products:
        if (
            product.product_id in actives
            and product.asset_class != AssetClass.CASH
        ):
            products_by_provider[product.provider].append(actives[product.product_id])
    for provider, provider_products in products_by_provider.items():
        provider_active = model.new_bool_var(f"provider__{provider}")
        provider_actives[provider] = provider_active
        for product_active in provider_products:
            model.add(product_active <= provider_active)
        model.add(provider_active <= sum(provider_products))
    if provider_actives:
        model.add(sum(provider_actives.values()) <= profile.max_financial_apps)

    maturity_actives: dict[int, cp_model.IntVar] = {}
    products_by_maturity: dict[int, list[cp_model.IntVar]] = defaultdict(list)
    for product in products:
        if product.product_id in actives and product.lockup_period > 0:
            products_by_maturity[product.lockup_period].append(actives[product.product_id])
    for maturity_days, maturity_products in products_by_maturity.items():
        maturity_active = model.new_bool_var(f"maturity__{maturity_days}")
        maturity_actives[maturity_days] = maturity_active
        for product_active in maturity_products:
            model.add(product_active <= maturity_active)
        model.add(maturity_active <= sum(maturity_products))

    effective_complexity_multiplier = max(0.0, complexity_multiplier)
    if capital <= complexity_config.small_capital_threshold:
        effective_complexity_multiplier *= complexity_config.small_capital_multiplier
    complexity_scale = round(
        capital_units
        * complexity_config.objective_scale
        * effective_complexity_multiplier
    )
    if complexity_scale > 0:
        objective_terms.extend(
            -provider_active * complexity_scale * complexity_config.provider_weight
            for provider_active in provider_actives.values()
        )
        objective_terms.extend(
            -product_active * complexity_scale * complexity_config.product_weight
            for product_active in actives.values()
        )
        objective_terms.extend(
            -fragment * complexity_scale * complexity_config.fragment_weight
            for fragment in fragments.values()
        )
        objective_terms.extend(
            -maturity_active * complexity_scale * complexity_config.maturity_weight
            for maturity_active in maturity_actives.values()
        )

    model.maximize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 8.0
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = 2026
    status = solver.solve(model)
    if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        return None

    allocations: list[ProductAllocation] = []
    for product in products:
        variable = amounts.get(product.product_id)
        if variable is None:
            continue
        amount_value = solver.value(variable) * MONEY_UNIT
        if amount_value <= 0:
            continue
        rate, segment_cost, segment_label = _rate_and_segment(product, amount_value)
        cost_rate = segment_cost if product.allocation_segments else product.transaction_cost
        lot_size = 100 if product.rounding_rule == RoundingRule.BOARD_LOT_100 else 1
        estimated_units = (
            int(amount_value // (product.buy_price * lot_size)) * lot_size
            if product.buy_price and product.buy_price > 0
            else None
        )
        allocations.append(
            ProductAllocation(
                product_id=product.product_id,
                product_name=product.product_name,
                provider=product.provider,
                asset_class=product.asset_class,
                amount=amount_value,
                weight=round(amount_value / capital, 8),
                expected_return_rate=rate,
                expected_return_amount=round(amount_value * rate),
                transaction_cost_amount=round(amount_value * cost_rate),
                liquidity_score=product.liquidity_score,
                reference_price=product.buy_price,
                estimated_units=estimated_units,
                lot_size=lot_size if product.buy_price else None,
                selected_segment=segment_label,
                execution_instruction=product.execution_instruction,
                source_reference=product.source_reference,
                data_timestamp=product.data_timestamp,
                reason_codes=(
                    [
                        "SELECTED_BY_COUPLED_OPTIMIZER",
                        "WITHIN_PRODUCT_AND_PORTFOLIO_CONSTRAINTS",
                    ]
                    + (
                        ["STRATEGIC_GOLD_DIVERSIFIER_FLOOR"]
                        if product.asset_class == AssetClass.GOLD and gold_floor_applied
                        else []
                    )
                    + (
                        ["STRATEGIC_FIXED_INCOME_DIVERSIFIER_FLOOR"]
                        if (
                            product.asset_class == AssetClass.BOND_FUND
                            and bond_floor_applied
                        )
                        else []
                    )
                ),
            )
        )

    class_totals: dict[AssetClass, dict[str, int]] = defaultdict(
        lambda: {"amount": 0, "return": 0, "cost": 0}
    )
    for allocation in allocations:
        totals = class_totals[allocation.asset_class]
        totals["amount"] += allocation.amount
        totals["return"] += allocation.expected_return_amount
        totals["cost"] += allocation.transaction_cost_amount
    class_allocations = [
        AssetClassAllocation(
            asset_class=asset_class,
            amount=totals["amount"],
            weight=round(totals["amount"] / capital, 8),
            expected_return_amount=totals["return"],
            transaction_cost_amount=totals["cost"],
        )
        for asset_class, totals in sorted(class_totals.items(), key=lambda item: str(item[0]))
    ]

    risk_metrics = calculate_risk_metrics(allocations, capital, profile.risk_capacity)
    maturity_days_by_product = {
        product.product_id: product.lockup_period for product in products
    }
    complexity_score, complexity_breakdown, fragmentation_warning = (
        calculate_operational_complexity(
            allocations,
            capital,
            maturity_days_by_product,
            config=complexity_config,
        )
    )
    expected_amount = sum(item.expected_return_amount for item in allocations)
    cost_amount = sum(item.transaction_cost_amount for item in allocations)
    solve_ms = round((time.perf_counter() - started) * 1000)
    signature = sha256(
        "|".join(
            f"{item.product_id}:{item.amount}" for item in sorted(allocations, key=lambda x: x.product_id)
        ).encode("utf-8")
    ).hexdigest()[:10]
    return PortfolioScenario(
        scenario_id=f"{recommendation_id}-{config.style.value.lower()}-{signature}",
        name=config.name,
        style=config.style,
        objective_description=config.objective_description,
        investable_capital=capital,
        allocated_amount=sum(item.amount for item in allocations),
        residual_cash=capital - sum(item.amount for item in allocations),
        expected_return_amount=expected_amount,
        expected_return_rate=round(expected_amount / capital, 8),
        total_cost_amount=cost_amount,
        product_allocations=allocations,
        asset_class_allocations=class_allocations,
        risk_metrics=risk_metrics,
        operational_complexity_score=complexity_score,
        complexity_breakdown=complexity_breakdown,
        complexity_config_version=complexity_config.version,
        fragmentation_warning=fragmentation_warning,
        complexity_resolve_count=complexity_resolve_count,
        trade_offs=[
            f"Ngân sách rủi ro tuyến tính: {config.risk_budget_fraction:.0%} trần hồ sơ.",
            f"Điểm thanh khoản bình quân tối thiểu trong mô hình: {config.min_liquidity_score}/100.",
            (
                f"Độ phức tạp vận hành {complexity_score:.2f}/100: "
                f"{complexity_breakdown.distinct_product_count} sản phẩm tại "
                f"{complexity_breakdown.distinct_provider_count} tổ chức, "
                f"{complexity_breakdown.fragment_product_count} phần phân bổ vụn và "
                f"{complexity_breakdown.distinct_maturity_count} kỳ hạn."
            ),
            "Lợi nhuận kỳ vọng và stress test là giả định mô hình, không phải cam kết.",
            *(
                [f"Vàng vật chất có sàn đa dạng hóa {requested_gold_floor:.0%}; số tiền thực tế làm tròn theo một chỉ hoặc một miếng."]
                if gold_floor_applied
                else []
            ),
        ],
        solver_status="OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE",
        solve_time_ms=solve_ms,
    )


def optimize_scenarios(
    products: list[AssetProduct],
    profile: UserFinancialProfile,
    financial_plan: FinancialPlan,
    recommendation_id: str,
    scenario_count: int,
) -> tuple[list[PortfolioScenario], InfeasibilityReport, BoundedResolveTrace]:
    scenarios: list[PortfolioScenario] = []
    seen_signatures: set[tuple[tuple[str, int], ...]] = set()
    for config in SCENARIO_CONFIGS:
        scenario = _solve_one(
            products,
            profile,
            financial_plan,
            config,
            recommendation_id,
        )
        if scenario is None:
            continue
        baseline = _solve_one(
            products,
            profile,
            financial_plan,
            config,
            recommendation_id,
            complexity_multiplier=0.0,
        )
        if baseline is not None:
            optimized_ids = {item.product_id for item in scenario.product_allocations}
            baseline_ids = {item.product_id for item in baseline.product_allocations}
            scenario = scenario.model_copy(
                update={
                    "complexity_excluded_product_ids": sorted(
                        baseline_ids - optimized_ids
                    )
                }
            )
        signature = tuple(
            sorted((item.product_id, item.amount) for item in scenario.product_allocations)
        )
        if signature not in seen_signatures:
            scenarios.append(scenario)
            seen_signatures.add(signature)
        if len(scenarios) >= scenario_count:
            break

    resolve_trace = verify_amount_dependent_state(scenarios, products)
    if len(scenarios) >= 2:
        return scenarios, InfeasibilityReport(is_infeasible=False), resolve_trace

    conflicts: list[str] = []
    if financial_plan.investable_capital <= 0:
        conflicts.append("NON_POSITIVE_INVESTABLE_CAPITAL")
    if not products:
        conflicts.append("EMPTY_ELIGIBLE_UNIVERSE")
    if profile.liquidity_need > financial_plan.investable_capital:
        conflicts.append("LIQUIDITY_NEED_EXCEEDS_INVESTABLE_CAPITAL")
    if not conflicts:
        conflicts.extend(
            [
                "RISK_LIQUIDITY_AND_MINIMUM_INVESTMENT_CONSTRAINTS_CONFLICT",
                "INSUFFICIENT_DISTINCT_FEASIBLE_SCENARIOS",
            ]
        )
    return (
        scenarios,
        InfeasibilityReport(
            is_infeasible=True,
            conflicting_constraints=conflicts,
            safe_fallback=(
                "Giữ vốn ở CASH nội bộ và xem lại thời hạn, nhu cầu thanh khoản hoặc vốn tối thiểu. "
                "Hệ thống không tự nới lỏng ràng buộc."
            ),
        ),
        resolve_trace,
    )

def reoptimize_scenario_for_complexity(
    products: list[AssetProduct],
    profile: UserFinancialProfile,
    financial_plan: FinancialPlan,
    current: PortfolioScenario,
    recommendation_id: str,
) -> PortfolioScenario:
    """Re-solve exactly one scenario with a bounded, auditable complexity boost."""

    next_count = current.complexity_resolve_count + 1
    if next_count > 3:
        raise ValueError("COMPLEXITY_RESOLVE_LIMIT_REACHED")
    config = next(
        item for item in SCENARIO_CONFIGS if item.style == current.style
    )
    complexity_config = get_complexity_config()
    solved = _solve_one(
        products,
        profile,
        financial_plan,
        config,
        recommendation_id,
        complexity_multiplier=complexity_config.resolve_boost * next_count,
        complexity_resolve_count=next_count,
    )
    if solved is None:
        raise ValueError("COMPLEXITY_RESOLVE_INFEASIBLE")

    previous_ids = {item.product_id for item in current.product_allocations}
    solved_ids = {item.product_id for item in solved.product_allocations}
    excluded = sorted(
        set(solved.complexity_excluded_product_ids) | (previous_ids - solved_ids)
    )
    delta_amount = solved.expected_return_amount - current.expected_return_amount
    delta_rate = solved.expected_return_rate - current.expected_return_rate
    return solved.model_copy(
        update={
            "scenario_id": current.scenario_id,
            "complexity_excluded_product_ids": excluded,
            "complexity_return_delta_amount": delta_amount,
            "complexity_return_delta_rate": delta_rate,
            "trade_offs": [
                *solved.trade_offs,
                (
                    f"Lần gộp {next_count}/3 thay đổi lợi nhuận kỳ vọng "
                    f"{delta_amount:+,} VND/năm ({delta_rate:+.2%}) so với trạng thái trước."
                ),
            ],
        }
    )

def verify_amount_dependent_state(
    scenarios: list[PortfolioScenario],
    products: list[AssetProduct],
    *,
    max_iterations: int = 3,
) -> BoundedResolveTrace:
    """Verify quote/tier state with an explicit bounded loop and cycle detection.

    The registered MVP snapshot is deterministic, so a correctly modeled CP-SAT
    solution normally converges in the first iteration. If a future quote adapter
    changes a rate without producing a new allocation state, the repeated signature
    is reported as a cycle instead of silently relaxing constraints.
    """

    product_map = {product.product_id: product for product in products}
    seen_signatures: set[str] = set()
    iterations: list[ResolveIteration] = []

    for iteration in range(1, max_iterations + 1):
        signature_payload: list[str] = []
        mismatches: list[str] = []
        repricing_products: list[str] = []
        for scenario in scenarios:
            for allocation in scenario.product_allocations:
                product = product_map[allocation.product_id]
                if product.repricing_required:
                    repricing_products.append(product.product_id)
                expected_rate, expected_cost, segment = _rate_and_segment(
                    product,
                    allocation.amount,
                )
                signature_payload.append(
                    (
                        f"{scenario.scenario_id}:{product.product_id}:{allocation.amount}:"
                        f"{expected_rate:.8f}:{expected_cost:.8f}:{segment or '-'}"
                    )
                )
                if (
                    product.repricing_required
                    and abs(allocation.expected_return_rate - expected_rate) > 1e-9
                ):
                    mismatches.append(product.product_id)

        signature = sha256(
            "|".join(sorted(signature_payload)).encode("utf-8")
        ).hexdigest()[:16]
        cycle_detected = signature in seen_signatures
        if cycle_detected:
            iterations.append(
                ResolveIteration(
                    iteration=iteration,
                    state_signature=signature,
                    repricing_required_products=sorted(set(repricing_products)),
                    mismatch_products=sorted(set(mismatches)),
                    cycle_detected=True,
                    status="CYCLE_DETECTED",
                )
            )
            return BoundedResolveTrace(
                max_iterations=max_iterations,
                iterations=iterations,
                converged=False,
                cycle_detected=True,
            )
        seen_signatures.add(signature)

        if not mismatches:
            iterations.append(
                ResolveIteration(
                    iteration=iteration,
                    state_signature=signature,
                    repricing_required_products=sorted(set(repricing_products)),
                    mismatch_products=[],
                    cycle_detected=False,
                    status="STABLE",
                )
            )
            return BoundedResolveTrace(
                max_iterations=max_iterations,
                iterations=iterations,
                converged=True,
                cycle_detected=False,
            )

        iterations.append(
            ResolveIteration(
                iteration=iteration,
                state_signature=signature,
                repricing_required_products=sorted(set(repricing_products)),
                mismatch_products=sorted(set(mismatches)),
                cycle_detected=False,
                status=(
                    "MAX_ITERATIONS"
                    if iteration == max_iterations
                    else "RESOLVE_REQUIRED"
                ),
            )
        )

    return BoundedResolveTrace(
        max_iterations=max_iterations,
        iterations=iterations,
        converged=False,
        cycle_detected=False,
    )
