from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models import (
    ChatAnswerSection,
    ChatResponse,
    PlanningRequest,
    ReleasedOutput,
    ReleasedScenario,
    UserFinancialProfile,
)
from backend.app.services.llm import generate_structured
from backend.app.services.gold_research import get_gold_research
from backend.app.services.deposit_comparison import (
    compare_deposits,
    extract_deposit_query,
)
from backend.app.services.equity_research import get_equity_research
from backend.app.services.investment_memo import build_investment_memo
from backend.app.services.market_data import market_data_summary


class _OpenAIChatNarrative(BaseModel):
    """Qualitative wording only; deterministic code owns every displayed number."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=650)
    sections: list[ChatAnswerSection] = Field(default_factory=list, max_length=1)
    suggested_questions: list[str] = Field(default_factory=list, max_length=2)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    without_marks = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    return without_marks.replace("đ", "d")


def _extract_amount(message: str) -> int | None:
    normalized = _normalize(message).replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(ty|trieu|m|k|nghin)?", normalized)
    if not match:
        return None
    value = float(match.group(1))
    suffix = match.group(2)
    multiplier = {
        "ty": 1_000_000_000,
        "trieu": 1_000_000,
        "m": 1_000_000,
        "k": 1_000,
        "nghin": 1_000,
        None: 1,
    }[suffix]
    return round(value * multiplier)


def _money(value: int | float) -> str:
    return f"{round(value):,}".replace(",", ".") + " VND"


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%".replace(".", ",")


def _bounded_text(
    parts: list[str],
    fallback: str,
    *,
    limit: int = 1_450,
) -> str:
    text = " ".join(part.strip() for part in parts if part and part.strip()) or fallback
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0] + "…"


def _source_question(message: str) -> bool:
    normalized = _normalize(message)
    return any(
        token in normalized
        for token in [
            "nguon du lieu",
            "du lieu nay",
            "lay tu dau",
            "cap nhat luc",
            "cap nhat khi",
            "du lieu that",
            "ket noi du lieu",
            "snapshot",
        ]
    )


def _deposit_question(message: str) -> bool:
    normalized = _normalize(message)
    return any(
        token in normalized
        for token in [
            "lai suat",
            "tien gui",
            "gui tiet kiem",
            "mbbank",
            "techcombank",
            "vpbank",
        ]
    )


def _portfolio_deposit_question(message: str) -> bool:
    normalized = _normalize(message)
    return any(
        token in normalized
        for token in [
            "ngan hang nao",
            "gui ngan hang",
            "ky han nao",
            "tien gui nao",
            "so von gui",
            "chia tien gui",
            "gui bao nhieu",
        ]
    )


def _portfolio_deposit_answer(
    released: ReleasedOutput,
    active_scenario_id: str | None,
) -> tuple[str, list[ChatAnswerSection], list[str]]:
    selected = _scenario(released, active_scenario_id)
    if selected is None or not selected.deposit_implementation:
        return (
            "Phương án này không có khoản tiền gửi được optimizer phân bổ.",
            [
                ChatAnswerSection(
                    title="Kết quả kiểm tra",
                    body="Không có ngân hàng, kỳ hạn hoặc số vốn tiền gửi cần triển khai trong phương án đang xem.",
                )
            ],
            ["Giải thích phân bổ tài sản", "So sánh cả 3 phương án"],
        )
    total_deposit = sum(item.amount for item in selected.deposit_implementation)
    deposit_summary = ", ".join(
        (
            f"{item.bank} {item.tenor_months} tháng {_money(item.amount)}"
            if item.tenor_months is not None
            else f"{item.bank} {_money(item.amount)}"
        )
        for item in selected.deposit_implementation
    )
    sections = []
    for item in selected.deposit_implementation:
        tenor = (
            f"{item.tenor_months} tháng"
            if item.tenor_months is not None
            else "kỳ hạn cần xác nhận"
        )
        term_interest = (
            _money(item.term_interest_amount)
            if item.term_interest_amount is not None
            else "cần xác nhận"
        )
        maturity = (
            _money(item.maturity_amount)
            if item.maturity_amount is not None
            else "cần xác nhận"
        )
        sections.append(
            ChatAnswerSection(
                title=f"{item.bank} · {tenor} · {_money(item.amount)}",
                body=(
                    f"Sản phẩm: {item.product_name}. Lãi suất tham chiếu "
                    f"{_pct(item.annual_rate)}/năm; lãi cuối kỳ minh họa {term_interest}; "
                    f"đáo hạn {maturity}; chiếm {_pct(item.weight)} danh mục. "
                    f"Thanh khoản {item.liquidity_score}/100. {item.why_selected} "
                    f"Điều kiện: {' '.join(item.conditions)} "
                    f"Dữ liệu cập nhật {_source_observed_text(item.data_timestamp.isoformat())}."
                ),
            )
        )
    return (
        (
            f"Với phương án “{selected.name}”, phần tiền gửi được chia như sau: "
            f"{deposit_summary}. Tổng cộng {_money(total_deposit)}. "
            "Bạn có thể mở từng mục bên dưới để xem lãi suất và điều kiện."
        ),
        sections,
        [
            "Vì sao chọn các kỳ hạn này?",
            "Nếu cần rút trước hạn thì phương án nào ít tốn nhất?",
            "So sánh lãi suất 3 ngân hàng",
        ],
    )


def _deposit_answer(
    profile: UserFinancialProfile,
    message: str,
) -> tuple[str, list[ChatAnswerSection], list[str]]:
    investable = max(
        1_000_000,
        round(
            profile.total_assets
            - profile.emergency_reserve
            - profile.near_term_liabilities
        ),
    )
    default_segment = (
        profile.customer_segments[0]
        if profile.customer_segments
        else "retail"
    )
    amount, tenor, segment = extract_deposit_query(
        message,
        default_amount=investable,
        default_segment=default_segment,
    )
    result = compare_deposits(
        amount=amount,
        tenor_months=tenor,
        customer_segment=segment,
    )
    sections = [
        ChatAnswerSection(
            title=(
                f"{row['provider']} · {row['annual_rate'] * 100:.2f}%/năm"
                + (" · Đủ điều kiện" if row["eligible"] else " · Chưa đủ điều kiện")
            ),
            body=(
                f"Lãi cuối kỳ minh họa {_money(row['projected_interest'])}; "
                f"giá trị đáo hạn {_money(row['maturity_amount'])}. "
                + " ".join(row["eligibility_reasons"])
            ),
        )
        for row in result["comparisons"]
    ]
    sections.append(
        ChatAnswerSection(
            title="Cách đọc kết quả",
            body=(
                result["calculation_note"]
                + " Lãi suất có thể thay đổi; cần xác nhận lại trên kênh chính thức "
                "của từng ngân hàng trước khi mở sổ."
            ),
        )
    )
    return (
        result["guidance"],
        sections,
        [
            f"So sánh 100 triệu kỳ hạn {tenor} tháng",
            "So sánh khách hàng Private với 3 tỷ",
            "Dữ liệu lãi suất cập nhật lúc nào?",
        ],
    )


def _source_observed_text(value: str | None) -> str:
    if not value:
        return "chưa có dữ liệu"
    observed = datetime.fromisoformat(value).astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
    return observed.strftime("%H:%M %d/%m/%Y")


def _data_source_answer() -> tuple[str, list[ChatAnswerSection], list[str]]:
    summary = market_data_summary()
    connected = [
        source
        for source in summary["sources"]
        if source["operational_status"] == "CONNECTED"
    ]
    unavailable = [
        source
        for source in summary["sources"]
        if source["operational_status"] != "CONNECTED"
    ]
    connected_text = "; ".join(
        (
            f"{source['display_name']} — quan sát "
            f"{_source_observed_text(source.get('observed_at'))}"
        )
        for source in connected
    ) or "Chưa có nguồn chính thức đang hoạt động; hệ thống dùng fallback có gắn cờ."
    unavailable_text = "; ".join(
        f"{source['display_name']}: {source.get('last_error') or source['operational_status']}"
        for source in unavailable
    ) or "Không có nguồn nào đang thiếu."
    return (
        (
            f"Kết quả đang dùng snapshot {summary['snapshot_id']}. "
            f"{summary['connected_sources']}/{summary['total_sources']} nguồn đã kết nối. "
            "Đây là dữ liệu chính thức có độ trễ, không phải giá giao dịch thời gian thực."
        ),
        [
            ChatAnswerSection(
                title="Nguồn và thời điểm quan sát",
                body=connected_text,
            ),
            ChatAnswerSection(
                title="Phạm vi chưa được kết nối",
                body=(
                    unavailable_text
                    + " Các tham số lợi nhuận kỳ vọng, biến động, VaR và stress test "
                    "vẫn là giả định mô hình, không phải dữ liệu thị trường quan sát."
                ),
            ),
        ],
        [
            "Mở bảng nguồn dữ liệu ở đâu?",
            "Giải thích phân bổ tài sản",
            "Rủi ro lớn nhất là gì?",
        ],
    )


def _scenario(
    released: ReleasedOutput,
    active_scenario_id: str | None,
) -> ReleasedScenario | None:
    if not released.scenarios:
        return None
    if active_scenario_id:
        for item in released.scenarios:
            if item.scenario_id == active_scenario_id:
                return item
    return released.scenarios[0]


def resolve_scenario_id(
    released: ReleasedOutput,
    message: str,
    active_scenario_id: str | None,
) -> str | None:
    """Resolve natural references without letting the LLM choose a scenario."""

    if not released.scenarios:
        return None
    normalized = _normalize(message)

    for scenario in released.scenarios:
        normalized_name = _normalize(scenario.name)
        if normalized_name and normalized_name in normalized:
            return scenario.scenario_id

    style_aliases = {
        "CAPITAL_PRESERVATION": [
            "dem an toan",
            "bao toan von",
            "phuong an khuyen nghi",
        ],
        "BALANCED": ["can bang"],
        "GROWTH": ["tang truong"],
    }
    for scenario in released.scenarios:
        if any(
            alias in normalized
            for alias in style_aliases.get(str(scenario.style), [])
        ):
            return scenario.scenario_id

    ordinal_patterns = [
        r"\bphuong an\s*(?:so|thu)?\s*(?:1|01|mot|nhat|dau tien)\b",
        r"\bphuong an\s*(?:so|thu)?\s*(?:2|02|hai)\b",
        r"\bphuong an\s*(?:so|thu)?\s*(?:3|03|ba)\b",
    ]
    for index, pattern in enumerate(ordinal_patterns):
        if index < len(released.scenarios) and re.search(pattern, normalized):
            return released.scenarios[index].scenario_id

    if active_scenario_id and any(
        item.scenario_id == active_scenario_id for item in released.scenarios
    ):
        return active_scenario_id
    return released.scenarios[0].scenario_id


def _gold_question(message: str) -> bool:
    normalized = _normalize(message)
    return any(
        token in normalized
        for token in [
            "vang",
            "sjc",
            "xau",
            "comex",
            "gia the gioi",
            "vang mieng",
            "vang nhan",
        ]
    )


def _gold_answer(
    released: ReleasedOutput,
    active_scenario_id: str | None,
) -> tuple[str, list[ChatAnswerSection], list[str]]:
    selected = _scenario(released, active_scenario_id)
    if selected is None:
        return (
            "Chưa có phương án đã kiểm duyệt để đối chiếu phân bổ vàng.",
            [],
            ["Hãy chạy lại phân tích hồ sơ"],
        )

    gold_allocations = [
        item for item in selected.allocations if item.asset_class.value == "GOLD"
    ]
    product_allocation = next(
        (item for item in gold_allocations if getattr(item, "product_id", None)),
        None,
    )
    gold_decisions = [
        item for item in released.selection_decisions if item.asset_class.value == "GOLD"
    ]
    preferred_decision = next(
        (
            item
            for item in gold_decisions
            if "ring" in item.product_id and str(item.status) == "SELECTED_INTERNAL"
        ),
        next((item for item in gold_decisions if "ring" in item.product_id), None),
    )

    product_id = (
        product_allocation.product_id
        if product_allocation is not None
        else preferred_decision.product_id
        if preferred_decision is not None
        else "gold-ring-pnj-delayed"
    )
    product_name = (
        product_allocation.product_name
        if product_allocation is not None
        else preferred_decision.product_name
        if preferred_decision is not None and preferred_decision.product_name
        else "Vàng nhẫn tròn 9999"
    )
    research = get_gold_research(
        product_id=product_id,
        product_name=product_name,
        reference_price=getattr(product_allocation, "reference_price", None),
        amount=getattr(product_allocation, "amount", None),
        estimated_units=getattr(product_allocation, "estimated_units", None),
        transaction_cost_amount=getattr(
            product_allocation, "transaction_cost_amount", None
        ),
    )

    if product_allocation is not None:
        answer = (
            f"Phương án “{selected.name}” phân bổ {_money(product_allocation.amount)} "
            f"({_pct(product_allocation.weight)}) vào {product_allocation.product_name}. "
            "Tỷ trọng này gồm sàn đa dạng hóa, làm tròn theo đơn vị vàng vật chất và kiểm tra rủi ro danh mục."
        )
        allocation_reason = next(
            (
                " ".join(item.reasons)
                for item in gold_decisions
                if item.product_id == product_allocation.product_id
            ),
            "Vàng được giữ như một tài sản đa dạng hóa; không phải vì hệ thống dự báo chắc chắn giá sẽ tăng.",
        )
    elif gold_allocations:
        aggregate = gold_allocations[0]
        answer = (
            f"Phương án “{selected.name}” có {_money(aggregate.amount)} "
            f"({_pct(aggregate.weight)}) ở nhóm vàng. Chế độ hiện tại chỉ phát hành cấp nhóm tài sản."
        )
        allocation_reason = (
            "Chi tiết vàng chỉ hay vàng miếng chỉ được phát hành trong Advisor; số cấp nhóm vẫn đến trực tiếp từ optimizer."
        )
    else:
        answer = (
            f"Phương án “{selected.name}” hiện không có vàng. Đây không phải lỗi mất dữ liệu: "
            "sản phẩm có thể bị loại vì đơn vị vật chất tối thiểu vượt trần tỷ trọng hoặc vì phương án cũ được tạo trước khi có sàn đa dạng hóa vàng."
        )
        allocation_reason = " ".join(
            reason
            for decision in gold_decisions
            for reason in decision.reasons
        ) or "Không có quyết định eligibility về vàng trong kết quả này."

    sections = [
        ChatAnswerSection(
            title="Vì sao có hoặc không có tỷ trọng vàng",
            body=allocation_reason,
        ),
        ChatAnswerSection(
            title="Sản phẩm vật chất và quy tắc số lượng",
            body=" ".join(research.product_facts),
        ),
        ChatAnswerSection(
            title="Giá SJC/vàng nhẫn trong nước",
            body=" ".join(research.local_price_facts) or "Chưa lấy được giá vàng vật chất chậm tại thời điểm trả lời.",
        ),
        ChatAnswerSection(
            title="Chart vàng thế giới",
            body=" ".join(research.global_price_facts) or "Chưa lấy được chuỗi COMEX cuối ngày.",
        ),
        ChatAnswerSection(
            title="Phân tích kỹ thuật vàng thế giới",
            body=" ".join(research.technical_facts) or "Chưa đủ dữ liệu để tính MA20, MA50, RSI14, biến động và drawdown.",
        ),
        ChatAnswerSection(
            title="Vĩ mô tác động đến vàng",
            body=" ".join(research.macro_facts) or "Chưa có quan sát vĩ mô đủ dùng trong registry.",
        ),
        ChatAnswerSection(
            title="Nguồn và giới hạn",
            body=" ".join(research.sources + research.limitations),
        ),
    ]
    return (
        answer,
        sections,
        [
            "Vàng miếng SJC khác vàng nhẫn ở chi phí nào?",
            "Nếu giá vàng giảm 10% thì danh mục ảnh hưởng bao nhiêu?",
            "So sánh premium SJC với giá vàng thế giới",
        ],
    )


def _product_question(message: str) -> bool:
    normalized = _normalize(message)
    return any(
        token in normalized
        for token in [
            "co phieu",
            "acb",
            "ma fpt",
            "fpt",
            "etf",
            "quy trai phieu",
            "vcbf",
            "tien mat",
            "vang",
            "sjc",
            "vang nhan",
            "tien gui",
            "mbbank",
            "techcombank",
            "vpbank",
            "tai sao mua",
            "vi sao mua",
            "bao nhieu co",
            "bao nhieu chung chi",
            "dau tu vao day",
            "vi sao chon ma",
            "tai sao chon ma",
            "vi sao chon cong ty",
            "tai sao chon cong ty",
            "tinh hinh cong ty",
            "phan tich cong ty",
            "phan tich co ban",
            "phan tich ky thuat",
            "tin tuc",
            "gia ca",
            "dinh gia",
        ]
    )


def _investment_memo_question(message: str) -> bool:
    normalized = _normalize(message)
    return any(
        token in normalized
        for token in [
            "tai sao",
            "vi sao",
            "luan diem",
            "investment",
            "chung minh",
            "dan chung",
            "phan tich chi tiet",
            "co nen",
            "rui ro cua",
            "chat xuc tac",
            "mat hieu luc",
        ]
    )


def _allocation_ticker(allocation: Any) -> str | None:
    product_id = str(getattr(allocation, "product_id", ""))
    match = re.search(r"(?:vn30-)?(?:equity|etf)-([a-z0-9]+)-(?:vnstock|mock)", product_id, re.I)
    if match:
        return match.group(1).upper()
    asset_class = getattr(getattr(allocation, "asset_class", None), "value", None)
    if asset_class not in {"EQUITY", "ETF"}:
        return None
    product_name = str(getattr(allocation, "product_name", ""))
    match = re.search(r"\b([A-Z]{3,5})\b", product_name)
    return match.group(1) if match else None


def _requested_product(scenario: ReleasedScenario, message: str):
    normalized = _normalize(message)
    product_allocations = [
        item for item in scenario.allocations if getattr(item, "product_id", None)
    ]
    for allocation in product_allocations:
        product_name = _normalize(allocation.product_name)
        if product_name and product_name in normalized:
            return allocation
        ticker = _allocation_ticker(allocation)
        if ticker and re.search(rf"\b{re.escape(ticker.lower())}\b", normalized):
            return allocation

    provider_matches = [
        item
        for item in product_allocations
        if _normalize(str(getattr(item, "provider", "")))
        and _normalize(str(getattr(item, "provider", ""))) in normalized
    ]
    tenor_match = re.search(r"\b(\d+)\s*thang\b", normalized)
    if tenor_match and provider_matches:
        tenor = int(tenor_match.group(1))
        tenor_specific = [
            item
            for item in provider_matches
            if re.search(
                rf"(?:-|online-){tenor}m(?:-|$)|\b{tenor}\s*thang\b",
                f"{item.product_id} {_normalize(item.product_name)}",
                re.I,
            )
        ]
        if len(tenor_specific) == 1:
            return tenor_specific[0]
    if len(provider_matches) == 1:
        return provider_matches[0]

    asset_tokens = {
        "CASH": ["tien mat", "tai khoan thanh toan"],
        "DEPOSIT": ["tien gui", "gui tiet kiem"],
        "BOND_FUND": ["quy trai phieu", "vcbf-fif", "fif"],
        "ETF": ["etf", "quy chi so"],
        "GOLD": ["vang nhan", "vang mieng", "sjc", "vang"],
    }
    for asset_class, tokens in asset_tokens.items():
        if not any(token in normalized for token in tokens):
            continue
        matches = [
            item
            for item in product_allocations
            if item.asset_class.value == asset_class
        ]
        if len(matches) == 1:
            return matches[0]
        if matches and "vang nhan" in normalized:
            ring = [item for item in matches if "ring" in item.product_id]
            if len(ring) == 1:
                return ring[0]
        if matches and ("vang mieng" in normalized or "sjc" in normalized):
            bars = [item for item in matches if "sjc" in item.product_id]
            if len(bars) == 1:
                return bars[0]
    return None


def _product_answer(
    released: ReleasedOutput,
    message: str,
    active_scenario_id: str | None,
) -> tuple[str, list[ChatAnswerSection], list[str]]:
    selected = _scenario(released, active_scenario_id)
    if selected is None:
        return (
            "Không có phương án đã kiểm duyệt để đối chiếu câu hỏi về sản phẩm.",
            [],
            ["Hãy chạy lại phân tích hồ sơ"],
        )

    if selected.allocation_granularity != "PRODUCT":
        equity = next(
            (
                item
                for item in selected.allocations
                if item.asset_class.value == "EQUITY"
            ),
            None,
        )
        equity_text = (
            f"Phương án chỉ phát hành {_money(equity.amount)} "
            f"({_pct(equity.weight)}) ở cấp nhóm cổ phiếu."
            if equity
            else "Phương án này không phát hành tỷ trọng cho nhóm cổ phiếu."
        )
        return (
            (
                f"Tôi chưa thể khẳng định phương án “{selected.name}” đầu tư vào FPT. "
                "Kết quả hiện tại là Research/Compare-only và chỉ được phát hành ở cấp "
                "nhóm tài sản, không có quyết định chọn mã hay số lượng cổ phiếu."
            ),
            [
                ChatAnswerSection(
                    title="Điều dữ liệu thực sự xác nhận",
                    body=equity_text,
                ),
                ChatAnswerSection(
                    title="Muốn có câu trả lời cấp mã",
                    body=(
                        "Cần phương án Advisor đã được cấp quyền, dữ liệu giá tham chiếu "
                        "còn hiệu lực và kết quả product-level đã qua Compliance Gate. "
                        "Hệ thống sẽ không suy ngược FPT từ tỷ trọng nhóm cổ phiếu."
                    ),
                ),
            ],
            [
                "Nhóm cổ phiếu chiếm bao nhiêu trong phương án này?",
                "Nguồn dữ liệu cổ phiếu cập nhật lúc nào?",
            ],
        )

    allocation = _requested_product(selected, message)
    if allocation is None:
        named_products = ", ".join(
            item.product_name
            for item in selected.allocations
            if getattr(item, "product_name", None)
            and item.asset_class.value in {"EQUITY", "ETF"}
        )
        requested_ticker = "ACB" if re.search(r"\bacb\b", _normalize(message)) else None
        if requested_ticker:
            research = get_equity_research(requested_ticker)
            return (
                (
                    f"{requested_ticker} không nằm trong các khoản phân bổ đã phát hành của phương án "
                    f"“{selected.name}”, nên tôi không gọi đây là một quyết định mua. Tuy vậy, dưới đây "
                    "là hồ sơ nghiên cứu có nguồn để bạn hiểu trường hợp đầu tư và các điều kiện bác bỏ."
                ),
                [
                    ChatAnswerSection(
                        title=f"Luận điểm đầu tư độc lập cho {requested_ticker}",
                        body=" ".join(research.investment_thesis),
                    ),
                    ChatAnswerSection(
                        title="Kết quả kinh doanh và chất lượng tài sản",
                        body=" ".join(research.earnings_facts + research.quality_facts),
                    ),
                    ChatAnswerSection(
                        title="Định giá và quan điểm của các tổ chức phân tích",
                        body=" ".join(research.valuation_facts + research.analyst_views),
                    ),
                    ChatAnswerSection(
                        title="Giá và phân tích kỹ thuật hiện tại",
                        body=(
                            " ".join(research.price_facts + research.technical_facts)
                            or "Chưa lấy được OHLCV mới để đánh giá xu hướng và vùng giá."
                        ),
                    ),
                    ChatAnswerSection(
                        title="Chất xúc tác, rủi ro và điều kiện bác bỏ",
                        body=" ".join(research.catalysts + research.risk_facts),
                    ),
                    ChatAnswerSection(
                        title="Nguồn và ngày công bố",
                        body=" | ".join(research.sources),
                    ),
                    ChatAnswerSection(
                        title="Đối chiếu với danh mục hiện tại",
                        body=(
                            f"Sản phẩm cổ phiếu/ETF đang thực sự được chọn: "
                            f"{named_products or 'không có'}. Muốn đưa ACB vào, hệ thống phải chạy lại "
                            "optimizer và Compliance Gate; không thay thế âm thầm một mã đã phát hành."
                        ),
                    ),
                ],
                [
                    "So sánh ACB với mã ngân hàng đang có trong phương án",
                    "Rủi ro nào khiến luận điểm ACB mất hiệu lực?",
                    "Nếu thêm ACB thì cần chạy lại danh mục thế nào?",
                ],
            )
        return (
            (
                f"Trong kết quả Advisor đã phát hành cho “{selected.name}”, tôi không tìm "
                "thấy khoản phân bổ vào mã bạn vừa hỏi."
            ),
            [
                ChatAnswerSection(
                    title="Các sản phẩm cổ phiếu/ETF thực sự được chọn",
                    body=named_products or "Không có sản phẩm cổ phiếu hoặc ETF được chọn.",
                )
            ],
            ["Giải thích cụ thể cách phân bổ tài sản", "So sánh cả 3 phương án"],
        )

    explanation = next(
        (
            item
            for item in selected.allocation_explanations
            if item.product_id == allocation.product_id
        ),
        None,
    )
    reference_price = getattr(allocation, "reference_price", None)
    estimated_units = getattr(allocation, "estimated_units", None)
    lot_size = getattr(allocation, "lot_size", None)
    formatted_units = (
        f"{estimated_units:,}".replace(",", ".")
        if estimated_units is not None
        else None
    )
    asset_class = allocation.asset_class.value
    if asset_class in {"EQUITY", "ETF"}:
        unit_name = "chứng chỉ quỹ ETF" if asset_class == "ETF" else "cổ phiếu"
        unit_text = (
            f"Giá tham chiếu {_money(reference_price)}/{unit_name}; tương đương khoảng "
            f"{formatted_units} {unit_name}"
            if reference_price and formatted_units is not None
            else (
                f"Snapshot chưa phát hành giá tham chiếu nên không được phép suy ra "
                f"số {unit_name}"
            )
        )
    elif asset_class == "GOLD":
        physical_unit = (
            "lượng vàng/miếng"
            if "sjc" in allocation.product_id.lower()
            else "chỉ vàng"
        )
        unit_text = (
            f"Đơn giá tham chiếu {_money(reference_price)}/{physical_unit}; "
            f"phân bổ {formatted_units} {physical_unit}"
            if reference_price and formatted_units is not None
            else "Đơn vị vàng vật chất phải được xác nhận lại trước khi thực hiện"
        )
    elif asset_class == "BOND_FUND":
        unit_text = (
            f"NAV tham chiếu {_money(reference_price)}/chứng chỉ quỹ"
            if reference_price
            else "Số chứng chỉ quỹ phụ thuộc NAV tại ngày khớp lệnh"
        )
    elif asset_class == "DEPOSIT":
        unit_text = (
            "Số vốn được triển khai theo khoản tiền gửi và kỳ hạn; "
            "không quy đổi sang cổ phiếu"
        )
    elif asset_class == "CASH":
        unit_text = "Giữ trực tiếp bằng VND trong vùng thanh khoản tức thời"
    else:
        unit_text = "Đơn vị thực hiện phải được xác nhận theo tài liệu sản phẩm"
    if (
        asset_class in {"EQUITY", "ETF"}
        and estimated_units is not None
        and lot_size
        and lot_size > 1
    ):
        lot_count = f"{estimated_units // lot_size:,}".replace(",", ".")
        unit_text += f" ({lot_count} lô {lot_size})"
    unit_text += "."
    memo = build_investment_memo(
        allocation=allocation,
        explanation=explanation,
        scenario=selected,
    )
    ticker = _allocation_ticker(allocation)
    sections = [
        ChatAnswerSection(
            title="Kết luận và luận điểm đầu tư",
            body=_bounded_text(
                memo.thesis,
                "Chưa có đủ bằng chứng để hình thành luận điểm đầu tư cho sản phẩm.",
            ),
        ),
        ChatAnswerSection(
            title="Số vốn và số lượng minh họa",
            body=_bounded_text(
                [
                    f"Vốn {_money(allocation.amount)}; {unit_text}",
                    *memo.proof_chain,
                ],
                "Chưa có chuỗi chứng minh định lượng.",
            ),
        ),
        ChatAnswerSection(
            title="Dẫn chứng sản phẩm và thị trường",
            body=_bounded_text(
                memo.market_evidence,
                (
                    "Chưa có dữ liệu thị trường/chỉ số cơ bản bổ sung. Luận điểm hiện "
                    "chỉ được chứng minh ở cấp optimizer và điều kiện sản phẩm."
                ),
            ),
        ),
        ChatAnswerSection(
            title="Chất xúc tác cần theo dõi",
            body=_bounded_text(
                memo.catalysts,
                "Chưa có chất xúc tác đủ nguồn để đưa vào kết luận.",
            ),
        ),
        ChatAnswerSection(
            title="Rủi ro và điều kiện làm luận điểm mất hiệu lực",
            body=_bounded_text(
                memo.risks,
                "Phải tái đánh giá khi giá, lãi suất, NAV, thanh khoản hoặc hồ sơ thay đổi.",
            ),
        ),
        ChatAnswerSection(
            title="So sánh với phương án thay thế",
            body=_bounded_text(
                memo.alternatives,
                "Không có sản phẩm cùng nhóm đủ dữ liệu để so sánh trong snapshot này.",
            ),
        ),
        ChatAnswerSection(
            title="Điều kiện thực hiện và tính lại",
            body=_bounded_text(
                memo.implementation,
                "Phải xác nhận lại dữ liệu và điều kiện sản phẩm trước khi thực hiện.",
            ),
        ),
        ChatAnswerSection(
            title="Nguồn, thời điểm và giới hạn",
            body=_bounded_text(
                [
                    f"Quan sát {_source_observed_text(allocation.data_timestamp.isoformat())}.",
                    " | ".join(memo.sources),
                    *(
                        memo.limitations
                        or ["Không có cảnh báo nguồn bổ sung."]
                    ),
                    (
                        "Đây là investment memo phục vụ quyết định có giám sát, "
                        "không phải lệnh tự động."
                    ),
                ],
                "Chưa có nguồn đủ dùng.",
            ),
        ),
    ]
    return (
        (
            f"{allocation.product_name} có mặt trong phương án “{selected.name}” với "
            f"{_money(allocation.amount)} ({_pct(allocation.weight)}). Memo dưới đây chứng minh "
            "từ số vốn/tỷ trọng của optimizer đến dữ liệu sản phẩm, thị trường, chất xúc tác, "
            "rủi ro, phương án thay thế và nguồn có thời điểm."
        ),
        sections,
        [
            f"Rủi ro lớn nhất của {allocation.product_name} là gì?",
            f"Dữ liệu nào có thể làm thay đổi đánh giá {ticker or allocation.product_name}?",
            f"So sánh {allocation.product_name} với phương án thay thế",
        ],
    )
def _allocation_text(scenario: ReleasedScenario) -> str:
    ranked = sorted(scenario.allocations, key=lambda item: item.amount, reverse=True)
    return "; ".join(
        f"{item.asset_class.value}: {_pct(item.weight)} ({_money(item.amount)})"
        for item in ranked[:4]
    )


_ASSET_LABELS = {
    "CASH": "Tiền mặt",
    "DEPOSIT": "Tiền gửi",
    "BOND_FUND": "Quỹ trái phiếu",
    "EQUITY": "Cổ phiếu",
    "ETF": "ETF",
    "GOLD": "Vàng",
    "SILVER": "Bạc",
    "GOVERNMENT_BOND_REFERENCE": "Trái phiếu Chính phủ tham chiếu",
}


def _allocation_detail_sections(
    scenario: ReleasedScenario,
) -> list[ChatAnswerSection]:
    explanations = {
        item.asset_class: item for item in scenario.allocation_explanations
    }
    sections: list[ChatAnswerSection] = []
    for allocation in sorted(
        scenario.allocations,
        key=lambda item: item.amount,
        reverse=True,
    ):
        explanation = explanations.get(allocation.asset_class)
        if explanation is None:
            continue
        label = _ASSET_LABELS.get(
            allocation.asset_class.value,
            allocation.asset_class.value,
        )
        sections.append(
            ChatAnswerSection(
                title=(
                    f"{label}: {_pct(allocation.weight)} · "
                    f"{_money(allocation.amount)}"
                ),
                body=(
                    f"Vai trò: {explanation.portfolio_role} "
                    f"Lý do phân bổ: {explanation.allocation_reason} "
                    f"Điểm giới hạn: {explanation.limiting_factor} "
                    f"Khi cần tính lại: {explanation.change_trigger}"
                ),
            )
        )
    return sections


def _comparison_text(released: ReleasedOutput) -> str:
    return " | ".join(
        (
            f"{item.name}: lợi nhuận kỳ vọng {_pct(item.expected_return_rate)}, "
            f"biến động {_pct(item.risk_metrics.annualized_volatility)}, "
            f"thanh khoản {item.risk_metrics.liquidity_score:.1f}/100"
        )
        for item in released.scenarios
    )


def _advisor_panorama_sections(
    released: ReleasedOutput,
    selected: ReleasedScenario,
) -> list[ChatAnswerSection]:
    largest = max(selected.allocations, key=lambda item: item.amount, default=None)
    worst_stress = min(
        selected.risk_metrics.stress_tests,
        key=lambda item: item.estimated_change_amount,
        default=None,
    )
    financial_plan = released.financial_plan
    profile_fit = (
        (
            f"Vốn có thể đầu tư {_money(financial_plan.investable_capital)} sau khi bảo vệ "
            f"quỹ dự phòng {_money(financial_plan.emergency_reserve)}, nghĩa vụ gần hạn "
            f"{_money(financial_plan.near_term_liabilities)} và bucket thanh khoản tức thời "
            f"{_money(financial_plan.immediate_liquidity_bucket)}."
        )
        if financial_plan
        else "Kế hoạch tài chính nền chưa được phát hành; không thể kết luận mức phù hợp hồ sơ."
    )
    allocation_focus = (
        f"Khoản lớn nhất là {largest.product_name or _ASSET_LABELS.get(largest.asset_class.value, largest.asset_class.value)} "
        f"với {_money(largest.amount)} ({_pct(largest.weight)}). "
        f"Toàn danh mục: {_allocation_text(selected)}."
        if largest
        else "Không có khoản phân bổ được phát hành."
    )
    stress_text = (
        f"Kịch bản bất lợi nhất đang mô hình hóa là “{worst_stress.scenario_name}”, "
        f"làm thay đổi ước tính {_money(worst_stress.estimated_change_amount)} "
        f"({_pct(worst_stress.estimated_change_pct)}). {worst_stress.assumptions}"
        if worst_stress
        else "Chưa có stress test được phát hành cho phương án này."
    )
    triggers = _bounded_text(
        [
            f"{item.trigger_condition} Khi kích hoạt: {item.action}"
            for item in selected.monitoring_triggers[:4]
        ],
        "Tính lại khi hồ sơ, dòng tiền hoặc dữ liệu sản phẩm thay đổi đáng kể.",
        limit=650,
    )
    sources = _bounded_text(
        selected.source_summary[:5],
        released.data_snapshot,
        limit=650,
    )
    assumptions_text = _bounded_text(
        selected.assumptions_that_change_result[:5],
        (
            "Giá, lãi suất, NAV, biến động và tương quan phải được xác nhận lại "
            "tại thời điểm thực hiện."
        ),
        limit=650,
    )
    trade_offs = _bounded_text(
        selected.trade_offs,
        "Chưa có mô tả đánh đổi.",
        limit=650,
    )
    return [
        ChatAnswerSection(
            title="Toàn cảnh phù hợp với hồ sơ và mục tiêu",
            body=(
                f"{profile_fit} Phương án “{selected.name}” được thiết kế để "
                f"{selected.objective_description.lower()}"
            ),
        ),
        ChatAnswerSection(
            title="Cấu trúc danh mục và động lực lợi nhuận",
            body=(
                f"{allocation_focus} Lợi nhuận kỳ vọng toàn danh mục "
                f"{_pct(selected.expected_return_rate)} ({_money(selected.expected_return_amount)}) "
                f"với tổng chi phí mô hình {_money(selected.total_cost_amount)}."
            ),
        ),
        ChatAnswerSection(
            title="Rủi ro toàn danh mục và kịch bản bất lợi",
            body=(
                f"Biến động {_pct(selected.risk_metrics.annualized_volatility)}, "
                f"VaR 95% {_money(selected.risk_metrics.var_95_amount)}, CVaR 95% "
                f"{_money(selected.risk_metrics.cvar_95_amount)}, thanh khoản "
                f"{selected.risk_metrics.liquidity_score:.1f}/100. {stress_text}"
            ),
        ),
        ChatAnswerSection(
            title="Bối cảnh dữ liệu, thị trường và giả định",
            body=(
                f"Nguồn đang dùng: {sources}. "
                f"Giả định có thể đổi kết quả: {assumptions_text}"
            ),
        ),
        ChatAnswerSection(
            title="Đánh đổi và điều kiện phải tái đánh giá",
            body=(
                f"Đánh đổi chính: {trade_offs} Ngưỡng theo dõi: {triggers}"
            ),
        ),
    ]


def _deterministic_answer(
    released: ReleasedOutput,
    message: str,
    active_scenario_id: str | None,
) -> tuple[str, list[ChatAnswerSection], list[str]]:
    selected = _scenario(released, active_scenario_id)
    if selected is None:
        return (
            "Kết quả hiện tại không có phương án được phép phát hành.",
            [
                ChatAnswerSection(
                    title="Lý do",
                    body=released.blocked_message
                    or "Legal/Compliance Gate chưa cho phép phát hành dữ liệu.",
                )
            ],
            ["Điều kiện nào đang thiếu?", "Tôi cần thay đổi hồ sơ gì?"],
        )

    normalized = _normalize(message)
    sections: list[ChatAnswerSection] = []

    if any(token in normalized for token in ["so sanh", "khac nhau", "phuong an nao"]):
        answer = (
            "Ba phương án không phải bảng xếp hạng. Chúng biểu diễn ba cách đánh đổi "
            "giữa bảo toàn vốn, thanh khoản và tăng trưởng."
        )
        sections.extend(
            [
                ChatAnswerSection(
                    title="So sánh cùng một thước đo",
                    body=_comparison_text(released),
                ),
                ChatAnswerSection(
                    title=f"Đang xem: {selected.name}",
                    body=selected.objective_description,
                ),
            ]
        )
    elif any(token in normalized for token in ["risk tolerance", "risk capacity"]):
        answer = (
            "Risk tolerance phản ánh mức biến động bạn cảm thấy có thể chấp nhận; "
            "risk capacity phản ánh mức tổn thất tài chính bạn thực sự có thể chịu mà "
            "không làm hỏng mục tiêu."
        )
        sections.extend(
            [
                ChatAnswerSection(
                    title="Trong optimizer",
                    body=(
                        f"Risk capacity được dùng như ràng buộc cứng. Phương án “{selected.name}” "
                        f"đang có biến động {_pct(selected.risk_metrics.annualized_volatility)} "
                        f"so với trần hồ sơ {_pct(selected.risk_metrics.risk_ceiling)}."
                    ),
                ),
                ChatAnswerSection(
                    title="Trong quyết định hành vi",
                    body=(
                        "Risk tolerance giúp đánh giá liệu bạn có đủ thoải mái để duy trì "
                        "phương án khi thị trường giảm, thay vì bán ra vì lo lắng."
                    ),
                ),
            ]
        )
    elif any(
        token in normalized
        for token in [
            "diem yeu",
            "bat loi",
            "han che",
            "danh doi",
            "trade off",
        ]
    ):
        worst_stress = min(
            selected.risk_metrics.stress_tests,
            key=lambda item: item.estimated_change_amount,
            default=None,
        )
        answer = (
            f"Điểm yếu chính của “{selected.name}” là phương án đã sử dụng phần lớn "
            "ngân sách rủi ro của hồ sơ, nên dư địa chịu thêm biến động thấp hơn "
            "phương án an toàn hơn."
        )
        sections.append(
            ChatAnswerSection(
                title="Đánh đổi cần chấp nhận",
                body=" ".join(selected.trade_offs),
            )
        )
        if worst_stress:
            sections.append(
                ChatAnswerSection(
                    title=f"Nếu kịch bản xấu xảy ra: {worst_stress.scenario_name}",
                    body=(
                        f"Thay đổi ước tính {_money(worst_stress.estimated_change_amount)}. "
                        f"{worst_stress.assumptions}"
                    ),
                )
            )
    elif any(token in normalized for token in ["rui ro", "lo", "var", "stress"]):
        worst_stress = min(
            selected.risk_metrics.stress_tests,
            key=lambda item: item.estimated_change_amount,
            default=None,
        )
        answer = (
            f"Rủi ro của “{selected.name}” đang nằm trong trần hồ sơ, nhưng điều đó "
            "không có nghĩa là phương án không thể lỗ."
        )
        sections.append(
            ChatAnswerSection(
                title="Mức rủi ro mô hình",
                body=(
                    f"Biến động {_pct(selected.risk_metrics.annualized_volatility)}; "
                    f"VaR 95% {_money(selected.risk_metrics.var_95_amount)}; "
                    f"trần hồ sơ {_pct(selected.risk_metrics.risk_ceiling)}."
                ),
            )
        )
        if worst_stress:
            sections.append(
                ChatAnswerSection(
                    title=f"Stress test: {worst_stress.scenario_name}",
                    body=(
                        f"Thay đổi ước tính {_money(worst_stress.estimated_change_amount)}. "
                        f"{worst_stress.assumptions}"
                    ),
                )
            )
    elif any(token in normalized for token in ["phan bo", "tai san", "danh muc"]):
        answer = (
            f"“{selected.name}” được giải thích theo từng nhóm tài sản dưới đây. "
            "Mỗi nhóm đều có số tiền, tỷ trọng, vai trò, lý do giữ tỷ trọng hiện tại, "
            "rủi ro giới hạn và điều kiện khiến hệ thống phải tối ưu lại."
        )
        sections.extend(_allocation_detail_sections(selected))
        sections.append(
            ChatAnswerSection(
                title="Ranh giới của phần giải thích",
                body=(
                    "Các số liệu đến trực tiếp từ optimizer. Trong chế độ COMPARE_ONLY, "
                    "hệ thống giải thích cụ thể ở cấp nhóm tài sản nhưng không biến kết quả "
                    "thành lệnh mua từng mã sản phẩm."
                ),
            )
        )
        if not selected.allocation_explanations:
            sections.extend(
                [
                ChatAnswerSection(
                    title="Các nhóm tài sản",
                    body=_allocation_text(selected),
                ),
                ]
            )
    elif any(token in normalized for token in ["thanh khoan", "rut", "can tien"]):
        answer = (
            f"Điểm thanh khoản của “{selected.name}” là "
            f"{selected.risk_metrics.liquidity_score:.1f}/100."
        )
        sections.extend(
            [
                ChatAnswerSection(
                    title="Nhu cầu đã được giữ lại",
                    body=(
                        f"Hồ sơ yêu cầu {_money(released.financial_plan.immediate_liquidity_bucket)} "
                        "trong bucket thanh khoản tức thời."
                        if released.financial_plan
                        else "Thông tin bucket thanh khoản không được phát hành."
                    ),
                ),
                ChatAnswerSection(
                    title="Điều cần cân nhắc",
                    body=(
                        "Thanh khoản cao hơn thường làm giảm phần vốn có thể chấp nhận "
                        "khóa lâu để tìm kiếm lợi nhuận kỳ vọng cao hơn."
                    ),
                ),
            ]
        )
    else:
        answer = (
            f"“{selected.name}” được tạo để {selected.objective_description.lower()} "
            "Các con số dưới đây đến trực tiếp từ optimizer đã qua Compliance Gate."
        )
        sections.extend(
            [
                ChatAnswerSection(
                    title="Kết quả cốt lõi",
                    body=(
                        f"Lợi nhuận kỳ vọng {_pct(selected.expected_return_rate)} "
                        f"({_money(selected.expected_return_amount)}); biến động "
                        f"{_pct(selected.risk_metrics.annualized_volatility)}; "
                        f"chi phí {_money(selected.total_cost_amount)}."
                    ),
                ),
                ChatAnswerSection(
                    title="Đánh đổi chính",
                    body=" ".join(selected.trade_offs),
                ),
                ChatAnswerSection(
                    title="Phân bổ nổi bật",
                    body=_allocation_text(selected),
                ),
            ]
        )

    largest = max(
        selected.allocations,
        key=lambda item: item.amount,
        default=None,
    )
    largest_question = (
        f"Vì sao {_ASSET_LABELS.get(largest.asset_class.value, largest.asset_class.value)} "
        f"chiếm {_pct(largest.weight)}?"
        if largest
        else "Giải thích phân bổ tài sản"
    )
    return (
        answer,
        sections,
        [
            "So sánh cả 3 phương án",
            "Rủi ro lớn nhất là gì?",
            largest_question,
        ],
    )


def _llm_wording(
    released: ReleasedOutput,
    message: str,
    active_scenario_id: str | None,
    conversation_history: list[dict[str, str]],
    verified_answer: str,
) -> tuple[_OpenAIChatNarrative | None, str]:
    selected = _scenario(released, active_scenario_id)
    compact_context = {
        "output_release_type": released.output_release_type,
        "data_snapshot": released.data_snapshot,
        "available_scenarios": [
            {
                "scenario_id": item.scenario_id,
                "name": item.name,
                "role": item.recommendation_role,
                "objective": item.objective_description,
            }
            for item in released.scenarios
        ],
        "active_scenario": (
            {
                "name": selected.name,
                "objective": selected.objective_description,
                "expected_return_rate": selected.expected_return_rate,
                "expected_return_amount": selected.expected_return_amount,
                "total_cost_amount": selected.total_cost_amount,
                "risk_metrics": selected.risk_metrics.model_dump(),
                "allocations": [
                    {
                        "asset_class": str(item.asset_class),
                        "amount": item.amount,
                        "weight": item.weight,
                        "expected_return_amount": item.expected_return_amount,
                    }
                    for item in selected.allocations
                ],
                "trade_offs": selected.trade_offs,
            }
            if selected
            else None
        ),
    }
    narrative, generated_by = generate_structured(
        _OpenAIChatNarrative,
        system_prompt=(
            "Bạn là Monopoly AI, một trợ lý tài chính tiếng Việt trò chuyện tự nhiên. "
            "Hãy dùng các lượt nói trước để hiểu đại từ và câu hỏi nối tiếp; không chào "
            "lại, không nhắc lại câu hỏi và không mở đầu bằng 'Tôi đã nhận câu hỏi'. "
            "Câu đầu phải trả lời thẳng điều người dùng hỏi. Viết từ một đến ba câu ngắn, "
            "giọng điệu gần gũi nhưng chuyên nghiệp. Chỉ diễn đạt lại verified_answer và "
            "released context đã qua kiểm duyệt; không tính toán, suy ra hoặc bổ sung dữ "
            "liệu. Không dùng chữ số trong phần diễn đạt vì các thẻ deterministic sẽ hiển "
            "thị số liệu chính xác. Không chọn thay người dùng, không ra lệnh mua/bán và "
            "không cam kết lợi nhuận. Không nhắc lại số liệu dưới dạng chữ. Chỉ thêm một "
            "section khi thực sự giúp làm rõ."
        ),
        user_content=json.dumps(
            {
                "conversation_history": conversation_history[-6:],
                "current_question": message,
                "verified_answer": verified_answer,
                "released_context": compact_context,
            },
            ensure_ascii=False,
        ),
    )
    if narrative is None:
        return None, "DETERMINISTIC_FALLBACK"
    rendered = " ".join(
        [
            narrative.message,
            *(section.title + " " + section.body for section in narrative.sections),
        ]
    )
    normalized_rendered = _normalize(rendered)
    numeric_units = [
        "phan tram",
        "vnd",
        "trieu",
        "ty dong",
        "nghin dong",
    ]
    if any(char.isdigit() for char in rendered) or any(
        unit in normalized_rendered for unit in numeric_units
    ):
        return None, "DETERMINISTIC_FALLBACK"
    return narrative, generated_by


def _general_deterministic_answer(
    profile: UserFinancialProfile,
    message: str,
) -> tuple[str, list[ChatAnswerSection], list[str]]:
    normalized = _normalize(message)

    if any(token in normalized for token in ["xin chao", "chao", "hello", "hi "]):
        return (
            f"Chào {profile.display_name}. Tôi sẵn sàng trao đổi về hồ sơ, mục tiêu, "
            "dòng tiền, rủi ro và cách hệ thống xây dựng phương án.",
            [
                ChatAnswerSection(
                    title="Bạn có thể bắt đầu tự nhiên",
                    body=(
                        "Hãy kể mục tiêu bạn đang quan tâm, điều khiến bạn lo lắng hoặc "
                        "một thay đổi tài chính vừa xảy ra."
                    ),
                ),
                ChatAnswerSection(
                    title="Khi cần con số",
                    body=(
                        "Tôi sẽ yêu cầu chạy phân tích để mọi số tiền và tỷ trọng đến từ "
                        "optimizer, không do chatbot tự suy đoán."
                    ),
                ),
            ],
            [
                "Hồ sơ của tôi còn thiếu gì?",
                "Tôi nên bắt đầu từ mục tiêu nào?",
                "Risk tolerance khác risk capacity thế nào?",
            ],
        )

    if any(token in normalized for token in ["lam duoc gi", "hoat dong", "he thong", "chatbot"]):
        return (
            "Tôi là lớp hội thoại của hệ thống lập kế hoạch đa tài sản. Bạn có thể hỏi "
            "tự nhiên; khi câu hỏi cần định lượng, tôi chuyển sang pipeline tối ưu có kiểm soát.",
            [
                ChatAnswerSection(
                    title="Trước phân tích",
                    body="Trao đổi về mục tiêu, hồ sơ, khái niệm rủi ro và chuẩn bị dữ liệu.",
                ),
                ChatAnswerSection(
                    title="Sau phân tích",
                    body=(
                        "Giải thích từng phương án, so sánh đánh đổi, stress test và lập "
                        "lại kế hoạch khi bạn nạp thêm hoặc cần rút tiền."
                    ),
                ),
            ],
            ["Hồ sơ của tôi còn thiếu gì?", "Hãy phân tích hồ sơ hiện tại", "Rủi ro lớn nhất là gì?"],
        )

    if any(token in normalized for token in ["ho so", "thieu gi", "du lieu"]):
        missing: list[str] = []
        if profile.monthly_income <= 0:
            missing.append("thu nhập hàng tháng")
        if profile.monthly_expenses <= 0:
            missing.append("chi tiêu hàng tháng")
        if not profile.goals:
            missing.append("ít nhất một mục tiêu có số tiền và thời hạn")
        if profile.total_assets <= 0:
            missing.append("tổng tài sản")
        if not missing:
            message_text = (
                "Hồ sơ đã có đủ năm nhóm dữ liệu nền tảng để bắt đầu phân tích. "
                "Bạn vẫn có thể cập nhật khi hoàn cảnh thay đổi."
            )
        else:
            message_text = "Hồ sơ cần bổ sung trước khi phân tích chính xác hơn."
        return (
            message_text,
            [
                ChatAnswerSection(
                    title="Trạng thái hồ sơ",
                    body=(
                        "Đã có nhân khẩu học, tài chính, mục tiêu, rủi ro và mức thuận tiện."
                        if not missing
                        else "Còn thiếu: " + ", ".join(missing) + "."
                    ),
                ),
                ChatAnswerSection(
                    title="Bước tiếp theo",
                    body="Mở mục Hồ sơ để kiểm tra, sau đó chọn Lưu & phân tích ngay.",
                ),
            ],
            ["Hãy phân tích hồ sơ hiện tại", "Risk capacity của tôi được dùng thế nào?"],
        )

    if any(token in normalized for token in ["risk tolerance", "risk capacity", "chiu rui ro"]):
        return (
            "Risk tolerance là mức biến động bạn cảm thấy thoải mái; risk capacity là "
            "khả năng tài chính thực tế chịu được tổn thất mà không phá vỡ mục tiêu.",
            [
                ChatAnswerSection(
                    title="Nguyên tắc an toàn",
                    body=(
                        "Khi hai mức khác nhau, hệ thống ưu tiên giới hạn thận trọng hơn "
                        "và kiểm tra thêm mức sụt giảm tối đa bạn chấp nhận."
                    ),
                ),
                ChatAnswerSection(
                    title="Trong optimizer",
                    body=(
                        "Risk capacity quyết định trần rủi ro; tolerance giúp giải thích "
                        "phương án nào dễ duy trì về mặt hành vi."
                    ),
                ),
            ],
            ["Mức sụt giảm tối đa có ý nghĩa gì?", "Hãy phân tích hồ sơ hiện tại"],
        )

    if any(token in normalized for token in ["muc tieu", "uu tien", "bat dau"]):
        primary = profile.goals[0].name if profile.goals else profile.goal
        return (
            f"Mục tiêu chính hiện tại là “{primary}”. Hệ thống sẽ bảo vệ thanh khoản "
            "và nghĩa vụ gần hạn trước khi phân bổ phần vốn còn lại.",
            [
                ChatAnswerSection(
                    title="Cách ưu tiên",
                    body=(
                        "Ưu tiên cao và ít linh hoạt được xem trước; mục tiêu linh hoạt "
                        "có thể điều chỉnh thời hạn hoặc số tiền khi ràng buộc xung đột."
                    ),
                ),
                ChatAnswerSection(
                    title="Để có phương án cụ thể",
                    body="Chọn Hãy phân tích hồ sơ hiện tại để chạy đầy đủ pipeline.",
                ),
            ],
            ["Hãy phân tích hồ sơ hiện tại", "Hồ sơ của tôi còn thiếu gì?"],
        )

    if any(token in normalized for token in ["no", "tra no", "bao hiem", "dong tien"]):
        return (
            "Trước khi đầu tư, hệ thống tách nghĩa vụ trả nợ, chi tiêu, quỹ dự phòng "
            "và nhu cầu thanh khoản khỏi phần vốn có thể phân bổ.",
            [
                ChatAnswerSection(
                    title="Vì sao cần bước này?",
                    body=(
                        "Một danh mục có lợi nhuận kỳ vọng tốt vẫn không phù hợp nếu làm "
                        "thiếu tiền cho nghĩa vụ thiết yếu hoặc buộc phải bán sớm."
                    ),
                ),
                ChatAnswerSection(
                    title="Vai trò của bảo hiểm",
                    body=(
                        "Bảo hiểm là lớp bảo vệ rủi ro cuộc sống, không được cộng trực tiếp "
                        "vào vốn đầu tư có thể sử dụng."
                    ),
                ),
            ],
            ["Hồ sơ của tôi còn thiếu gì?", "Hãy phân tích hồ sơ hiện tại"],
        )

    return (
        "Bạn muốn tôi tập trung vào hồ sơ, mục tiêu, dòng tiền hay cách các phương án "
        "được hình thành? Hãy nói quyết định bạn đang cân nhắc; nếu cần con số cá nhân "
        "hóa, tôi sẽ dùng hồ sơ và optimizer thay vì tự đoán.",
        [
            ChatAnswerSection(
                title="Có thể hỏi theo cách của bạn",
                body=(
                    "Ví dụ: tôi cần tiền sau sáu tháng, tôi lo danh mục giảm mạnh, hoặc "
                    "vì sao phương án cân bằng hợp với mục tiêu của tôi?"
                ),
            ),
        ],
        ["Hồ sơ của tôi còn thiếu gì?", "Tôi nên bắt đầu từ mục tiêu nào?", "Hãy phân tích hồ sơ hiện tại"],
    )


def _general_llm_wording(
    message: str,
    conversation_history: list[dict[str, str]],
    verified_answer: str,
) -> tuple[_OpenAIChatNarrative | None, str]:
    narrative, generated_by = generate_structured(
        _OpenAIChatNarrative,
        system_prompt=(
            "Bạn là Monopoly AI, một trợ lý tài chính tiếng Việt trò chuyện tự nhiên. "
            "Dùng lịch sử để hiểu câu hỏi nối tiếp và đại từ. Không chào lại, không lặp "
            "câu hỏi, không nói 'Tôi đã nhận câu hỏi'. Trả lời thẳng ngay câu đầu, từ một "
            "đến ba câu ngắn, gần gũi và cụ thể. Dùng verified_answer làm nền tảng nhưng "
            "được phép diễn đạt mềm mại hơn. Không đưa lệnh mua bán, không cam kết lợi "
            "nhuận và không tự tạo số liệu cá nhân. Chỉ thêm một section nếu cần."
        ),
        user_content=json.dumps(
            {
                "conversation_history": conversation_history[-6:],
                "current_question": message,
                "verified_answer": verified_answer,
            },
            ensure_ascii=False,
        ),
    )
    return narrative, generated_by


def interpret_follow_up(
    original: PlanningRequest,
    message: str,
    released: ReleasedOutput | None = None,
    active_scenario_id: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> tuple[ChatResponse, PlanningRequest | None]:
    normalized = _normalize(message)
    history = conversation_history or []
    amount = _extract_amount(message)
    changes: dict[str, Any] = {}
    intent = "EXPLAIN"

    if amount is not None and any(token in normalized for token in ["nap", "them", "bo sung"]):
        intent = "ADD_CAPITAL"
        changes["total_assets"] = original.profile.total_assets + amount
    elif amount is not None and any(token in normalized for token in ["rut", "can dung", "can tien"]):
        intent = "WITHDRAWAL_NEED"
        changes["liquidity_need"] = amount
        month_match = re.search(r"trong\s+(\d+)\s*thang", normalized)
        if month_match:
            changes["liquidity_need_months"] = int(month_match.group(1))

    if changes:
        payload = original.model_dump()
        payload["profile"] = {**payload["profile"], **changes}
        revised = PlanningRequest.model_validate(payload)
        changed_text = "; ".join(
            f"{key}: {_money(value) if isinstance(value, int) and key != 'liquidity_need_months' else value}"
            for key, value in changes.items()
        )
        change_sections = [
            ChatAnswerSection(
                title="Thay đổi được hiểu",
                body=changed_text,
            ),
            ChatAnswerSection(
                title="Điều hệ thống sẽ làm",
                body=(
                    "Tính lại vốn khả dụng, eligibility, ba bài toán CP-SAT, "
                    "risk engine và Compliance Gate."
                ),
            ),
        ]
        if intent == "WITHDRAWAL_NEED" and released is not None:
            current_scenario = _scenario(released, active_scenario_id)
            if current_scenario is not None:
                change_sections.extend(
                    ChatAnswerSection(
                        title=(
                            f"Ưu tiên {option.priority}: {option.title} · "
                            f"khả dụng {_money(option.available_amount)}"
                        ),
                        body=(
                            f"Chi phí: {option.estimated_cost} "
                            f"Ảnh hưởng: {option.portfolio_impact} "
                            f"Điều kiện: {' '.join(option.conditions)}"
                        ),
                    )
                    for option in sorted(
                        current_scenario.withdrawal_options,
                        key=lambda item: item.priority,
                    )
                )
        return (
            ChatResponse(
                recommendation_id="",
                intent=intent,
                message=(
                    "Tôi đã nhận thay đổi dòng tiền. Toàn bộ pipeline sẽ chạy lại; "
                    "không tái sử dụng tỷ trọng cũ."
                ),
                replanning_required=True,
                proposed_profile_changes=changes,
                sections=change_sections,
                suggested_questions=[
                    "So sánh kết quả mới với kết quả cũ",
                    "Rủi ro thay đổi thế nào?",
                ],
            ),
            revised,
        )

    memo_scenario = (
        _scenario(released, active_scenario_id)
        if released is not None
        else None
    )
    has_memo_target = bool(
        memo_scenario
        and (
            _requested_product(memo_scenario, message) is not None
            or re.search(r"\bacb\b", normalized)
        )
    )
    if (
        released is not None
        and has_memo_target
        and _investment_memo_question(message)
        and not (
            _gold_question(message)
            and any(
                token in normalized
                for token in ["chart", "vi mo", "gia the gioi", "comex"]
            )
        )
    ):
        answer, sections, suggestions = _product_answer(
            released,
            message,
            active_scenario_id,
        )
        return (
            ChatResponse(
                recommendation_id="",
                intent="EXPLAIN_PRODUCT_ALLOCATION",
                message=answer,
                replanning_required=False,
                sections=sections,
                suggested_questions=suggestions,
                generated_by="DATA_REGISTRY",
            ),
            None,
        )

    contextual_deposit_question = (
        released is not None
        and _deposit_question(message)
        and any(
            token in normalized
            for token in [
                "phuong an",
                "khoan nay",
                "o day",
                "trong nay",
                "danh muc",
            ]
        )
    )
    if released is not None and (
        _portfolio_deposit_question(message) or contextual_deposit_question
    ):
        answer, sections, suggestions = _portfolio_deposit_answer(
            released,
            active_scenario_id,
        )
        return (
            ChatResponse(
                recommendation_id="",
                intent="EXPLAIN_DEPOSIT_IMPLEMENTATION",
                message=answer,
                replanning_required=False,
                sections=sections,
                suggested_questions=suggestions,
                generated_by="DATA_REGISTRY",
            ),
            None,
        )

    if _deposit_question(message):
        answer, sections, suggestions = _deposit_answer(
            original.profile,
            message,
        )
        return (
            ChatResponse(
                recommendation_id="",
                intent="COMPARE_DEPOSIT_RATES",
                message=answer,
                replanning_required=False,
                sections=sections,
                suggested_questions=suggestions,
                generated_by="DATA_REGISTRY",
            ),
            None,
        )

    if released is not None and _gold_question(message):
        answer, sections, suggestions = _gold_answer(
            released,
            active_scenario_id,
        )
        return (
            ChatResponse(
                recommendation_id="",
                intent="EXPLAIN_GOLD_ALLOCATION",
                message=answer,
                replanning_required=False,
                sections=sections,
                suggested_questions=suggestions,
                generated_by="DATA_REGISTRY",
            ),
            None,
        )

    if _source_question(message):
        answer, sections, suggestions = _data_source_answer()
        return (
            ChatResponse(
                recommendation_id="",
                intent="DATA_PROVENANCE",
                message=answer,
                replanning_required=False,
                sections=sections,
                suggested_questions=suggestions,
                generated_by="DATA_REGISTRY",
            ),
            None,
        )

    if released is not None and _product_question(message):
        answer, sections, suggestions = _product_answer(
            released,
            message,
            active_scenario_id,
        )
        return (
            ChatResponse(
                recommendation_id="",
                intent="EXPLAIN_PRODUCT_ALLOCATION",
                message=answer,
                replanning_required=False,
                sections=sections,
                suggested_questions=suggestions,
                generated_by="DATA_REGISTRY",
            ),
            None,
        )
    if released is None:
        answer, sections, suggestions = _general_deterministic_answer(
            original.profile,
            message,
        )
        narrative, provider_generated_by = _general_llm_wording(
            message,
            history,
            answer,
        )
        generated_by = "DETERMINISTIC_FALLBACK"
        if narrative is not None:
            answer = narrative.message
            narrative_sections = [
                section
                for section in narrative.sections
                if _normalize(section.body) not in _normalize(answer)
                and _normalize(answer) not in _normalize(section.body)
            ]
            sections = narrative_sections or sections[:1]
            suggestions = narrative.suggested_questions or suggestions
            generated_by = provider_generated_by
        return (
            ChatResponse(
                recommendation_id="",
                intent=intent,
                message=answer,
                replanning_required=False,
                sections=sections,
                suggested_questions=suggestions,
                generated_by=generated_by,
            ),
            None,
        )

    answer, sections, suggestions = _deterministic_answer(
        released,
        message,
        active_scenario_id,
    )
    narrative, provider_generated_by = _llm_wording(
        released,
        message,
        active_scenario_id,
        history,
        answer,
    )
    generated_by = "DETERMINISTIC_FALLBACK"
    if narrative is not None:
        answer = narrative.message
        suggestions = narrative.suggested_questions or suggestions
        generated_by = provider_generated_by
    advisor_mode = released.output_release_type == "ADVISORY_SELECTED"
    detail_requested = any(
        token in normalized
        for token in [
            "chi tiet",
            "cu the",
            "phan bo",
            "ngan hang",
            "ky han",
            "so von",
        ]
    )
    if advisor_mode and memo_scenario is not None:
        existing_titles = {section.title for section in sections}
        sections.extend(
            section
            for section in _advisor_panorama_sections(released, memo_scenario)
            if section.title not in existing_titles
        )
    elif not detail_requested:
        sections = sections[:2]

    return (
        ChatResponse(
            recommendation_id="",
            intent=intent,
            message=answer,
            replanning_required=False,
            sections=sections,
            suggested_questions=suggestions,
            generated_by=generated_by,
        ),
        None,
    )
