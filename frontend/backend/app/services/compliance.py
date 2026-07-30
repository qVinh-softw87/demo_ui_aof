from __future__ import annotations

import re
from datetime import datetime

from backend.app.models import (
    AllocationExplanation,
    AssetClass,
    DepositImplementationDetail,
    FullCalculationOutput,
    LegalOperatingMode,
    MonitoringTrigger,
    OutputReleaseType,
    PortfolioScenario,
    ReleasedOutput,
    ReleasedScenario,
    ScenarioStyle,
    WithdrawalOption,
)


def _money(value: int | float) -> str:
    return f"{round(value):,}".replace(",", ".") + " VND"


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%".replace(".", ",")


_PORTFOLIO_ROLES: dict[AssetClass, str] = {
    AssetClass.CASH: "Thanh khoản tức thời và vùng đệm để tránh phải bán tài sản khác khi cần tiền.",
    AssetClass.DEPOSIT: "Ổn định vốn và tạo dòng lợi nhuận dự kiến tương đối dễ theo dõi.",
    AssetClass.BOND_FUND: "Tạo thu nhập phòng thủ và đa dạng hóa ngoài tiền gửi.",
    AssetClass.EQUITY: "Động lực tăng trưởng dài hạn, chấp nhận biến động giá cao hơn.",
    AssetClass.ETF: "Tiếp cận tăng trưởng cổ phiếu theo rổ, giảm phụ thuộc vào một mã riêng lẻ.",
    AssetClass.GOLD: "Đa dạng hóa trước cú sốc thị trường và rủi ro sức mua của tiền.",
    AssetClass.SILVER: "Đa dạng hóa bằng kim loại quý nhưng có độ nhạy giá cao hơn vàng.",
    AssetClass.GOVERNMENT_BOND_REFERENCE: "Mốc thu nhập phòng thủ để so sánh với các tài sản rủi ro hơn.",
}

_LIMITING_FACTORS: dict[AssetClass, str] = {
    AssetClass.CASH: "Giữ quá nhiều tiền mặt làm giảm lợi nhuận kỳ vọng và sức mua có thể bị bào mòn.",
    AssetClass.DEPOSIT: "Tỷ trọng quá cao tạo rủi ro tập trung và lợi suất có thể giảm khi tái tục.",
    AssetClass.BOND_FUND: "Giá quỹ có thể giảm khi lãi suất tăng; đây không phải tiền gửi được cố định giá.",
    AssetClass.EQUITY: "Biến động và mức sụt giảm có thể lớn, nên tỷ trọng bị giới hạn bởi ngân sách rủi ro.",
    AssetClass.ETF: "Vẫn chịu rủi ro thị trường cổ phiếu dù đã đa dạng hóa theo rổ.",
    AssetClass.GOLD: "Không tạo dòng tiền định kỳ và giá có thể biến động mạnh theo tâm lý thị trường.",
    AssetClass.SILVER: "Biến động giá và chênh lệch giao dịch thường cao hơn tài sản phòng thủ.",
    AssetClass.GOVERNMENT_BOND_REFERENCE: "Lợi nhuận thực có thể thấp và giá vẫn nhạy với thay đổi lãi suất.",
}

_CHANGE_TRIGGERS: dict[AssetClass, str] = {
    AssetClass.CASH: "Tính lại khi nhu cầu rút tiền, quỹ dự phòng hoặc nghĩa vụ gần hạn thay đổi.",
    AssetClass.DEPOSIT: "Tính lại khi thời hạn mục tiêu, nhu cầu thanh khoản hoặc mặt bằng lãi suất thay đổi.",
    AssetClass.BOND_FUND: "Tính lại khi thời hạn đầu tư, khả năng khóa vốn hoặc kịch bản lãi suất thay đổi.",
    AssetClass.EQUITY: "Tính lại khi thời hạn mục tiêu, mức sụt giảm chấp nhận được hoặc risk capacity thay đổi.",
    AssetClass.ETF: "Tính lại khi thời hạn mục tiêu, ngân sách rủi ro hoặc nhu cầu rút vốn thay đổi.",
    AssetClass.GOLD: "Tính lại khi mục tiêu phòng thủ, mức tập trung danh mục hoặc ngân sách rủi ro thay đổi.",
    AssetClass.SILVER: "Tính lại khi khả năng chịu biến động hoặc giới hạn tập trung thay đổi.",
    AssetClass.GOVERNMENT_BOND_REFERENCE: "Tính lại khi kỳ hạn mục tiêu hoặc giả định lãi suất thay đổi.",
}


