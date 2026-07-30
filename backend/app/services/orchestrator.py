from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from backend.app.core.config import get_settings
from backend.app.data.mock_asset_products import load_mock_asset_products
from backend.app.db.repository import append_audit, save_recommendation
from backend.app.db import fetch_asset_products, upsert_asset_products
from backend.app.models import (
    AssetProduct,
    FullCalculationOutput,
    PlanningRequest,
    ProductSelectionDecision,
    RecommendationResponse,
    SelectionStatus,
)
from backend.app.services.compliance import apply_output_policy, compliance_findings
from backend.app.services.explanation import explain_released_output
from backend.app.services.financial_planning import build_financial_plan
from backend.app.services.legal import resolve_legal_mode
from backend.app.services.market_data import market_data_summary
from backend.app.services.optimizer import (
    optimize_scenarios,
    reoptimize_scenario_for_complexity,
    verify_amount_dependent_state,
)
from backend.app.services.universe import build_product_universe


PIPELINE_STEPS = [
    "01_LEGAL_PERIMETER_GATE",
    "02_FINANCIAL_PLANNING",
    "03_LIQUIDITY_BUCKETS_AND_INTERNAL_CASH",
    "04_REGISTERED_DATA_SNAPSHOT",
    "05_DATA_NORMALIZATION_AND_GOVERNANCE",
    "06_ASSET_AGENTS_AND_FEASIBLE_SEGMENTS",
    "07_RISK_ANALYSIS_PARAMETERS",
    "08_COUPLED_MASTER_OPTIMIZER",
    "09_RECONFIRM_AMOUNT_DEPENDENT_QUOTES",
    "10_BOUNDED_RESOLVE_AND_CYCLE_DETECTION",
    "11_COMPLIANCE_LEGAL_RELEASE_GATE",
    "12_OUTPUT_POLICY_ENGINE",
    "13_EXPLANATION_LAYER_RELEASED_SCHEMA_ONLY",
]


def _load_products() -> list[AssetProduct]:
    synchronize_mock_product_definitions()
    rows = fetch_asset_products(approved_only=True)
    return [AssetProduct.model_validate(row) for row in rows]


def synchronize_mock_product_definitions() -> int:
    """Refresh code-owned mock rows without re-enabling restricted fallbacks."""

    settings = get_settings()
    canonical_products = load_mock_asset_products(settings.data_dir)
    existing_rows = fetch_asset_products(approved_only=False)
    if not existing_rows:
        return upsert_asset_products(canonical_products)

    existing_by_id = {
        row["product_id"]: row
        for row in existing_rows
    }
    approved_mock_ids = {
        row["product_id"]
        for row in existing_rows
        if str(row.get("source_registry_id", "")).startswith("MOCK")
        and str(row.get("rights_status", "")) == "APPROVED"
    }
    products_to_refresh = [
        product
        for product in canonical_products
        if product.product_id in approved_mock_ids
        and AssetProduct.model_validate(
            existing_by_id[product.product_id]
        ).model_dump(mode="json")
        != product.model_dump(mode="json")
    ]
    if not products_to_refresh:
        return 0
    return upsert_asset_products(products_to_refresh)


