from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any

from backend.app.db import fetch_asset_products
from backend.app.models import AssetClass, AssetProduct


SUPPORTED_TENORS = (1, 3, 6, 12, 18, 24, 36)
SUPPORTED_SEGMENTS = {"retail", "priority", "private"}
TARGET_BANKS = ("MBBank", "Techcombank", "VPBank")


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )


def extract_deposit_query(
    message: str,
    *,
    default_amount: int,
    default_segment: str,
) -> tuple[int, int, str]:
    normalized = _normalize(message).replace(",", ".")
    amount = default_amount
    amount_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(ty|trieu|m|k|nghin)\b",
        normalized,
    )
    if amount_match:
        multiplier = {
            "ty": 1_000_000_000,
            "trieu": 1_000_000,
            "m": 1_000_000,
            "k": 1_000,
            "nghin": 1_000,
        }[amount_match.group(2)]
        amount = round(float(amount_match.group(1)) * multiplier)

    tenor = 12
    tenor_match = re.search(r"(\d+)\s*(?:thang|m)\b", normalized)
    if tenor_match:
        requested = int(tenor_match.group(1))
        tenor = min(SUPPORTED_TENORS, key=lambda value: abs(value - requested))

    segment = default_segment if default_segment in SUPPORTED_SEGMENTS else "retail"
    if "private" in normalized:
        segment = "private"
    elif any(token in normalized for token in ("uu tien", "priority")):
        segment = "priority"
    elif any(token in normalized for token in ("pho thong", "retail")):
        segment = "retail"
    return max(1_000_000, amount), tenor, segment


def _eligibility(
    product: AssetProduct,
    *,
    amount: int,
    customer_segment: str,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    required_segment = str(
        product.eligibility_conditions.get("customer_segment", "retail")
    )
    if required_segment == "private" and customer_segment != "private":
        reasons.append("Mức tham chiếu này chỉ áp dụng cho khách hàng Private.")
    if amount < product.minimum_investment:
        reasons.append(
            f"Số vốn tối thiểu là {product.minimum_investment:,.0f} VND."
        )
    if product.maximum_investment is not None and amount > product.maximum_investment:
        reasons.append(
            "Bảng tham chiếu hiện tại chỉ công bố điều kiện cho số dư dưới "
            f"{product.maximum_investment + 1:,.0f} VND."
        )
    return not reasons, reasons


def compare_deposits(
    *,
    amount: int,
    tenor_months: int,
    customer_segment: str = "retail",
) -> dict[str, Any]:
    if tenor_months not in SUPPORTED_TENORS:
        raise ValueError(
            "Kỳ hạn được hỗ trợ: " + ", ".join(map(str, SUPPORTED_TENORS)) + " tháng."
        )
    if customer_segment not in SUPPORTED_SEGMENTS:
        raise ValueError("Phân khúc hợp lệ: retail, priority hoặc private.")

    products = [
        AssetProduct.model_validate(row)
        for row in fetch_asset_products(
            asset_class=AssetClass.DEPOSIT,
            approved_only=True,
        )
        if row.get("provider") in TARGET_BANKS
        and int(row.get("eligibility_conditions", {}).get("tenor_months", 0))
        == tenor_months
    ]
    comparisons: list[dict[str, Any]] = []
    for product in products:
        eligible, reasons = _eligibility(
            product,
            amount=amount,
            customer_segment=customer_segment,
        )
        annual_rate = product.expected_return
        projected_interest = round(amount * annual_rate * tenor_months / 12)
        comparisons.append(
            {
                "product_id": product.product_id,
                "provider": product.provider,
                "product_name": product.product_name,
                "tenor_months": tenor_months,
                "amount": amount,
                "customer_segment": customer_segment,
                "eligible": eligible,
                "annual_rate": annual_rate,
                "projected_interest": projected_interest,
                "maturity_amount": amount + projected_interest,
                "liquidity_score": product.liquidity_score,
                "lockup_days": product.lockup_period,
                "conditions": product.eligibility_conditions,
                "eligibility_reasons": reasons
                or ["Phù hợp với số vốn và phân khúc trong phạm vi bảng tham chiếu."],
                "early_exit_note": (
                    "Rút trước hạn thường làm khoản tiền gửi hưởng lãi không kỳ hạn; "
                    "cần kiểm tra quy định chính thức của ngân hàng."
                ),
                "source_reference": product.source_reference,
                "data_timestamp": product.data_timestamp.isoformat(),
                "verification_status": product.verification_status,
                "data_confidence": product.data_confidence,
            }
        )
    comparisons.sort(
        key=lambda row: (
            not row["eligible"],
            -row["annual_rate"],
            row["provider"],
        )
    )

    eligible_rows = [row for row in comparisons if row["eligible"]]
    if eligible_rows:
        leader = eligible_rows[0]
        guidance = (
            f"Trong phạm vi dữ liệu đủ điều kiện, {leader['provider']} có mức lãi suất "
            f"tham chiếu cao nhất là {leader['annual_rate'] * 100:.2f}%/năm cho kỳ hạn "
            f"{tenor_months} tháng. Đây là kết quả so sánh, không phải lệnh mở sổ; "
            "hãy xác nhận lại mức áp dụng trên ứng dụng ngân hàng."
        )
    else:
        guidance = (
            "Chưa có mức lãi suất nào đồng thời khớp số vốn và phân khúc đã chọn. "
            "Hãy đổi phân khúc, số vốn hoặc kỳ hạn; hệ thống không tự gán mức ưu đãi "
            "khi chưa đủ điều kiện."
        )
    return {
        "amount": amount,
        "tenor_months": tenor_months,
        "customer_segment": customer_segment,
        "supported_tenors": list(SUPPORTED_TENORS),
        "comparison_count": len(comparisons),
        "guidance": guidance,
        "comparisons": comparisons,
        "scope": "RESEARCH_EDUCATION_COMPARE_ONLY",
        "calculation_note": (
            "Tiền lãi minh họa = số vốn × lãi suất năm × kỳ hạn/12; chưa tính thuế, "
            "tái tục, lãi kép hoặc thay đổi lãi suất."
        ),
        "generated_at": datetime.now().astimezone().isoformat(),
    }