def _allocation_explanations(
    scenario: PortfolioScenario,
    immediate_liquidity_bucket: int,
    data_snapshot: str,
    *,
    advisory: bool,
) -> list[AllocationExplanation]:
    style_reason = {
        ScenarioStyle.CAPITAL_PRESERVATION: (
            "Phương án ưu tiên bảo toàn vốn và khả năng sử dụng tiền."
        ),
        ScenarioStyle.BALANCED: (
            "Phương án cân bằng giữa thanh khoản, ổn định và tăng trưởng."
        ),
        ScenarioStyle.GROWTH: (
            "Phương án dành thêm ngân sách rủi ro cho mục tiêu tăng trưởng dài hạn."
        ),
    }[scenario.style]

    worst_stress = min(
        scenario.risk_metrics.stress_tests,
        key=lambda item: item.estimated_change_amount,
        default=None,
    )
    released_allocations = (
        list(scenario.product_allocations)
        if advisory
        else list(scenario.asset_class_allocations)
    )
    explanations: list[AllocationExplanation] = []
    for allocation in sorted(released_allocations, key=lambda item: item.amount, reverse=True):
        grouped_products = [
            item
            for item in scenario.product_allocations
            if item.asset_class == allocation.asset_class
        ]
        expected_return_rate = (
            allocation.expected_return_rate
            if advisory
            else (
                allocation.expected_return_amount / allocation.amount
                if allocation.amount
                else 0
            )
        )
        liquidity_score = (
            allocation.liquidity_score
            if advisory
            else (
                sum(item.amount * item.liquidity_score for item in grouped_products)
                / sum(item.amount for item in grouped_products)
                if grouped_products
                else 0
            )
        )
        liquidity_link = (
            f" Hồ sơ đồng thời cần bucket thanh khoản tức thời "
            f"{_money(immediate_liquidity_bucket)}."
            if allocation.asset_class in {AssetClass.CASH, AssetClass.DEPOSIT}
            else ""
        )
        explanations.append(
            AllocationExplanation(
                asset_class=allocation.asset_class,
                product_id=allocation.product_id if advisory else None,
                product_name=allocation.product_name if advisory else None,
                provider=allocation.provider if advisory else None,
                amount=allocation.amount,
                weight=allocation.weight,
                expected_return_rate=expected_return_rate,
                expected_return_amount=allocation.expected_return_amount,
                transaction_cost_amount=allocation.transaction_cost_amount,
                liquidity_score=round(liquidity_score, 1),
                portfolio_role=_PORTFOLIO_ROLES[allocation.asset_class],
                allocation_reason=(
                    f"Optimizer phân bổ {_money(allocation.amount)} "
                    f"({_pct(allocation.weight)}) vào "
                    f"{allocation.product_name if advisory else 'nhóm tài sản này'}; "
                    f"đóng góp lợi nhuận kỳ vọng {_money(allocation.expected_return_amount)}/năm. "
                    f"{style_reason}{liquidity_link} Nghiệm nằm trong trần rủi ro "
                    f"{_pct(scenario.risk_metrics.risk_ceiling)}."
                ),
                limiting_factor=_LIMITING_FACTORS[allocation.asset_class],
                change_trigger=_CHANGE_TRIGGERS[allocation.asset_class],
                expected_return_and_risk=(
                    f"Lợi nhuận kỳ vọng {_pct(expected_return_rate)}/năm, tương ứng "
                    f"{_money(allocation.expected_return_amount)}. Ở cấp danh mục: biến động "
                    f"{_pct(scenario.risk_metrics.annualized_volatility)}, VaR 95% "
                    f"{_money(scenario.risk_metrics.var_95_amount)}, CVaR 95% "
                    f"{_money(scenario.risk_metrics.cvar_95_amount)}; không phải cam kết."
                ),
                cost_and_liquidity=(
                    f"Chi phí mô hình {_money(allocation.transaction_cost_amount)}; "
                    f"điểm thanh khoản {liquidity_score:.1f}/100. "
                    "Chi phí thoát thực tế phải được báo giá lại khi thực hiện."
                ),
                execution_conditions=(
                    [
                        allocation.execution_instruction,
                        *(
                            [f"Phân khúc/tier được chọn: {allocation.selected_segment}"]
                            if allocation.selected_segment
                            else []
                        ),
                    ]
                    if advisory
                    else [
                        (
                            (
                                f"{len(grouped_products)} khoản tiền gửi đã vượt eligibility; "
                                "ngân hàng, kỳ hạn và số vốn được công bố trong breakdown tiền gửi."
                            )
                            if allocation.asset_class == AssetClass.DEPOSIT
                            else (
                                f"{len(grouped_products)} sản phẩm nội bộ đã vượt eligibility; "
                                "chi tiết mã và số tiền chỉ phát hành khi Legal Gate cho phép advisory."
                            )
                        )
                    ]
                ),
                adverse_scenario=(
                    (
                        f"{worst_stress.scenario_name}: danh mục thay đổi ước tính "
                        f"{_money(worst_stress.estimated_change_amount)} "
                        f"({_pct(worst_stress.estimated_change_pct)}). "
                        f"Giả định: {worst_stress.assumptions}"
                    )
                    if worst_stress
                    else "Chưa có stress test được phát hành."
                ),
                data_evidence=(
                    [
                        allocation.source_reference,
                        f"Thời điểm dữ liệu: {allocation.data_timestamp.isoformat()}",
                        f"Snapshot: {data_snapshot}",
                    ]
                    if advisory
                    else [
                        f"Snapshot dữ liệu đã kiểm duyệt: {data_snapshot}",
                        "Số liệu nhóm được cộng trực tiếp từ phân bổ sản phẩm của optimizer.",
                    ]
                ),
                result_sensitive_assumptions=[
                    "Expected return và covariance là giả định mô hình, không phải dự báo chắc chắn.",
                    "Giá, lãi suất, NAV, eligibility và chi phí phải được xác nhận lại trước thực hiện.",
                    _CHANGE_TRIGGERS[allocation.asset_class],
                ],
            )
        )
    return explanations


