from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from backend.app.db.market_data import latest_observations
from backend.app.models import AssetClass
from backend.app.services.deposit_comparison import compare_deposits
from backend.app.services.equity_research import get_equity_research
from backend.app.services.gold_research import get_gold_research


@dataclass(slots=True)
class InvestmentMemo:
    """Evidence-first explanation for one released Advisor product."""

    thesis: list[str] = field(default_factory=list)
    proof_chain: list[str] = field(default_factory=list)
    market_evidence: list[str] = field(default_factory=list)
    catalysts: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    implementation: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


def _money(value: int | float) -> str:
    return f"{round(value):,}".replace(",", ".") + " VND"


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%".replace(".", ",")


def _number(value: float, digits: int = 2) -> str:
    return (
        f"{value:,.{digits}f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def _tenor_months(product_id: str, product_name: str) -> int | None:
    match = re.search(r"(?:-|online-)(\d+)m(?:-|$)", product_id, re.I)
    if match:
        return int(match.group(1))
    match = re.search(r"\b(\d+)\s*tháng\b", product_name, re.I)
    return int(match.group(1)) if match else None


def _allocation_formula(allocation: Any) -> list[str]:
    expected = round(allocation.amount * allocation.expected_return_rate)
    facts = [
        (
            f"{_money(allocation.amount)} × {_pct(allocation.expected_return_rate)}/năm "
            f"≈ {_money(expected)}/năm; optimizer phát hành "
            f"{_money(allocation.expected_return_amount)}/năm sau quy tắc làm tròn."
        ),
        (
            f"Tỷ trọng {_pct(allocation.weight)}; chi phí mô hình "
            f"{_money(allocation.transaction_cost_amount)}; thanh khoản "
            f"{allocation.liquidity_score}/100."
        ),
    ]
    reference_price = getattr(allocation, "reference_price", None)
    units = getattr(allocation, "estimated_units", None)
    if reference_price and units is not None:
        facts.append(
            f"{units:,} đơn vị × {_money(reference_price)} ≈ "
            f"{_money(units * reference_price)} trước phần dư và chi phí."
            .replace(",", ".")
        )
    return facts


def _portfolio_evidence(allocation: Any, explanation: Any | None) -> tuple[list[str], list[str]]:
    thesis: list[str] = []
    proof: list[str] = _allocation_formula(allocation)
    if explanation is None:
        thesis.append(
            "Sản phẩm được optimizer chọn trong các ràng buộc lợi nhuận, rủi ro, "
            "thanh khoản, tập trung và độ phức tạp vận hành."
        )
        return thesis, proof
    thesis.extend([explanation.portfolio_role, explanation.allocation_reason])
    proof.extend(
        [
            f"Giới hạn đang chi phối: {explanation.limiting_factor}",
            explanation.expected_return_and_risk,
            explanation.cost_and_liquidity,
            f"Stress test bất lợi: {explanation.adverse_scenario}",
        ]
    )
    return thesis, proof


def _alternative_evidence(
    allocation: Any,
    scenario: Any,
) -> list[str]:
    decisions = [
        item
        for item in scenario.selection_decisions
        if item.asset_class == allocation.asset_class
        and item.product_id != allocation.product_id
    ]
    ranked = sorted(
        decisions,
        key=lambda item: (
            str(item.status) == "REJECTED",
            -(item.expected_return or -1),
            item.product_name or item.product_id,
        ),
    )
    alternatives: list[str] = []
    for item in ranked[:3]:
        metrics = []
        if item.expected_return is not None:
            metrics.append(f"lợi nhuận mô hình {_pct(item.expected_return)}")
        if item.volatility is not None:
            metrics.append(f"biến động {_pct(item.volatility)}")
        if item.liquidity_score is not None:
            metrics.append(f"thanh khoản {item.liquidity_score}/100")
        reason = " ".join(item.reasons[:1]) or "Không cải thiện nghiệm đã phát hành."
        alternatives.append(
            f"{item.product_name or item.product_id}: {', '.join(metrics)}. {reason}"
        )
    return alternatives


def _deposit_memo(allocation: Any, scenario: Any, memo: InvestmentMemo) -> None:
    detail = next(
        (
            item
            for item in scenario.deposit_implementation
            if item.product_id == allocation.product_id
        ),
        None,
    )
    tenor = _tenor_months(allocation.product_id, allocation.product_name)
    memo.thesis.append(
        "Luận điểm của tiền gửi là khóa một mức sinh lời danh nghĩa có thể tính trước "
        "cho phần vốn ưu tiên ổn định, không phải kỳ vọng tăng giá tài sản."
    )
    if detail:
        memo.market_evidence.extend(
            [
                (
                    f"{detail.bank}, kỳ hạn {detail.tenor_months or tenor or 'chưa xác nhận'} "
                    f"tháng, lãi suất tham chiếu {_pct(detail.annual_rate)}/năm."
                ),
                (
                    f"Với {_money(detail.amount)}, lãi cuối kỳ minh họa "
                    f"{_money(detail.term_interest_amount or 0)} và giá trị đáo hạn "
                    f"{_money(detail.maturity_amount or detail.amount)}."
                ),
                f"Phân khúc/tier: {detail.selected_segment or 'phổ thông theo bảng tham chiếu'}.",
            ]
        )
        memo.implementation.extend(detail.conditions)
    memo.catalysts.extend(
        [
            "Khoản gửi trở nên tương đối hấp dẫn hơn nếu lãi suất thị trường giảm sau khi đã khóa kỳ hạn.",
            "Dòng tiền và thời điểm đáo hạn khớp mục tiêu giúp tránh phải bán tài sản biến động.",
        ]
    )
    memo.risks.extend(
        [
            "Rút trước hạn có thể khiến toàn bộ hoặc một phần khoản gửi chỉ hưởng lãi không kỳ hạn.",
            "Lãi suất thị trường tăng sau khi mở sổ tạo chi phí cơ hội; tái tục có thể ở mức thấp hơn.",
            "Tập trung quá nhiều tại một ngân hàng hoặc một ngày đáo hạn làm giảm khả năng ứng phó dòng tiền.",
        ]
    )
    if tenor:
        try:
            comparisons = compare_deposits(
                amount=allocation.amount,
                tenor_months=tenor,
                customer_segment="retail",
            )["comparisons"]
            comparisons_as_text = [
                (
                    f"{row['provider']} {_pct(row['annual_rate'])}/năm; lãi kỳ hạn "
                    f"{_money(row['projected_interest'])}; "
                    f"{'đủ điều kiện' if row['eligible'] else 'chưa đủ điều kiện'}."
                )
                for row in comparisons[:3]
            ]
            if comparisons_as_text:
                memo.alternatives = comparisons_as_text
        except Exception as exc:
            memo.limitations.append(
                f"Chưa dựng được bảng so sánh cùng kỳ hạn: {type(exc).__name__}."
            )


def _gold_memo(allocation: Any, memo: InvestmentMemo) -> None:
    research = get_gold_research(
        product_id=allocation.product_id,
        product_name=allocation.product_name,
        reference_price=getattr(allocation, "reference_price", None),
        amount=allocation.amount,
        estimated_units=getattr(allocation, "estimated_units", None),
        transaction_cost_amount=allocation.transaction_cost_amount,
    )
    memo.thesis.extend(
        [
            "Vàng được dùng như tài sản đa dạng hóa và phòng vệ sức mua/cú sốc, "
            "không phải tài sản tạo dòng tiền định kỳ.",
            *research.product_facts,
        ]
    )
    memo.market_evidence.extend(
        research.local_price_facts
        + research.global_price_facts
        + research.technical_facts
        + research.macro_facts
    )
    memo.catalysts.extend(
        [
            "Lợi suất thực Mỹ giảm, USD suy yếu hoặc rủi ro địa chính trị tăng thường hỗ trợ nhu cầu vàng.",
            "Premium vàng vật chất trong nước thu hẹp có thể cải thiện giá thực hiện so với giá thế giới quy đổi.",
        ]
    )
    memo.risks.extend(
        [
            "Lợi suất thực và USD tăng có thể gây áp lực lên vàng thế giới.",
            "Chênh lệch mua–bán và premium nội địa có thể làm nhà đầu tư lỗ dù chart quốc tế ít thay đổi.",
            "Vàng không tạo dòng tiền; tỷ trọng cao làm giảm lợi nhuận kỳ vọng của danh mục trong giai đoạn tài sản rủi ro tăng.",
        ]
    )
    memo.alternatives.extend(
        [
            "Vàng nhẫn 9999: đơn vị nhỏ, linh hoạt hơn nhưng cần so sánh spread và thương hiệu.",
            "Vàng miếng SJC 1 lượng: vốn tối thiểu lớn hơn và premium nội địa có thể khác đáng kể.",
            "Giữ tiền mặt/tiền gửi: ít biến động hơn nhưng không có vai trò phòng vệ giá vàng.",
        ]
    )
    memo.sources.extend(research.sources)
    memo.limitations.extend(research.limitations)


def _bond_fund_memo(allocation: Any, memo: InvestmentMemo) -> None:
    observation = next(
        (
            row
            for row in latest_observations()
            if row["source_id"] == "VCBF_NAV" and row["series_key"] == "FIF_NAV"
        ),
        None,
    )
    memo.thesis.append(
        "Quỹ trái phiếu được dùng để tìm mức sinh lời cao hơn tiền mặt/tiền gửi trong "
        "khi biến động dự kiến thấp hơn cổ phiếu, nhưng NAV không được bảo đảm."
    )
    if observation:
        payload = observation.get("payload", {})
        memo.market_evidence.append(
            f"NAV công bố gần nhất {_money(float(observation['value']))}/chứng chỉ quỹ, "
            f"quan sát {observation['observed_at']}."
        )
        if payload.get("return_1y") is not None:
            memo.market_evidence.append(
                f"Hiệu suất một năm do nguồn công bố: {_pct(float(payload['return_1y']))}."
            )
        if payload.get("return_3y_annualized") is not None:
            memo.market_evidence.append(
                "Hiệu suất ba năm năm hóa do nguồn công bố: "
                f"{_pct(float(payload['return_3y_annualized']))}."
            )
    else:
        memo.market_evidence.append(
            "Chưa có NAV VCBF-FIF trong registry của phiên này; hệ thống không tự điền "
            "một mức NAV giả và yêu cầu đồng bộ nguồn chính thức trước khi thực hiện."
        )
        memo.limitations.append("Registry chưa có quan sát NAV VCBF-FIF để đối chiếu.")
    memo.catalysts.extend(
        [
            "Lãi suất thị trường giảm có thể hỗ trợ giá trái phiếu và NAV, tùy duration danh mục.",
            "Chất lượng tín dụng ổn định và dòng tiền coupon đều hỗ trợ hiệu suất quỹ.",
        ]
    )
    memo.risks.extend(
        [
            "Lãi suất tăng làm giá trái phiếu giảm; NAV quỹ có thể âm trong một số giai đoạn.",
            "Rủi ro tín dụng, thanh khoản tài sản cơ sở, phí quản lý và thời gian xử lý lệnh làm kết quả khác tiền gửi.",
            "Hiệu suất lịch sử và expected return của optimizer không phải cam kết lợi nhuận tương lai.",
        ]
    )
    memo.alternatives.extend(
        [
            "Tiền gửi cùng thời hạn: lãi dễ tính trước hơn nhưng rút trước hạn có thể mất lãi.",
            "Trái phiếu Chính phủ/quỹ duration ngắn: rủi ro tín dụng thấp hơn nhưng lợi suất có thể thấp hơn.",
            "Tiền mặt: thanh khoản tức thời nhưng chịu chi phí cơ hội và lạm phát.",
        ]
    )


def _cash_memo(memo: InvestmentMemo) -> None:
    memo.thesis.append(
        "Tiền mặt được giữ để đáp ứng quỹ dự phòng, nghĩa vụ gần hạn và tránh bán tài "
        "sản khác trong thời điểm bất lợi; đây là một lựa chọn quản trị rủi ro."
    )
    memo.catalysts.append(
        "Giá trị của vùng đệm tiền mặt tăng khi nhu cầu rút vốn gần, thị trường biến động mạnh hoặc cơ hội đầu tư cần giải ngân nhanh."
    )
    memo.risks.extend(
        [
            "Lạm phát bào mòn sức mua và lợi nhuận kỳ vọng danh mục.",
            "Giữ vượt nhu cầu thanh khoản tạo chi phí cơ hội so với tiền gửi hoặc tài sản sinh lời.",
        ]
    )
    memo.alternatives.extend(
        [
            "Tiền gửi không kỳ hạn/kỳ hạn rất ngắn cho phần vốn chưa cần ngay.",
            "Quỹ trái phiếu duration ngắn nếu chấp nhận NAV biến động và thời gian xử lý lệnh.",
        ]
    )


def _equity_memo(allocation: Any, memo: InvestmentMemo, *, is_etf: bool) -> None:
    ticker_match = re.search(
        r"(?:vn30-)?(?:equity|etf)-([a-z0-9]+)-(?:vnstock|mock)",
        allocation.product_id,
        re.I,
    )
    ticker = ticker_match.group(1).upper() if ticker_match else None
    if is_etf:
        memo.thesis.append(
            "ETF được chọn để tiếp cận một rổ cổ phiếu và giảm rủi ro riêng lẻ so với "
            "một mã đơn, nhưng vẫn chịu rủi ro thị trường cổ phiếu."
        )
        memo.catalysts.extend(
            [
                "Độ rộng thị trường cải thiện và lợi nhuận doanh nghiệp trong rổ tăng hỗ trợ NAV.",
                "Thanh khoản/quy mô quỹ tăng có thể giảm tracking difference và spread.",
            ]
        )
        memo.risks.extend(
            [
                "Rủi ro giảm giá toàn thị trường, tracking error, spread và chênh lệch giá thị trường so với NAV.",
                "Cơ cấu chỉ số tập trung vào một số ngành lớn có thể làm mức đa dạng hóa thấp hơn kỳ vọng.",
            ]
        )
        memo.alternatives.extend(
            [
                "Cổ phiếu đơn lẻ: luận điểm riêng rõ hơn nhưng rủi ro doanh nghiệp cao hơn.",
                "Quỹ cổ phiếu chủ động: khác về phí, phong cách và rủi ro lệch chuẩn chỉ số.",
            ]
        )
        return
    if not ticker:
        memo.limitations.append("Không trích xuất được mã cổ phiếu từ product_id.")
        return
    research = get_equity_research(
        ticker,
        getattr(allocation, "reference_price", None),
    )
    memo.thesis.extend(
        research.investment_thesis
        or [
            "Cổ phiếu được chọn ở cấp danh mục, nhưng chưa có báo cáo phân tích doanh "
            "nghiệp đủ nguồn để biến kết quả optimizer thành luận điểm cơ bản độc lập."
        ]
    )
    memo.market_evidence.extend(
        research.company_facts
        + research.analyst_views
        + research.earnings_facts
        + research.quality_facts
        + research.valuation_facts
        + research.fundamental_facts
        + research.price_facts
        + research.technical_facts
        + research.news_facts
        + research.macro_facts
    )
    memo.catalysts.extend(research.catalysts)
    memo.risks.extend(
        research.risk_facts
        or [
            "Lợi nhuận doanh nghiệp thấp hơn kỳ vọng, định giá co lại hoặc xu hướng giá "
            "xấu đi có thể làm luận điểm mất hiệu lực.",
            "Rủi ro riêng doanh nghiệp và thanh khoản của một mã không được loại bỏ chỉ "
            "vì mã thuộc VN30.",
        ]
    )
    if not memo.catalysts:
        memo.catalysts.append(
            "Kết quả kinh doanh, định giá hoặc thông tin doanh nghiệp cải thiện có kiểm "
            "chứng là điều kiện cần để nâng đánh giá; biến động giá đơn thuần không đủ."
        )
    memo.sources.extend(research.sources)
    memo.limitations.extend(research.limitations)


def build_investment_memo(
    *,
    allocation: Any,
    explanation: Any | None,
    scenario: Any,
) -> InvestmentMemo:
    memo = InvestmentMemo()
    memo.thesis, memo.proof_chain = _portfolio_evidence(allocation, explanation)
    memo.implementation.extend(
        [
            allocation.execution_instruction,
            (
                f"Tính lại giá/lãi suất/NAV tại thời điểm thực hiện; dữ liệu hiện tại "
                f"quan sát {allocation.data_timestamp.isoformat()}."
            ),
        ]
    )
    if getattr(allocation, "selected_segment", None):
        memo.implementation.append(
            f"Phân khúc hoặc tier được chọn: {allocation.selected_segment}."
        )
    memo.sources.append(allocation.source_reference)
    if explanation:
        memo.implementation.extend(explanation.execution_conditions)
        memo.limitations.extend(explanation.result_sensitive_assumptions)
    memo.alternatives.extend(_alternative_evidence(allocation, scenario))

    asset_class = allocation.asset_class
    if asset_class == AssetClass.DEPOSIT:
        _deposit_memo(allocation, scenario, memo)
    elif asset_class == AssetClass.GOLD:
        _gold_memo(allocation, memo)
    elif asset_class == AssetClass.BOND_FUND:
        _bond_fund_memo(allocation, memo)
    elif asset_class == AssetClass.CASH:
        _cash_memo(memo)
    elif asset_class == AssetClass.EQUITY:
        _equity_memo(allocation, memo, is_etf=False)
    elif asset_class == AssetClass.ETF:
        _equity_memo(allocation, memo, is_etf=True)
    else:
        memo.thesis.append(
            "Sản phẩm chỉ được giữ khi vai trò danh mục và đóng góp định lượng bù được "
            "chi phí, thanh khoản và rủi ro trong giới hạn hồ sơ."
        )
        memo.risks.append(
            "Chưa có bộ phân tích chuyên biệt cho loại tài sản này; cần kiểm tra tài "
            "liệu sản phẩm và giá thực hiện trước khi ra quyết định."
        )

    for field_name in (
        "thesis",
        "proof_chain",
        "market_evidence",
        "catalysts",
        "risks",
        "alternatives",
        "implementation",
        "sources",
        "limitations",
    ):
        values = getattr(memo, field_name)
        setattr(memo, field_name, list(dict.fromkeys(item for item in values if item)))
    return memo
