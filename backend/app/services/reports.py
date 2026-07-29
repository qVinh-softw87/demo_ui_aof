from __future__ import annotations

from html import escape
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    KeepTogether,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.app.models import ReleasedOutput


ASSET_LABELS = {
    "CASH": "Tiền mặt",
    "GOLD": "Vàng",
    "SILVER": "Bạc",
    "DEPOSIT": "Tiền gửi",
    "EQUITY": "Cổ phiếu",
    "ETF": "ETF VN30",
    "BOND_FUND": "Quỹ trái phiếu",
    "GOVERNMENT_BOND_REFERENCE": "TPCP tham chiếu",
}

STATUS_LABELS = {
    "SELECTED_INTERNAL": "Được chọn nội bộ",
    "ELIGIBLE_NOT_SELECTED": "Đủ điều kiện",
    "REJECTED": "Bị loại",
}


def _register_font() -> str:
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSansCondensed.ttf"),
    ]
    for path in candidates:
        if path.exists():
            if "AQUnicode" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("AQUnicode", str(path)))
            return "AQUnicode"
    return "Helvetica"


def _money(value: int | float) -> str:
    return f"{value:,.0f} VND".replace(",", ".")


def _percent(value: int | float) -> str:
    return f"{value * 100:.2f}%"


def generate_recommendation_pdf(released: ReleasedOutput) -> bytes:
    font = _register_font()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=17 * mm,
        rightMargin=17 * mm,
        topMargin=18 * mm,
        bottomMargin=17 * mm,
        title=f"Monopoly AI Portfolio Lab - {released.recommendation_id}",
        author="AQ2026-176 Monopoly",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleUnicode",
        parent=styles["Title"],
        fontName=font,
        fontSize=22,
        leading=27,
        textColor=colors.HexColor("#102521"),
        alignment=TA_LEFT,
        spaceAfter=8,
    )
    heading = ParagraphStyle(
        "HeadingUnicode",
        parent=styles["Heading2"],
        fontName=font,
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#245B4E"),
        spaceBefore=12,
        spaceAfter=7,
    )
    body = ParagraphStyle(
        "BodyUnicode",
        parent=styles["BodyText"],
        fontName=font,
        fontSize=8.5,
        leading=12.5,
        textColor=colors.HexColor("#34463F"),
    )
    small = ParagraphStyle(
        "SmallUnicode",
        parent=body,
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor("#62736C"),
    )
    centered = ParagraphStyle(
        "CenteredUnicode",
        parent=small,
        alignment=TA_CENTER,
    )

    story: list = [
        Paragraph("MONOPOLY AI PORTFOLIO LAB", title),
        Paragraph(
            "Báo cáo so sánh phương án đa tài sản - nội dung nghiên cứu và giáo dục",
            heading,
        ),
        Table(
            [
                ["Recommendation ID", released.recommendation_id],
                ["Legal mode", str(released.legal_operating_mode)],
                ["Release type", str(released.output_release_type)],
                ["Data snapshot", released.data_snapshot],
                ["Model version", released.model_version],
            ],
            colWidths=[42 * mm, 128 * mm],
            style=TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E5EFEA")),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#245B4E")),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C8D5CF")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            ),
        ),
        Spacer(1, 5 * mm),
    ]

    if released.financial_plan:
        plan = released.financial_plan
        story.extend(
            [
                Paragraph("1. Kế hoạch tài chính", heading),
                Table(
                    [
                        ["Vốn khả dụng", _money(plan.investable_capital)],
                        ["Quỹ dự phòng", _money(plan.emergency_reserve)],
                        ["Nghĩa vụ gần hạn", _money(plan.near_term_liabilities)],
                        [
                            "Bucket thanh khoản tức thời",
                            _money(plan.immediate_liquidity_bucket),
                        ],
                    ],
                    colWidths=[85 * mm, 85 * mm],
                    style=TableStyle(
                        [
                            ("FONTNAME", (0, 0), (-1, -1), font),
                            ("FONTSIZE", (0, 0), (-1, -1), 8),
                            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [
                                colors.white,
                                colors.HexColor("#F5F5EF"),
                            ]),
                            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D9DFDA")),
                            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                            ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ]
                    ),
                ),
            ]
        )

    story.append(Paragraph("2. So sánh phương án", heading))
    comparison_rows = [["Phương án", "LN kỳ vọng", "Biến động", "VaR 95%", "Thanh khoản", "Phức tạp"]]
    for scenario in released.scenarios:
        scenario_role = (
            "Khuyến nghị"
            if scenario.recommendation_role == "RECOMMENDED"
            else "Thay thế" if scenario.recommendation_role == "ALTERNATIVE" else None
        )
        comparison_rows.append(
            [
                f"{scenario.name} ({scenario_role})"
                if scenario_role
                else scenario.name,
                _percent(scenario.expected_return_rate),
                _percent(scenario.risk_metrics.annualized_volatility),
                _money(scenario.risk_metrics.var_95_amount),
                f"{scenario.risk_metrics.liquidity_score:.1f}/100",
                f"{scenario.operational_complexity_score:.1f}/100",
            ]
        )
    story.append(
        Table(
            comparison_rows,
            colWidths=[45 * mm, 23 * mm, 23 * mm, 30 * mm, 25 * mm, 24 * mm],
            repeatRows=1,
            style=TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#102521")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C8D5CF")),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            ),
        )
    )

    for index, scenario in enumerate(released.scenarios, start=1):
        scenario_role = (
            "Khuyến nghị"
            if scenario.recommendation_role == "RECOMMENDED"
            else "Thay thế" if scenario.recommendation_role == "ALTERNATIVE" else None
        )
        allocation_rows = [["Nhóm tài sản", "Số tiền", "Tỷ trọng", "LN kỳ vọng", "Chi phí"]]
        for allocation in scenario.allocations:
            asset_class = str(allocation.asset_class)
            allocation_rows.append(
                [
                    ASSET_LABELS.get(asset_class, asset_class),
                    _money(allocation.amount),
                    _percent(allocation.weight),
                    _money(allocation.expected_return_amount),
                    _money(allocation.transaction_cost_amount),
                ]
            )
        allocation_table = Table(
            allocation_rows,
            colWidths=[46 * mm, 38 * mm, 25 * mm, 36 * mm, 25 * mm],
            repeatRows=1,
            style=TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font),
                    ("FONTSIZE", (0, 0), (-1, -1), 6.8),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5EFEA")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#245B4E")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D2DAD5")),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            ),
        )
        story.append(
            KeepTogether(
                [
                    Paragraph(
                        f"2.{index} {escape(scenario.name)}"
                        + (f" — {escape(scenario_role)}" if scenario_role else ""),
                        heading,
                    ),
                    Paragraph(escape(scenario.objective_description), body),
                    Paragraph(
                        escape(
                            f"Độ phức tạp vận hành {scenario.operational_complexity_score:.1f}/100 — "
                            f"{scenario.complexity_breakdown.distinct_product_count} sản phẩm tại "
                            f"{scenario.complexity_breakdown.distinct_provider_count} tổ chức; "
                            f"{scenario.complexity_breakdown.fragment_product_count} phần phân bổ vụn; "
                            f"config {scenario.complexity_config_version}."
                        ),
                        small,
                    ),
                    Spacer(1, 2 * mm),
                    allocation_table,
                ]
            )
        )
        if scenario.allocation_explanations:
            story.append(Paragraph("Lý do theo từng nhóm tài sản", body))
            for detail in scenario.allocation_explanations:
                asset_class = str(detail.asset_class)
                label = ASSET_LABELS.get(asset_class, asset_class)
                story.append(
                    Paragraph(
                        (
                            f"<b>{escape(label)}</b> — "
                            f"{escape(detail.portfolio_role)} "
                            f"{escape(detail.allocation_reason)} "
                            f"<b>Điểm giới hạn:</b> {escape(detail.limiting_factor)} "
                            f"<b>Khi tính lại:</b> {escape(detail.change_trigger)}"
                        ),
                        small,
                    )
                )

    story.extend([PageBreak(), Paragraph("3. Giải thích chọn và loại sản phẩm", heading)])
    selected_rows = [["Sản phẩm", "Nhóm", "Trạng thái", "Reason code"]]
    for decision in released.selection_decisions:
        selected_rows.append(
            [
                Paragraph(
                    (
                        f"<b>{escape(decision.product_name)}</b><br/>"
                        f"{escape(decision.provider or '')}<br/>"
                        f"<font color='#718079'>{escape(decision.product_id)}</font>"
                        if decision.product_name
                        else escape(decision.product_id)
                    ),
                    small,
                ),
                Paragraph(
                    escape(
                        ASSET_LABELS.get(
                            str(decision.asset_class),
                            str(decision.asset_class),
                        )
                    ),
                    small,
                ),
                Paragraph(
                    escape(STATUS_LABELS.get(str(decision.status), str(decision.status))),
                    small,
                ),
                Paragraph("<br/>".join(map(escape, decision.reason_codes)), small),
            ]
        )
    story.append(
        Table(
            selected_rows,
            colWidths=[50 * mm, 27 * mm, 42 * mm, 51 * mm],
            repeatRows=1,
            style=TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font),
                    ("FONTSIZE", (0, 0), (-1, -1), 6.5),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#102521")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D2DAD5")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            ),
        )
    )

    story.append(
        KeepTogether(
            [
            Paragraph("4. Giả định và cảnh báo", heading),
            *[
                Paragraph(f"- {escape(item)}", body)
                for item in [*released.assumptions, *released.warnings]
            ],
            Spacer(1, 4 * mm),
            Paragraph(
                "Báo cáo này không phải khuyến nghị mua/bán, không cam kết lợi nhuận "
                "và không tạo lệnh giao dịch. Người dùng phải xác nhận trước mọi quyết định.",
                centered,
            ),
            ]
        )
    )

    def footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont(font, 7)
        canvas.setFillColor(colors.HexColor("#6A7A73"))
        canvas.drawString(17 * mm, 9 * mm, "AQ2026-176 - Monopoly AI Portfolio Lab")
        canvas.drawRightString(193 * mm, 9 * mm, f"Trang {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