def _monitoring_triggers(
    scenario: PortfolioScenario,
    data_snapshot: str,
) -> list[MonitoringTrigger]:
    return [
        MonitoringTrigger(
            trigger_type="ADDITIONAL_CAPITAL",
            trigger_condition="Có bất kỳ khoản nạp thêm nào.",
            current_reference=f"Vốn hiện tại {_money(scenario.investable_capital)}.",
            action="Chạy lại eligibility, optimizer, risk và Compliance Gate.",
        ),
        MonitoringTrigger(
            trigger_type="WITHDRAWAL_REQUEST",
            trigger_condition="Phát sinh nhu cầu rút vốn hoặc thay đổi thời điểm cần tiền.",
            current_reference=f"Thanh khoản hiện tại {scenario.risk_metrics.liquidity_score:.1f}/100.",
            action="So sánh tiền mặt, tất toán tiền gửi, bán tài sản thanh khoản cao và bán theo tỷ lệ.",
        ),
        MonitoringTrigger(
            trigger_type="GOAL_OR_HORIZON_CHANGE",
            trigger_condition="Số tiền mục tiêu, mức ưu tiên hoặc thời hạn thay đổi.",
            current_reference=f"Phương án hiện tại: {scenario.name}.",
            action="Tính lại bucket thời gian và toàn bộ ràng buộc.",
        ),
        MonitoringTrigger(
            trigger_type="RISK_PROFILE_CHANGE",
            trigger_condition="Risk tolerance, risk capacity hoặc mức sụt giảm chấp nhận thay đổi.",
            current_reference=f"Trần rủi ro {_pct(scenario.risk_metrics.risk_ceiling)}.",
            action="Tính lại risk budget và chặn phương án vượt trần mới.",
        ),
        MonitoringTrigger(
            trigger_type="MATERIAL_PRODUCT_DATA_CHANGE",
            trigger_condition="Lãi suất/expected return đổi từ 0,50 điểm % hoặc nguồn quá hạn.",
            current_reference=f"Snapshot {data_snapshot}.",
            action="Định giá lại, kiểm tra tier và chạy bounded re-solve.",
        ),
        MonitoringTrigger(
            trigger_type="PORTFOLIO_DRIFT",
            trigger_condition="Tỷ trọng thực tế lệch mục tiêu từ 5 điểm phần trăm ở bất kỳ nhóm nào.",
            current_reference="Tỷ trọng mục tiêu là cơ cấu được phát hành trong phương án.",
            action="Đánh giá tái cân bằng sau khi tính chi phí và thanh khoản.",
        ),
        MonitoringTrigger(
            trigger_type="USER_REQUEST",
            trigger_condition="Người dùng chủ động yêu cầu phân tích lại.",
            current_reference=f"Mã phương án {scenario.scenario_id}.",
            action="Tạo recommendation mới; không sửa âm thầm phương án đã xác nhận.",
        ),
    ]