def _build_selection_decisions(
    products: list[AssetProduct],
    universe_decisions: list,
    scenarios: list,
) -> list[ProductSelectionDecision]:
    selected_ids = {
        allocation.product_id
        for scenario in scenarios
        for allocation in scenario.product_allocations
    }
    selected_reason_codes: dict[str, set[str]] = {}
    for scenario in scenarios:
        for allocation in scenario.product_allocations:
            selected_reason_codes.setdefault(allocation.product_id, set()).update(
                allocation.reason_codes
            )
    complexity_excluded_ids = {
        product_id
        for scenario in scenarios
        for product_id in scenario.complexity_excluded_product_ids
    }
    product_map = {product.product_id: product for product in products}
    investable_capital = scenarios[0].investable_capital if scenarios else 0
    decisions: list[ProductSelectionDecision] = []
    for eligibility in universe_decisions:
        product = product_map[eligibility.product_id]
        if not eligibility.eligible:
            status = SelectionStatus.REJECTED
            reason_codes = eligibility.reason_codes
            reasons = eligibility.reasons
        elif product.product_id in selected_ids:
            status = SelectionStatus.SELECTED_INTERNAL
            reason_codes = [
                "SELECTED_BY_COUPLED_OPTIMIZER",
                "WITHIN_PRODUCT_AND_PORTFOLIO_CONSTRAINTS",
            ]
            if (
                product.asset_class.value == "GOLD"
                and "STRATEGIC_GOLD_DIVERSIFIER_FLOOR"
                in selected_reason_codes.get(product.product_id, set())
            ):
                reason_codes.append("STRATEGIC_GOLD_DIVERSIFIER_FLOOR")
                reasons = [
                    f"{product.product_name} được chọn theo đơn vị vật chất nguyên chiếc để bổ sung vai trò đa dạng hóa; tỷ trọng thực tế bị làm tròn theo giá một chỉ hoặc một miếng.",
                    (
                        f"Optimizer vẫn kiểm tra lợi nhuận mô hình {product.expected_return * 100:.2f}%/năm, "
                        f"biến động {product.volatility * 100:.2f}%, chênh lệch mua–bán và "
                        f"thanh khoản {product.liquidity_score}/100."
                    ),
                ]
            elif (
                product.asset_class.value == "BOND_FUND"
                and "STRATEGIC_FIXED_INCOME_DIVERSIFIER_FLOOR"
                in selected_reason_codes.get(product.product_id, set())
            ):
                reason_codes.append("STRATEGIC_FIXED_INCOME_DIVERSIFIER_FLOOR")
                reasons = [
                    (
                        f"{product.product_name} tạo lớp thu nhập cố định ngoài tiền gửi, "
                        "giúp phương án dài hạn không phụ thuộc hoàn toàn vào một cơ chế "
                        "lãi suất ngân hàng."
                    ),
                    (
                        f"Optimizer vẫn kiểm tra lợi nhuận mô hình "
                        f"{product.expected_return * 100:.2f}%/năm, biến động "
                        f"{product.volatility * 100:.2f}%, thanh khoản "
                        f"{product.liquidity_score}/100 và giới hạn số ứng dụng của hồ sơ."
                    ),
                ]
            else:
                reasons = [
                    (
                        f"{product.product_name} được optimizer chọn sau khi đồng thời xét số vốn, "
                        f"quy tắc lô/bậc lãi suất, lợi nhuận mô hình {product.expected_return * 100:.2f}%/năm, "
                        f"biến động {product.volatility * 100:.2f}% và thanh khoản "
                        f"{product.liquidity_score}/100 trong các ràng buộc của hồ sơ."
                    )
                ]
        else:
            status = SelectionStatus.ELIGIBLE_NOT_SELECTED
            product_cap = investable_capital * (product.max_weight_hint or 1.0)
            if product.product_id in complexity_excluded_ids:
                reason_codes = ["EXCLUDED_TO_REDUCE_FRAGMENTATION"]
                reasons = [
                    (
                        f"{product.product_name} vẫn đủ điều kiện, nhưng không được bật trong "
                        "kịch bản này vì nghiệm bốn chiều ưu tiên giảm số sản phẩm, tổ chức "
                        "hoặc kỳ hạn phải theo dõi. Đây không phải lỗi eligibility hay thanh khoản."
                    )
                ]
            elif (
                product.asset_class.value == "GOLD"
                and product.minimum_investment > product_cap
            ):
                reason_codes = ["PHYSICAL_UNIT_EXCEEDS_PRODUCT_WEIGHT_CAP"]
                reasons = [
                    (
                        f"{product.product_name} cần tối thiểu {product.minimum_investment:,.0f} VND "
                        f"cho một đơn vị, cao hơn phần vốn tối đa {product_cap:,.0f} VND theo trần "
                        "tỷ trọng của danh mục này; vì vậy sản phẩm không thể được bật."
                    )
                ]
            else:
                reason_codes = ["ELIGIBLE_BUT_NOT_SELECTED_IN_SCENARIO_SET"]
                reasons = [
                    (
                        f"{product.product_name} đáp ứng điều kiện vốn và kỳ hạn, nhưng với lợi nhuận "
                        f"mô hình {product.expected_return * 100:.2f}%/năm, biến động "
                        f"{product.volatility * 100:.2f}% và thanh khoản {product.liquidity_score}/100, "
                        "sản phẩm không cải thiện mục tiêu của ba phương án được phát hành."
                    )
                ]
        decisions.append(
            ProductSelectionDecision(
                product_id=product.product_id,
                product_name=product.product_name,
                provider=product.provider,
                asset_class=product.asset_class,
                status=status,
                reason_codes=reason_codes,
                reasons=reasons,
                expected_return=product.expected_return,
                volatility=product.volatility,
                liquidity_score=product.liquidity_score,
                minimum_investment=product.minimum_investment,
                lockup_period_days=product.lockup_period,
                data_timestamp=product.data_timestamp,
            )
        )
    return decisions


