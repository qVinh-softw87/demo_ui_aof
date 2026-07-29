from __future__ import annotations

from backend.app.models import (
    AssetClass,
    AssetProduct,
    EligibilityDecision,
    RightsStatus,
    UserFinancialProfile,
)


def evaluate_product_eligibility(
    product: AssetProduct,
    profile: UserFinancialProfile,
) -> EligibilityDecision:
    codes: list[str] = []
    reasons: list[str] = []

    if product.rights_status != RightsStatus.APPROVED:
        codes.append("RIGHTS_NOT_APPROVED")
        reasons.append("Quyền sử dụng dữ liệu chưa được phê duyệt cho đầu ra.")

    if product.asset_class == AssetClass.GOVERNMENT_BOND_REFERENCE:
        codes.append("REFERENCE_DATA_NOT_INVESTIBLE")
        reasons.append("Đây là dữ liệu tham chiếu, không phải sản phẩm phân bổ trực tiếp.")

    if product.asset_class in profile.excluded_asset_classes:
        codes.append("ASSET_CLASS_EXCLUDED_BY_USER")
        reasons.append("Người dùng đã loại nhóm tài sản này.")

    if product.minimum_investment > profile.investable_capital:
        codes.append("MINIMUM_INVESTMENT_EXCEEDS_CAPITAL")
        reasons.append("Số tiền đầu tư tối thiểu vượt vốn khả dụng.")

    horizon_days = profile.horizon_months * 30
    if product.lockup_period > horizon_days:
        codes.append("LOCKUP_EXCEEDS_HORIZON")
        reasons.append("Thời gian khóa vốn dài hơn thời hạn mục tiêu.")

    tolerated_lockup_days = profile.lockup_tolerance_months * 30
    if product.lockup_period > tolerated_lockup_days:
        codes.append("LOCKUP_EXCEEDS_USER_TOLERANCE")
        reasons.append("Thời gian khóa vốn vượt mức người dùng chấp nhận.")

    liquidity_horizon_days = profile.liquidity_need_months * 30
    if (
        profile.liquidity_need > 0
        and product.lockup_period > liquidity_horizon_days
        and product.liquidity_score < 70
    ):
        codes.append("LIQUIDITY_MISMATCH")
        reasons.append("Khóa vốn và thanh khoản không phù hợp nhu cầu rút gần hạn.")

    required_segment = product.eligibility_conditions.get("customer_segment")
    if required_segment and required_segment not in profile.customer_segments:
        codes.append("CUSTOMER_SEGMENT_MISMATCH")
        reasons.append("Phân khúc khách hàng không đáp ứng điều kiện sản phẩm.")

    return EligibilityDecision(
        product_id=product.product_id,
        asset_class=product.asset_class,
        eligible=not codes,
        reason_codes=codes or ["ELIGIBLE"],
        reasons=reasons or ["Sản phẩm đáp ứng các điều kiện dữ liệu, vốn và kỳ hạn."],
    )