def _withdrawal_options(scenario: PortfolioScenario) -> list[WithdrawalOption]:
    by_class = {
        asset_class: sum(
            item.amount
            for item in scenario.product_allocations
            if item.asset_class == asset_class
        )
        for asset_class in AssetClass
    }
    liquid_classes = {
        AssetClass.ETF,
        AssetClass.EQUITY,
        AssetClass.BOND_FUND,
        AssetClass.GOLD,
        AssetClass.SILVER,
    }
    liquid_amount = sum(by_class[item] for item in liquid_classes)
    liquid_cost = sum(
        item.transaction_cost_amount
        for item in scenario.product_allocations
        if item.asset_class in liquid_classes
    )
    return [
        WithdrawalOption(
            option_type="USE_CASH",
            title="Sử dụng tiền mặt trước",
            available_amount=by_class[AssetClass.CASH],
            estimated_cost="0 VND chi phí giao dịch mô hình.",
            portfolio_impact="Ít ảnh hưởng tài sản tăng trưởng nhưng làm giảm vùng đệm thanh khoản.",
            conditions=["Không làm tiền mặt còn lại thấp hơn quỹ dự phòng bắt buộc."],
            priority=1,
        ),
        WithdrawalOption(
            option_type="SELL_HIGH_LIQUIDITY_ASSETS",
            title="Bán tài sản thanh khoản cao",
            available_amount=liquid_amount,
            estimated_cost=(
                f"Chi phí mô hình tham chiếu {_money(liquid_cost)} cho toàn bộ phần này; "
                "phải báo giá lại theo số tiền thực rút."
            ),
            portfolio_impact="Có thể giảm lợi nhuận kỳ vọng và làm lệch cơ cấu tăng trưởng/phòng thủ.",
            conditions=["Ưu tiên tài sản thanh khoản cao đang vượt tỷ trọng mục tiêu."],
            priority=2,
        ),
        WithdrawalOption(
            option_type="BREAK_DEPOSIT",
            title="Tất toán tiền gửi",
            available_amount=by_class[AssetClass.DEPOSIT],
            estimated_cost="Chưa chốt: có thể mất phần lớn lãi kỳ hạn; phải lấy báo giá tất toán.",
            portfolio_impact="Giảm phần ổn định vốn và lợi nhuận kỳ vọng đã tính.",
            conditions=["So sánh ngày đáo hạn và quy định rút trước hạn từng hợp đồng."],
            priority=3,
        ),
        WithdrawalOption(
            option_type="PROPORTIONAL_SALE",
            title="Bán theo tỷ lệ toàn danh mục",
            available_amount=scenario.investable_capital,
            estimated_cost=(
                f"Chi phí mô hình toàn danh mục {_money(scenario.total_cost_amount)}; "
                "chi phí thực tế phụ thuộc số tiền rút."
            ),
            portfolio_impact="Giữ cơ cấu tương đối nhưng phát sinh giao dịch trên nhiều tài sản.",
            conditions=["Chỉ dùng khi các lựa chọn ưu tiên không đáp ứng đủ nhu cầu."],
            priority=4,
        ),
    ]