def run_planning_pipeline(
    request: PlanningRequest,
    *,
    persist: bool = True,
) -> tuple[RecommendationResponse, FullCalculationOutput]:
    settings = get_settings()
    recommendation_id = f"AQ26-{datetime.now():%Y%m%d}-{uuid4().hex[:10].upper()}"
    mode, legal_reasons = resolve_legal_mode(
        request.requested_mode,
        request.legal_evidence,
    )
    financial_plan = build_financial_plan(request.profile)
    products = _load_products()
    data_summary = market_data_summary()
    data_snapshot = data_summary["snapshot_id"]
    eligible_products, universe = build_product_universe(products, request.profile)
    scenarios, infeasibility, bounded_resolve = optimize_scenarios(
        eligible_products,
        request.profile,
        financial_plan,
        recommendation_id,
        request.scenario_count,
    )
    scenarios = [
        scenario.model_copy(
            update={
                "selection_decisions": _build_selection_decisions(
                    products,
                    universe.decisions,
                    [scenario],
                )
            }
        )
        for scenario in scenarios
    ]
    selection_decisions = _build_selection_decisions(
        products,
        universe.decisions,
        scenarios,
    )

    stale_products = [
        product.product_id
        for product in products
        if (datetime.now(product.data_timestamp.tzinfo) - product.data_timestamp).days > 120
    ]
    mock_classes = sorted(
        {
            str(product.asset_class)
            for product in products
            if product.source_registry_id.startswith("MOCK")
        }
    )
    degraded_sources = [
        source["display_name"]
        for source in data_summary["sources"]
        if source["operational_status"] in {"ERROR", "STALE_FALLBACK"}
    ]
    warnings = [
        (
            "Giá, lãi suất và NAV được lấy từ snapshot chính thức có độ trễ; "
            "cần xác nhận lại tại đơn vị cung cấp trước mọi quyết định bên ngoài hệ thống."
        ),
        (
            "Expected return, volatility, VaR và CVaR là giả định mô hình, "
            "không phải cam kết lợi nhuận."
        ),
        *(
            [
                "Các nhóm chưa có nguồn được cấp quyền vẫn dùng dữ liệu mô phỏng: "
                + ", ".join(mock_classes)
                + "."
            ]
            if mock_classes
            else []
        ),
        *(
            [
                "Nguồn đang lỗi hoặc quá hạn; hệ thống giữ snapshot gần nhất: "
                + ", ".join(degraded_sources)
            ]
            if degraded_sources
            else []
        ),
        *([f"STALE_DATA:{','.join(stale_products)}"] if stale_products else []),
    ]
    full_output = FullCalculationOutput(
        recommendation_id=recommendation_id,
        calculated_at=datetime.now().astimezone(),
        legal_operating_mode=mode,
        data_snapshot=data_snapshot,
        model_version=settings.model_version,
        financial_plan=financial_plan,
        universe=universe,
        selection_decisions=selection_decisions,
        scenarios=scenarios,
        infeasibility=infeasibility,
        bounded_resolve=bounded_resolve,
        pipeline_trace=PIPELINE_STEPS,
        assumptions=[
            *financial_plan.assumptions,
            "Covariance dùng ma trận tương quan giả định theo nhóm tài sản cho stress/risk demo.",
            "CP-SAT giải đồng thời số tiền sản phẩm, bậc lãi suất, bước làm tròn và trần nhóm tài sản.",
            "Bounded re-solve dừng khi state signature ổn định; dữ liệu có cờ repricing phải được xác nhận lại trước quyết định ngoài hệ thống.",
            *legal_reasons,
        ],
        warnings=warnings,
    )

    # The release gate is deliberately evaluated again after all calculations.
    final_mode, final_legal_reasons = resolve_legal_mode(
        request.requested_mode,
        request.legal_evidence,
    )
    if final_mode != full_output.legal_operating_mode:
        full_output = full_output.model_copy(update={"legal_operating_mode": final_mode})
    if final_legal_reasons != legal_reasons:
        full_output.assumptions.extend(final_legal_reasons)

    released = apply_output_policy(full_output)
    explanation = explain_released_output(released)
    response = RecommendationResponse(
        released_output=released,
        explanation=explanation,
    )

    if persist:
        save_recommendation(request, full_output, response)
        audit_payloads = [
            ("LegalPerimeterGate", {"mode": mode, "reason_codes": legal_reasons}),
            ("FinancialPlanning", financial_plan),
            (
                "LiquidityBuckets",
                {
                    "immediate": financial_plan.immediate_liquidity_bucket,
                    "medium": financial_plan.medium_term_bucket,
                    "long_term": financial_plan.long_term_capacity,
                },
            ),
            (
                "DataSnapshotRegistry",
                {
                    "snapshot": data_snapshot,
                    "mode": data_summary["mode"],
                    "sources": data_summary["sources"],
                },
            ),
            ("DataNormalization", {"product_count": len(products)}),
            ("AssetAgentRegistry", universe),
            (
                "RiskEngine",
                {"scenario_risk": [item.risk_metrics for item in scenarios]},
            ),
            (
                "MasterOptimizer",
                {
                    "scenario_ids": [item.scenario_id for item in scenarios],
                    "infeasibility": infeasibility,
                    "operational_complexity": [
                        {
                            "scenario_id": item.scenario_id,
                            "score": item.operational_complexity_score,
                            "breakdown": item.complexity_breakdown,
                            "config_version": item.complexity_config_version,
                            "fragmentation_warning": item.fragmentation_warning,
                        }
                        for item in scenarios
                    ],
                },
            ),
            ("QuoteReconfirmation", {"status": "STABLE_WITHIN_MODELED_SEGMENTS"}),
            (
                "BoundedResolve",
                {
                    "iterations": len(bounded_resolve.iterations),
                    "cycle_detected": bounded_resolve.cycle_detected,
                    "converged": bounded_resolve.converged,
                    "states": bounded_resolve.iterations,
                },
            ),
            (
                "ComplianceReleaseGate",
                {"findings": compliance_findings(full_output)},
            ),
            (
                "OutputPolicyEngine",
                {
                    "release_type": released.output_release_type,
                    "mode": released.legal_operating_mode,
                },
            ),
            (
                "ExplanationAgent",
                {"generated_by": explanation.generated_by},
            ),
        ]
        for index, (module_name, output_data) in enumerate(audit_payloads, start=1):
            append_audit(
                module_name=module_name,
                event_type=f"PIPELINE_STEP_{index:02d}_COMPLETED",
                recommendation_id=recommendation_id,
                user_id=request.profile.user_id,
                input_data=request if index == 1 else None,
                output_data=output_data,
            )

    return response, full_output


