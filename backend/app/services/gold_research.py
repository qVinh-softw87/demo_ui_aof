from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.app.db.market_data import latest_observations, list_source_status


TROY_OUNCES_PER_LUONG = 37.5 / 31.1034768


@dataclass(slots=True)
class GoldResearchResult:
    product_facts: list[str] = field(default_factory=list)
    local_price_facts: list[str] = field(default_factory=list)
    global_price_facts: list[str] = field(default_factory=list)
    technical_facts: list[str] = field(default_factory=list)
    macro_facts: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


def _money(value: float) -> str:
    return f"{round(value):,}".replace(",", ".") + " VND"


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%".replace(".", ",")


def _number(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _metric_map() -> dict[str, dict[str, Any]]:
    return {row["series_key"]: row for row in latest_observations()}


def _value(metrics: dict[str, dict[str, Any]], key: str) -> float | None:
    row = metrics.get(key)
    if row is None or row.get("value") is None:
        return None
    return float(row["value"])


def _source_connected(source_id: str) -> bool:
    return any(
        row["source_id"] == source_id and row["status"] == "CONNECTED"
        for row in list_source_status()
    )


def get_gold_research(
    *,
    product_id: str,
    product_name: str,
    reference_price: float | None,
    amount: int | None = None,
    estimated_units: int | None = None,
    transaction_cost_amount: int | None = None,
) -> GoldResearchResult:
    metrics = _metric_map()
    result = GoldResearchResult()
    is_bar = "sjc" in product_id.lower() or "bullion" in product_id.lower()
    unit_name = "miếng 1 lượng" if is_bar else "chỉ vàng nhẫn 9999"
    result.product_facts.append(
        f"Sản phẩm vật chất được mô hình hóa theo đơn vị nguyên chiếc: 1 {unit_name}; không mua phần lẻ."
    )
    if amount is not None and estimated_units is not None:
        result.product_facts.append(
            f"Phương án dành {_money(amount)} cho khoảng {estimated_units} {unit_name}."
        )

    if reference_price is None:
        local_key = "SJC_BUY" if is_bar else "N24K_BUY"
        local_quote = _value(metrics, local_key)
        reference_price = (
            local_quote * 10 if is_bar and local_quote is not None else local_quote
        )

    if reference_price:
        result.local_price_facts.append(
            f"Giá khách hàng mua tham chiếu là {_money(reference_price)} mỗi {unit_name}."
        )
        if transaction_cost_amount is not None and amount:
            spread_rate = transaction_cost_amount / amount
            result.local_price_facts.append(
                f"Chênh lệch mua–bán ước tính {_pct(spread_rate)}, tương đương khoảng {_money(transaction_cost_amount)} trên số vốn phân bổ."
            )

    world_price = _value(metrics, "GC_F_PRICE")
    usd_vnd = _value(metrics, "USDVND")
    local_per_luong = reference_price if is_bar else (reference_price * 10 if reference_price else None)
    if world_price is not None:
        result.global_price_facts.append(
            f"Giá vàng thế giới tham chiếu theo hợp đồng COMEX gần nhất: {_number(world_price)} USD/troy ounce."
        )
    if world_price is not None and usd_vnd is not None and local_per_luong is not None:
        converted = world_price * usd_vnd * TROY_OUNCES_PER_LUONG
        premium = local_per_luong / converted - 1
        comparison = "cao hơn" if premium >= 0 else "thấp hơn"
        result.local_price_facts.append(
            f"Quy đổi cơ học giá thế giới theo USD/VND cho ra khoảng {_money(converted)}/lượng; giá sản phẩm trong nước đang {comparison} {_pct(abs(premium))}."
        )
        result.limitations.append(
            "Khoảng chênh này chưa trừ thuế, chi phí lưu thông, cung–cầu vàng vật chất và premium thương hiệu SJC."
        )

    for key, label in (
        ("GC_F_RETURN_1M", "1 tháng"),
        ("GC_F_RETURN_3M", "3 tháng"),
        ("GC_F_RETURN_1Y", "1 năm"),
    ):
        value = _value(metrics, key)
        if value is not None:
            result.global_price_facts.append(f"Hiệu suất {label}: {_pct(value)}.")

    ma20 = _value(metrics, "GC_F_MA20")
    ma50 = _value(metrics, "GC_F_MA50")
    rsi = _value(metrics, "GC_F_RSI14")
    volatility = _value(metrics, "GC_F_VOLATILITY_60D")
    drawdown = _value(metrics, "GC_F_MAX_DRAWDOWN_1Y")
    if world_price is not None and ma20 is not None and ma50 is not None:
        trend = (
            "xu hướng tăng ngắn–trung hạn"
            if world_price > ma20 > ma50
            else "xu hướng giảm ngắn–trung hạn"
            if world_price < ma20 < ma50
            else "trạng thái giằng co, chưa có xác nhận đồng thuận giữa MA20 và MA50"
        )
        result.technical_facts.append(
            f"Giá {_number(world_price)}; MA20 {_number(ma20)}; MA50 {_number(ma50)} — {trend}."
        )
    if rsi is not None:
        state = "quá mua" if rsi >= 70 else "quá bán" if rsi <= 30 else "trung tính"
        result.technical_facts.append(f"RSI14 ở {_number(rsi, 1)} điểm, thuộc vùng {state}.")
    if volatility is not None:
        result.technical_facts.append(
            f"Biến động năm hóa từ 60 phiên là {_pct(volatility)}."
        )
    if drawdown is not None:
        result.technical_facts.append(
            f"Mức sụt giảm lớn nhất trong chuỗi một năm là {_pct(drawdown)}."
        )

    real_yield = _value(metrics, "US_REAL_YIELD_10Y")
    real_yield_change = _value(metrics, "US_REAL_YIELD_CHANGE_3M")
    dxy = _value(metrics, "DXY")
    dxy_change = _value(metrics, "DXY_RETURN_3M")
    vn_inflation = _value(metrics, "VNM_CPI_INFLATION")
    if real_yield is not None:
        direction = "tăng" if (real_yield_change or 0) > 0 else "giảm"
        result.macro_facts.append(
            f"Lợi suất thực Mỹ 10 năm {_pct(real_yield)}, đã {direction} {_pct(abs(real_yield_change or 0))} trong khoảng ba tháng; lợi suất thực tăng thường làm chi phí cơ hội nắm giữ vàng cao hơn."
        )
    if dxy is not None:
        direction = "mạnh lên" if (dxy_change or 0) > 0 else "yếu đi"
        result.macro_facts.append(
            f"DXY ở {_number(dxy, 1)} điểm và {direction} {_pct(abs(dxy_change or 0))} trong ba tháng; USD mạnh thường là lực cản đối với giá vàng tính bằng USD."
        )
    if vn_inflation is not None:
        result.macro_facts.append(
            f"Lạm phát CPI Việt Nam gần nhất trong registry là {_pct(vn_inflation)}; đây là dữ liệu năm có độ trễ, chỉ dùng làm bối cảnh chứ không phải tín hiệu mua ngắn hạn."
        )

    if _source_connected("PNJ_GOLD"):
        result.sources.append(
            "Giá vàng vật chất: API niêm yết PNJ, gồm mã SJC và nhẫn 24K, có độ trễ."
        )
    else:
        result.limitations.append("Nguồn giá vàng vật chất PNJ/SJC đang không kết nối.")
    if _source_connected("GLOBAL_GOLD_MARKET"):
        result.sources.append(
            "Biểu đồ quốc tế: Yahoo Finance GC=F; USD/VND và DXY từ Yahoo Finance; lợi suất thực 10 năm từ FRED DFII10."
        )
    else:
        result.global_price_facts.append(
            "Phiên này chưa đồng bộ được giá hợp đồng vàng COMEX (GC=F), nên hệ thống "
            "không suy diễn xu hướng giá thế giới từ dữ liệu cũ hoặc tự tạo."
        )
        result.macro_facts.append(
            "Chưa có quan sát DXY và lợi suất thực Mỹ trong registry của phiên này; "
            "hai biến này phải được cập nhật trước khi dùng làm luận điểm vĩ mô."
        )
        result.limitations.append("Nguồn biểu đồ vàng thế giới và biến vĩ mô Mỹ đang không kết nối.")
    result.sources.append(
        "Trang sản phẩm/biểu đồ SJC được dùng để đối chiếu thương hiệu; endpoint trực tiếp của SJC có thể chặn truy cập máy bằng Cloudflare."
    )
    result.limitations.append(
        "GC=F là hợp đồng tương lai COMEX, không phải giá giao ngay LBMA và không phải giá thực hiện tại Việt Nam."
    )
    return result