def _deposit_implementation(
    scenario: PortfolioScenario,
) -> list[DepositImplementationDetail]:
    details: list[DepositImplementationDetail] = []
    for allocation in scenario.product_allocations:
        if allocation.asset_class != AssetClass.DEPOSIT or allocation.amount <= 0:
            continue
        tenor_match = re.search(
            r"(\d+)\s*tháng",
            allocation.product_name,
            flags=re.IGNORECASE,
        ) or re.search(r"-(\d+)m(?:-|$)", allocation.product_id, flags=re.IGNORECASE)
        tenor_months = int(tenor_match.group(1)) if tenor_match else None
        term_interest = (
            round(
                allocation.amount
                * allocation.expected_return_rate
                * tenor_months
                / 12
            )
            if tenor_months
            else None
        )
        details.append(
            DepositImplementationDetail(
                product_id=allocation.product_id,
                bank=allocation.provider,
                product_name=allocation.product_name,
                tenor_months=tenor_months,
                amount=allocation.amount,
                weight=allocation.weight,
                annual_rate=allocation.expected_return_rate,
                annual_interest_amount=allocation.expected_return_amount,
                term_interest_amount=term_interest,
                maturity_amount=(
                    allocation.amount + term_interest
                    if term_interest is not None
                    else None
                ),
                transaction_cost_amount=allocation.transaction_cost_amount,
                liquidity_score=allocation.liquidity_score,
                selected_segment=allocation.selected_segment,
                conditions=[
                    allocation.execution_instruction,
                    *(
                        [f"Tier/phân khúc: {allocation.selected_segment}"]
                        if allocation.selected_segment
                        else []
                    ),
                ],
                why_selected=(
                    "Được optimizer chọn sau khi đồng thời xét số vốn, kỳ hạn khóa vốn, "
                    "tier lãi suất, thanh khoản, giới hạn tập trung và risk ceiling."
                ),
                source_reference=allocation.source_reference,
                data_timestamp=allocation.data_timestamp,
            )
        )
    return sorted(details, key=lambda item: item.amount, reverse=True)


def compliance_findings(output: FullCalculationOutput) -> list[str]:
    findings: list[str] = []
    if output.infeasibility.is_infeasible:
        findings.append("OPTIMIZER_INFEASIBLE_OR_INSUFFICIENT_SCENARIOS")
    if not output.bounded_resolve.converged:
        findings.append("QUOTE_RECONFIRMATION_DID_NOT_CONVERGE")
    for scenario in output.scenarios:
        if not scenario.risk_metrics.within_risk_ceiling:
            findings.append(f"RISK_CEILING_BREACH:{scenario.scenario_id}")
        if scenario.allocated_amount + scenario.residual_cash != scenario.investable_capital:
            findings.append(f"CAPITAL_RECONCILIATION_FAILED:{scenario.scenario_id}")
        if scenario.total_cost_amount < 0 or scenario.expected_return_amount < -scenario.investable_capital:
            findings.append(f"INVALID_QUANTITATIVE_OUTPUT:{scenario.scenario_id}")
        if not scenario.complexity_config_version:
            findings.append(f"MISSING_COMPLEXITY_CONFIG_VERSION:{scenario.scenario_id}")
        for decision in scenario.selection_decisions:
            if (
                "EXCLUDED_TO_REDUCE_FRAGMENTATION" in decision.reason_codes
                and "LIQUIDITY_MISMATCH" in decision.reason_codes
            ):
                findings.append(f"COMPLEXITY_REASON_CODE_MISMATCH:{scenario.scenario_id}")
    return findings