def run_complexity_resolve(
    stored: dict[str, Any],
    scenario_id: str,
) -> tuple[RecommendationResponse, FullCalculationOutput]:
    """Re-solve only the selected scenario and preserve the other scenarios verbatim."""

    request = PlanningRequest.model_validate(stored["request"])
    full_output = FullCalculationOutput.model_validate(stored["full_output"])
    target_index = next(
        (
            index
            for index, scenario in enumerate(full_output.scenarios)
            if scenario.scenario_id == scenario_id
        ),
        None,
    )
    if target_index is None:
        raise ValueError("SCENARIO_NOT_FOUND")

    products = _load_products()
    eligible_products, universe = build_product_universe(products, request.profile)
    current = full_output.scenarios[target_index]
    resolved = reoptimize_scenario_for_complexity(
        eligible_products,
        request.profile,
        full_output.financial_plan,
        current,
        full_output.recommendation_id,
    )
    resolved = resolved.model_copy(
        update={
            "selection_decisions": _build_selection_decisions(
                products,
                universe.decisions,
                [resolved],
            )
        }
    )
    scenarios = list(full_output.scenarios)
    scenarios[target_index] = resolved
    bounded_resolve = verify_amount_dependent_state(scenarios, eligible_products)
    selection_decisions = _build_selection_decisions(
        products,
        universe.decisions,
        scenarios,
    )
    updated_full = full_output.model_copy(
        update={
            "calculated_at": datetime.now().astimezone(),
            "universe": universe,
            "selection_decisions": selection_decisions,
            "scenarios": scenarios,
            "bounded_resolve": bounded_resolve,
        }
    )
    released = apply_output_policy(updated_full)
    explanation = explain_released_output(released)
    response = RecommendationResponse(
        released_output=released,
        explanation=explanation,
    )
    save_recommendation(request, updated_full, response)
    append_audit(
        module_name="MasterOptimizer",
        event_type="COMPLEXITY_RESOLVE_COMPLETED",
        recommendation_id=updated_full.recommendation_id,
        user_id=request.profile.user_id,
        input_data={
            "scenario_id": scenario_id,
            "previous_complexity_score": current.operational_complexity_score,
            "resolve_iteration": resolved.complexity_resolve_count,
        },
        output_data={
            "scenario_id": scenario_id,
            "complexity_score": resolved.operational_complexity_score,
            "complexity_breakdown": resolved.complexity_breakdown,
            "complexity_config_version": resolved.complexity_config_version,
            "return_delta_amount": resolved.complexity_return_delta_amount,
            "return_delta_rate": resolved.complexity_return_delta_rate,
            "bounded_resolve": bounded_resolve,
        },
    )
    return response, updated_full
