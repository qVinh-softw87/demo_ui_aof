from __future__ import annotations

import json

from backend.app.models import ExplanationPayload, ReleasedOutput
from backend.app.services.complexity import explain_complexity_payload
from backend.app.services.llm import generate_structured


def _money(value: int | float) -> str:
    return f"{round(value):,}".replace(",", ".") + " VND"


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%".replace(".", ",")


def _fallback_explanation(released: ReleasedOutput) -> ExplanationPayload:
    if released.output_release_type == "BLOCKED":
        reasoning = [
            "Hệ thống không phát hành phương án vì phạm vi pháp lý hoặc kiểm tra tuân thủ chưa đạt.",
            "Các ràng buộc định lượng vẫn được giữ nguyên; không có bước tự nới lỏng.",
        ]
    else:
        scenario_reasoning: list[str] = []
        for scenario in released.scenarios:
            worst_stress = min(
                scenario.risk_metrics.stress_tests,
                key=lambda item: item.estimated_change_amount,
                default=None,
            )
            scenario_reasoning.append(
                (
                    f"{scenario.name}: vốn {_money(scenario.investable_capital)}, lợi nhuận kỳ vọng "
                    f"{_pct(scenario.expected_return_rate)} ({_money(scenario.expected_return_amount)}/năm), "
                    f"chi phí mô hình {_money(scenario.total_cost_amount)}, biến động "
                    f"{_pct(scenario.risk_metrics.annualized_volatility)}, VaR 95% "
                    f"{_money(scenario.risk_metrics.var_95_amount)}, CVaR 95% "
                    f"{_money(scenario.risk_metrics.cvar_95_amount)}, thanh khoản "
                    f"{scenario.risk_metrics.liquidity_score:.1f}/100."
                )
            )
            scenario_reasoning.append(
                explain_complexity_payload(
                    {
                        "operational_complexity_score": scenario.operational_complexity_score,
                        "complexity_breakdown": scenario.complexity_breakdown.model_dump(),
                    },
                    str(released.legal_operating_mode),
                )
            )
            scenario_reasoning.extend(
                (
                    f"{detail.product_name or str(detail.asset_class)}: "
                    f"{_money(detail.amount)} ({_pct(detail.weight)}), lợi nhuận kỳ vọng "
                    f"{_pct(detail.expected_return_rate)}, chi phí "
                    f"{_money(detail.transaction_cost_amount)}, thanh khoản "
                    f"{detail.liquidity_score:.1f}/100. {detail.allocation_reason} "
                    f"{detail.limiting_factor}"
                )
                for detail in scenario.allocation_explanations
            )
            if worst_stress:
                scenario_reasoning.append(
                    f"Kịch bản bất lợi {worst_stress.scenario_name}: "
                    f"{_money(worst_stress.estimated_change_amount)} "
                    f"({_pct(worst_stress.estimated_change_pct)}); {worst_stress.assumptions}"
                )
        reasoning = [
            (
                f"Đã phát hành {len(released.scenarios)} phương án sau Compliance Gate. "
                f"Chế độ {released.output_release_type}: "
                + (
                    "phương án đầu tiên là khuyến nghị, các phương án còn lại là lựa chọn thay thế; "
                    "tất cả chi tiết sản phẩm được phép hiển thị vì bằng chứng advisory đã xác minh."
                    if released.output_release_type == "ADVISORY_SELECTED"
                    else "chỉ hiển thị cấp nhóm tài sản, không biến so sánh thành lệnh mua."
                )
            ),
            *scenario_reasoning,
            (
                "Mọi số tiền, tỷ trọng, lợi nhuận kỳ vọng và chỉ số rủi ro ở trên được "
                "sao chép từ optimizer đã qua kiểm duyệt; AI không tính lại."
            ),
        ]
    return ExplanationPayload(
        reasoning=reasoning,
        source_reference=[
            released.data_snapshot,
            released.model_version,
            *[
                source
                for scenario in released.scenarios
                for source in scenario.source_summary
            ],
        ],
        warning=released.warnings,
        confidence=82 if released.scenarios else 60,
        generated_by="DETERMINISTIC_FALLBACK",
    )


def explain_released_output(released: ReleasedOutput) -> ExplanationPayload:
    """Explain only the released schema.

    The API path is optional for a resilient demo. No full optimizer output, hidden
    product allocation, tool, or calculator is exposed to the model.
    """

    compact_payload = {
        "output_release_type": released.output_release_type,
        "legal_operating_mode": released.legal_operating_mode,
        "data_snapshot": released.data_snapshot,
        "model_version": released.model_version,
        "scenarios": [
            {
                "name": scenario.name,
                "objective": scenario.objective_description,
                "expected_return_rate": scenario.expected_return_rate,
                "expected_return_amount": scenario.expected_return_amount,
                "total_cost_amount": scenario.total_cost_amount,
                "risk": {
                    "volatility": scenario.risk_metrics.annualized_volatility,
                    "var_95": scenario.risk_metrics.var_95_amount,
                    "cvar_95": scenario.risk_metrics.cvar_95_amount,
                    "liquidity": scenario.risk_metrics.liquidity_score,
                    "risk_ceiling": scenario.risk_metrics.risk_ceiling,
                },
                "allocations": [
                    {
                        "asset_class": str(item.asset_class),
                        "amount": item.amount,
                        "weight": item.weight,
                        "expected_return_amount": item.expected_return_amount,
                    }
                    for item in scenario.allocations
                ],
                "deposits": [
                    {
                        "bank": item.bank,
                        "tenor_months": item.tenor_months,
                        "amount": item.amount,
                        "annual_rate": item.annual_rate,
                        "term_interest_amount": item.term_interest_amount,
                    }
                    for item in scenario.deposit_implementation
                ],
                "operational_complexity_score": scenario.operational_complexity_score,
                "complexity_breakdown": scenario.complexity_breakdown.model_dump(),
                "complexity_config_version": scenario.complexity_config_version,
                "fragmentation_warning": scenario.fragmentation_warning,
                "trade_offs": scenario.trade_offs,
            }
            for scenario in released.scenarios
        ],
        "warnings": released.warnings[:5],
    }
    explanation, generated_by = generate_structured(
        ExplanationPayload,
        system_prompt=(
            "Bạn là Explanation Agent cho hệ thống giáo dục tài chính. "
            "Chỉ diễn giải JSON released_output được cung cấp. Không tính, "
            "suy ra, làm tròn, thay đổi hoặc bổ sung bất kỳ con số nào. "
            "Độ phức tạp chỉ được diễn giải khi có operational_complexity_score và "
            "complexity_breakdown; nếu thiếu phải báo thiếu dữ liệu, không tự ước lượng. "
            "Ở RESEARCH_EDUCATION chỉ mô tả COMPARE_ONLY, không dùng câu mệnh lệnh "
            "cá nhân hóa như 'bạn nên gộp'. Không cam kết lợi nhuận và không ra lệnh "
            "mua/bán. Viết tiếng Việt."
        ),
        user_content=json.dumps(compact_payload, ensure_ascii=False),
    )
    if explanation is None:
        return _fallback_explanation(released)
    deterministic = _fallback_explanation(released)
    explanation.reasoning = [
        *deterministic.reasoning,
        *explanation.reasoning,
    ]
    explanation.source_reference = list(
        dict.fromkeys(
            [
                *deterministic.source_reference,
                *explanation.source_reference,
            ]
        )
    )
    explanation.warning = list(
        dict.fromkeys([*deterministic.warning, *explanation.warning])
    )
    explanation.generated_by = generated_by
    return explanation