def apply_output_policy(output: FullCalculationOutput) -> ReleasedOutput:
    findings = compliance_findings(output)
    if output.legal_operating_mode == LegalOperatingMode.BLOCKED or findings:
        return ReleasedOutput(
            recommendation_id=output.recommendation_id,
            released_at=datetime.now().astimezone(),
            legal_operating_mode=LegalOperatingMode.BLOCKED,
            output_release_type=OutputReleaseType.BLOCKED,
            data_snapshot=output.data_snapshot,
            model_version=output.model_version,
            assumptions=output.assumptions,
            warnings=[*output.warnings, *findings],
            blocked_message=(
                "Không thể phát hành phương án cá nhân hóa. Hệ thống chỉ cung cấp "
                "nội dung giáo dục an toàn; các ràng buộc không được tự động nới lỏng."
            ),
        )

    advisory = output.legal_operating_mode == LegalOperatingMode.LICENSED_ADVISORY
    released_scenarios = [
        ReleasedScenario(
            scenario_id=scenario.scenario_id,
            name=scenario.name,
            style=scenario.style,
            recommendation_role=(
                "RECOMMENDED"
                if advisory and index == 0
                else "ALTERNATIVE" if advisory else None
            ),
            objective_description=scenario.objective_description,
            investable_capital=scenario.investable_capital,
            expected_return_amount=scenario.expected_return_amount,
            expected_return_rate=scenario.expected_return_rate,
            total_cost_amount=scenario.total_cost_amount,
            allocations=(
                list(scenario.product_allocations)
                if advisory
                else list(scenario.asset_class_allocations)
            ),
            allocation_explanations=_allocation_explanations(
                scenario,
                output.financial_plan.immediate_liquidity_bucket,
                output.data_snapshot,
                advisory=advisory,
            ),
            allocation_granularity="PRODUCT" if advisory else "ASSET_CLASS",
            risk_metrics=scenario.risk_metrics,
            operational_complexity_score=scenario.operational_complexity_score,
            complexity_breakdown=scenario.complexity_breakdown,
            complexity_config_version=scenario.complexity_config_version,
            fragmentation_warning=scenario.fragmentation_warning,
            complexity_resolve_count=scenario.complexity_resolve_count,
            complexity_return_delta_amount=scenario.complexity_return_delta_amount,
            complexity_return_delta_rate=scenario.complexity_return_delta_rate,
            selection_decisions=scenario.selection_decisions,
            trade_offs=scenario.trade_offs,
            monitoring_triggers=_monitoring_triggers(
                scenario,
                output.data_snapshot,
            ),
            withdrawal_options=_withdrawal_options(scenario),
            source_summary=(
                [
                    (
                        f"{item.provider} · {item.product_name} · "
                        f"cập nhật {item.data_timestamp.isoformat()} · {item.source_reference}"
                    )
                    for item in scenario.product_allocations
                ]
                if advisory
                else [
                    f"Snapshot đã kiểm duyệt {output.data_snapshot}.",
                    "Nguồn chi tiết cấp sản phẩm chỉ phát hành trong LICENSED_ADVISORY.",
                ]
            ),
            assumptions_that_change_result=[
                *output.assumptions,
                "Ngưỡng drift vận hành mặc định là 5 điểm phần trăm.",
                "Biến động dữ liệu sản phẩm từ 0,50 điểm % kích hoạt định giá lại.",
            ],
            deposit_implementation=_deposit_implementation(scenario),
        )
        for index, scenario in enumerate(output.scenarios[:3])
    ]
    return ReleasedOutput(
        recommendation_id=output.recommendation_id,
        released_at=datetime.now().astimezone(),
        legal_operating_mode=output.legal_operating_mode,
        output_release_type=(
            OutputReleaseType.ADVISORY_SELECTED
            if advisory
            else OutputReleaseType.COMPARE_ONLY
        ),
        data_snapshot=output.data_snapshot,
        model_version=output.model_version,
        financial_plan=output.financial_plan,
        scenarios=released_scenarios,
        universe=output.universe,
        selection_decisions=output.selection_decisions,
        assumptions=output.assumptions,
        warnings=[
            *output.warnings,
            (
                "Chỉ so sánh phương án theo nhóm tài sản; không phải khuyến nghị "
                "mua mã chứng khoán kèm số tiền."
                if not advisory
                else "Đầu ra tư vấn chỉ hợp lệ trong phạm vi bằng chứng pháp lý đã xác minh."
            ),
        ],
        human_confirmation_required=True,
    )
