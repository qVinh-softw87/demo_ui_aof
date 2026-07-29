from __future__ import annotations

from backend.app.models import FinancialPlan, UserFinancialProfile


def build_financial_plan(profile: UserFinancialProfile) -> FinancialPlan:
    capital = profile.investable_capital
    immediate = min(capital, profile.liquidity_need)
    remaining = capital - immediate

    if profile.horizon_months <= 12:
        medium = remaining
    elif profile.horizon_months <= 36:
        medium = round(remaining * 0.55)
    else:
        medium = round(remaining * 0.30)
    long_term = remaining - medium

    return FinancialPlan(
        total_assets=profile.total_assets,
        emergency_reserve=profile.emergency_reserve,
        near_term_liabilities=profile.near_term_liabilities,
        investable_capital=capital,
        immediate_liquidity_bucket=immediate,
        medium_term_bucket=medium,
        long_term_capacity=long_term,
        assumptions=[
            "Vốn khả dụng = tổng tài sản - quỹ dự phòng - nghĩa vụ gần hạn.",
            "Nhu cầu thanh khoản được giữ như một ràng buộc tối thiểu, không phải dự báo.",
            "Dữ liệu sản phẩm trong prototype là snapshot giả lập, không phải báo giá giao dịch.",
        ],
    )
