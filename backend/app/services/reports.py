from __future__ import annotations

from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.app.models import ReleasedOutput
from backend.app.services.investment_memo import build_investment_memo


BRAND_DARK = colors.HexColor("#102521")
BRAND_GREEN = colors.HexColor("#1F6655")
BRAND_MINT = colors.HexColor("#E7F0EC")
BRAND_GOLD = colors.HexColor("#D5A93F")
INK = colors.HexColor("#243A33")
MUTED = colors.HexColor("#65766F")
LINE = colors.HexColor("#CED9D4")
PAPER = colors.HexColor("#F7F8F5")
WARNING_BG = colors.HexColor("#FFF5DF")
REJECT_BG = colors.HexColor("#FBEAE5")

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
    "SELECTED_INTERNAL": "Được chọn",
    "ELIGIBLE_NOT_SELECTED": "Đủ điều kiện - chưa chọn",
    "REJECTED": "Bị loại",
}

MODE_LABELS = {
    "LICENSED_ADVISORY": "Advisor - tư vấn có xác minh",
    "RESEARCH_EDUCATION": "Nghiên cứu và giáo dục",
}

RELEASE_LABELS = {
    "ADVISORY_SELECTED": "Phương án sản phẩm được kiểm duyệt",
    "COMPARE_ONLY": "So sánh theo nhóm tài sản",
    "BLOCKED": "Chưa đủ điều kiện phát hành",
}

MONITORING_LABELS = {
    "ADDITIONAL_CAPITAL": "Nạp thêm tiền",
    "WITHDRAWAL_REQUEST": "Yêu cầu rút vốn",
    "GOAL_OR_HORIZON_CHANGE": "Mục tiêu hoặc thời hạn thay đổi",
    "RISK_PROFILE_CHANGE": "Khả năng chịu rủi ro thay đổi",
    "MATERIAL_PRODUCT_DATA_CHANGE": "Dữ liệu sản phẩm thay đổi đáng kể",
    "PORTFOLIO_DRIFT": "Danh mục lệch cơ cấu mục tiêu",
    "USER_REQUEST": "Người dùng yêu cầu phân tích lại",
}

WITHDRAWAL_LABELS = {
    "USE_CASH": "Sử dụng tiền mặt",
    "BREAK_DEPOSIT": "Tất toán tiền gửi",
    "SELL_HIGH_LIQUIDITY_ASSETS": "Bán tài sản thanh khoản cao",
    "PROPORTIONAL_SALE": "Bán theo tỷ lệ",
}


def _register_fonts() -> tuple[str, str]:
    candidates = [
        (
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
    ]
    for regular_path, bold_path in candidates:
        if regular_path.exists():
            if "AQUnicode" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("AQUnicode", str(regular_path)))
            if bold_path.exists() and "AQUnicode-Bold" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("AQUnicode-Bold", str(bold_path)))
            bold_name = "AQUnicode-Bold" if bold_path.exists() else "AQUnicode"
            pdfmetrics.registerFontFamily(
                "AQUnicode",
                normal="AQUnicode",
                bold=bold_name,
                italic="AQUnicode",
                boldItalic=bold_name,
            )
            return "AQUnicode", bold_name
    return "Helvetica", "Helvetica-Bold"


def _clean(value: Any) -> str:
    return (
        str(value if value is not None else "")
        .replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u00a0", " ")
    )


def _html(value: Any) -> str:
    return escape(_clean(value))


def _money(value: int | float) -> str:
    return f"{round(value):,}".replace(",", ".") + " đ"


def _percent(value: int | float) -> str:
    return f"{value * 100:.2f}%".replace(".", ",")


def _date_time(value: Any) -> str:
    if value is None:
        return "Chưa có"
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y %H:%M")
    return _clean(value)


def _asset_label(value: Any) -> str:
    key = getattr(value, "value", value)
    return ASSET_LABELS.get(str(key), str(key))


def _styles(font: str, bold_font: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_label": ParagraphStyle(
            "CoverLabel",
            parent=base["Normal"],
            fontName=bold_font,
            fontSize=8,
            leading=10,
            textColor=BRAND_GREEN,
            spaceAfter=4,
        ),
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName=bold_font,
            fontSize=24,
            leading=29,
            textColor=BRAND_DARK,
            alignment=TA_LEFT,
            spaceAfter=5,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontName=font,
            fontSize=10,
            leading=14,
            textColor=MUTED,
            spaceAfter=9,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName=bold_font,
            fontSize=17,
            leading=21,
            textColor=BRAND_DARK,
            spaceBefore=4,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName=bold_font,
            fontSize=12,
            leading=15,
            textColor=BRAND_GREEN,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontName=bold_font,
            fontSize=9.5,
            leading=12,
            textColor=BRAND_DARK,
            spaceBefore=7,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName=font,
            fontSize=8.2,
            leading=11.7,
            textColor=INK,
            spaceAfter=3,
            allowWidows=0,
            allowOrphans=0,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName=font,
            fontSize=7,
            leading=9.5,
            textColor=MUTED,
            wordWrap="CJK",
        ),
        "small_bold": ParagraphStyle(
            "SmallBold",
            parent=base["BodyText"],
            fontName=bold_font,
            fontSize=7,
            leading=9.5,
            textColor=INK,
            wordWrap="CJK",
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["Normal"],
            fontName=bold_font,
            fontSize=7,
            leading=9,
            textColor=colors.white,
            wordWrap="CJK",
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            parent=base["Normal"],
            fontName=font,
            fontSize=7.2,
            leading=9.5,
            textColor=INK,
            wordWrap="CJK",
        ),
        "table_cell_right": ParagraphStyle(
            "TableCellRight",
            parent=base["Normal"],
            fontName=font,
            fontSize=7.2,
            leading=9.5,
            textColor=INK,
            alignment=TA_RIGHT,
            wordWrap="CJK",
        ),
        "kpi_label": ParagraphStyle(
            "KpiLabel",
            parent=base["Normal"],
            fontName=font,
            fontSize=6.5,
            leading=8,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "kpi_value": ParagraphStyle(
            "KpiValue",
            parent=base["Normal"],
            fontName=bold_font,
            fontSize=11,
            leading=14,
            textColor=BRAND_DARK,
            alignment=TA_CENTER,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName=font,
            fontSize=8,
            leading=11.2,
            leftIndent=9,
            firstLineIndent=-7,
            textColor=INK,
            spaceAfter=2,
            wordWrap="CJK",
        ),
        "source": ParagraphStyle(
            "Source",
            parent=base["BodyText"],
            fontName=font,
            fontSize=6.6,
            leading=9,
            leftIndent=9,
            firstLineIndent=-7,
            textColor=MUTED,
            spaceAfter=2,
            wordWrap="CJK",
        ),
        "disclaimer": ParagraphStyle(
            "Disclaimer",
            parent=base["BodyText"],
            fontName=font,
            fontSize=7,
            leading=9.5,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
    }


def _paragraph(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_html(text), style)


def _rich(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def _bullet_items(
    values: Iterable[Any],
    style: ParagraphStyle,
    *,
    color: str = "#1F6655",
) -> list[Paragraph]:
    return [
        _rich(
            f"<font color='{color}'><b>•</b></font>&nbsp; {_html(value)}",
            style,
        )
        for value in values
        if _clean(value).strip()
    ]


def _section_title(
    number: str,
    title: str,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    return [
        Spacer(1, 2 * mm),
        HRFlowable(width="100%", thickness=0.7, color=LINE, spaceAfter=5),
        _rich(
            f"<font color='#D5A93F'>{_html(number)}</font>&nbsp;&nbsp;{_html(title)}",
            styles["h1"],
        ),
    ]


def _base_table(
    rows: list[list[Any]],
    widths: list[float],
    font: str,
    *,
    header: bool = True,
    repeat_rows: int = 1,
) -> Table:
    commands: list[tuple] = [
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, PAPER]),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ]
        )
    return Table(
        rows,
        colWidths=widths,
        repeatRows=repeat_rows if header else 0,
        splitByRow=1,
        splitInRow=1,
        style=TableStyle(commands),
    )


def _metadata_table(
    released: ReleasedOutput,
    styles: dict[str, ParagraphStyle],
    font: str,
) -> Table:
    release_key = str(released.output_release_type)
    mode_key = str(released.legal_operating_mode)
    rows = [
        [
            _paragraph("Mã báo cáo", styles["small_bold"]),
            _paragraph(released.recommendation_id, styles["small"]),
        ],
        [
            _paragraph("Chế độ", styles["small_bold"]),
            _paragraph(MODE_LABELS.get(mode_key, mode_key), styles["small"]),
        ],
        [
            _paragraph("Phạm vi phát hành", styles["small_bold"]),
            _paragraph(RELEASE_LABELS.get(release_key, release_key), styles["small"]),
        ],
        [
            _paragraph("Thời điểm phát hành", styles["small_bold"]),
            _paragraph(_date_time(released.released_at), styles["small"]),
        ],
        [
            _paragraph("Dữ liệu / mô hình", styles["small_bold"]),
            _paragraph(
                f"{released.data_snapshot} | {released.model_version}",
                styles["small"],
            ),
        ],
    ]
    table = Table(rows, colWidths=[44 * mm, 126 * mm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("BACKGROUND", (0, 0), (0, -1), BRAND_MINT),
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _financial_plan_story(
    released: ReleasedOutput,
    styles: dict[str, ParagraphStyle],
    font: str,
) -> list[Any]:
    if not released.financial_plan:
        return []
    plan = released.financial_plan
    rows = [
        [
            _paragraph("Tổng tài sản", styles["table_cell"]),
            _paragraph(_money(plan.total_assets), styles["table_cell_right"]),
            _paragraph("Quỹ dự phòng", styles["table_cell"]),
            _paragraph(_money(plan.emergency_reserve), styles["table_cell_right"]),
        ],
        [
            _paragraph("Nghĩa vụ gần hạn", styles["table_cell"]),
            _paragraph(_money(plan.near_term_liabilities), styles["table_cell_right"]),
            _paragraph("Vốn khả dụng", styles["table_cell"]),
            _paragraph(_money(plan.investable_capital), styles["table_cell_right"]),
        ],
        [
            _paragraph("Thanh khoản tức thời", styles["table_cell"]),
            _paragraph(_money(plan.immediate_liquidity_bucket), styles["table_cell_right"]),
            _paragraph("Năng lực dài hạn", styles["table_cell"]),
            _paragraph(_money(plan.long_term_capacity), styles["table_cell_right"]),
        ],
    ]
    table = Table(rows, colWidths=[42 * mm, 43 * mm, 42 * mm, 43 * mm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, PAPER]),
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return [
        *_section_title("01", "Nền tảng kế hoạch tài chính", styles),
        table,
        Spacer(1, 2 * mm),
        *_bullet_items(plan.assumptions, styles["small"]),
    ]


def _comparison_story(
    released: ReleasedOutput,
    styles: dict[str, ParagraphStyle],
    font: str,
) -> list[Any]:
    headers = [
        "Phương án",
        "Lợi nhuận kỳ vọng",
        "Biến động",
        "VaR 95%",
        "Thanh khoản",
    ]
    rows: list[list[Any]] = [
        [_paragraph(item, styles["table_header"]) for item in headers]
    ]
    for scenario in released.scenarios:
        role = (
            "Khuyến nghị"
            if scenario.recommendation_role == "RECOMMENDED"
            else "Lựa chọn thay thế"
            if scenario.recommendation_role == "ALTERNATIVE"
            else "So sánh"
        )
        rows.append(
            [
                _rich(
                    f"<b>{_html(scenario.name)}</b><br/>"
                    f"<font color='#65766F'>{_html(role)}</font>",
                    styles["table_cell"],
                ),
                _rich(
                    f"<b>{_html(_percent(scenario.expected_return_rate))}</b><br/>"
                    f"{_html(_money(scenario.expected_return_amount))}/năm",
                    styles["table_cell_right"],
                ),
                _paragraph(
                    _percent(scenario.risk_metrics.annualized_volatility),
                    styles["table_cell_right"],
                ),
                _paragraph(
                    _money(scenario.risk_metrics.var_95_amount),
                    styles["table_cell_right"],
                ),
                _paragraph(
                    f"{scenario.risk_metrics.liquidity_score:.1f}/100",
                    styles["table_cell_right"],
                ),
            ]
        )
    return [
        *_section_title("02", "So sánh ba phương án", styles),
        _base_table(
            rows,
            [48 * mm, 38 * mm, 27 * mm, 31 * mm, 26 * mm],
            font,
        ),
        Spacer(1, 2 * mm),
        _paragraph(
            "Lợi nhuận kỳ vọng, biến động, VaR và stress test là đầu ra mô hình, "
            "không phải cam kết. Hãy đọc cùng điều kiện thực hiện và giả định ở cuối báo cáo.",
            styles["small"],
        ),
    ]


def _kpi_table(
    scenario: Any,
    styles: dict[str, ParagraphStyle],
    font: str,
) -> Table:
    values = [
        ("Vốn phân bổ", _money(scenario.investable_capital)),
        ("LN kỳ vọng", _percent(scenario.expected_return_rate)),
        ("Biến động", _percent(scenario.risk_metrics.annualized_volatility)),
        ("VaR 95%", _money(scenario.risk_metrics.var_95_amount)),
        ("Thanh khoản", f"{scenario.risk_metrics.liquidity_score:.1f}/100"),
    ]
    table = Table(
        [
            [_paragraph(label, styles["kpi_label"]) for label, _ in values],
            [_paragraph(value, styles["kpi_value"]) for _, value in values],
        ],
        colWidths=[34 * mm] * 5,
    )
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("BACKGROUND", (0, 0), (-1, -1), PAPER),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
                ("TOPPADDING", (0, 0), (-1, 0), 5),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
                ("TOPPADDING", (0, 1), (-1, 1), 1),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
            ]
        )
    )
    return table


def _allocation_table(
    scenario: Any,
    styles: dict[str, ParagraphStyle],
    font: str,
) -> Table:
    rows: list[list[Any]] = [
        [
            _paragraph("Sản phẩm / nhóm tài sản", styles["table_header"]),
            _paragraph("Phân bổ", styles["table_header"]),
            _paragraph("Lợi nhuận kỳ vọng", styles["table_header"]),
            _paragraph("Chi phí / thanh khoản", styles["table_header"]),
        ]
    ]
    for allocation in scenario.allocations:
        product_name = getattr(allocation, "product_name", None)
        provider = getattr(allocation, "provider", None)
        title = product_name or _asset_label(allocation.asset_class)
        detail_lines = [_asset_label(allocation.asset_class)]
        if provider:
            detail_lines.append(provider)
        reference_price = getattr(allocation, "reference_price", None)
        estimated_units = getattr(allocation, "estimated_units", None)
        if reference_price:
            detail_lines.append(f"Giá tham chiếu: {_money(reference_price)}")
        if estimated_units is not None:
            detail_lines.append(f"Số lượng minh họa: {estimated_units:,}".replace(",", "."))
        expected_return_rate = getattr(allocation, "expected_return_rate", None)
        if expected_return_rate is None:
            expected_return_rate = (
                allocation.expected_return_amount / allocation.amount
                if allocation.amount
                else 0
            )
        rows.append(
            [
                _rich(
                    f"<b>{_html(title)}</b><br/>"
                    + "<br/>".join(
                        f"<font color='#65766F'>{_html(item)}</font>"
                        for item in detail_lines
                    ),
                    styles["table_cell"],
                ),
                _rich(
                    f"<b>{_html(_money(allocation.amount))}</b><br/>"
                    f"{_html(_percent(allocation.weight))}",
                    styles["table_cell_right"],
                ),
                _rich(
                    f"{_html(_percent(expected_return_rate))} / năm<br/>"
                    f"{_html(_money(allocation.expected_return_amount))} / năm",
                    styles["table_cell_right"],
                ),
                _rich(
                    f"{_html(_money(allocation.transaction_cost_amount))}<br/>"
                    f"{getattr(allocation, 'liquidity_score', scenario.risk_metrics.liquidity_score):.0f}/100",
                    styles["table_cell_right"],
                ),
            ]
        )
    return _base_table(
        rows,
        [66 * mm, 34 * mm, 40 * mm, 30 * mm],
        font,
    )


def _allocation_explanation_story(
    scenario: Any,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    story: list[Any] = []
    if not scenario.allocation_explanations:
        return story
    story.append(_paragraph("Vì sao hình thành tỷ trọng", styles["h2"]))
    for detail in scenario.allocation_explanations:
        name = detail.product_name or _asset_label(detail.asset_class)
        story.extend(
            [
                KeepTogether(
                    [
                        _rich(
                            f"<b>{_html(name)}</b> - {_html(_money(detail.amount))} "
                            f"({_html(_percent(detail.weight))})",
                            styles["h3"],
                        ),
                        _rich(
                            f"<b>Vai trò:</b> {_html(detail.portfolio_role)}",
                            styles["body"],
                        ),
                        _rich(
                            f"<b>Lý do chọn và hình thành tỷ trọng:</b> "
                            f"{_html(detail.allocation_reason)}",
                            styles["body"],
                        ),
                    ]
                ),
                _rich(
                    f"<b>Lợi nhuận và rủi ro:</b> "
                    f"{_html(detail.expected_return_and_risk)}",
                    styles["body"],
                ),
                _rich(
                    f"<b>Chi phí và thanh khoản:</b> "
                    f"{_html(detail.cost_and_liquidity)}",
                    styles["body"],
                ),
                _rich(
                    f"<b>Kịch bản bất lợi:</b> {_html(detail.adverse_scenario)}",
                    styles["body"],
                ),
                _rich(
                    f"<b>Giới hạn đang chi phối:</b> {_html(detail.limiting_factor)}",
                    styles["body"],
                ),
                _rich(
                    f"<b>Khi nào cần tính lại:</b> {_html(detail.change_trigger)}",
                    styles["body"],
                ),
            ]
        )
        if detail.execution_conditions:
            story.append(_paragraph("Điều kiện thực hiện", styles["small_bold"]))
            story.extend(_bullet_items(detail.execution_conditions, styles["small"]))
        if detail.data_evidence:
            story.append(_paragraph("Dữ liệu và bằng chứng", styles["small_bold"]))
            story.extend(_bullet_items(detail.data_evidence, styles["source"]))
        if detail.result_sensitive_assumptions:
            story.append(_paragraph("Giả định có thể làm thay đổi kết quả", styles["small_bold"]))
            story.extend(
                _bullet_items(
                    detail.result_sensitive_assumptions,
                    styles["small"],
                    color="#D5A93F",
                )
            )
    return story


def _deposit_story(
    scenario: Any,
    styles: dict[str, ParagraphStyle],
    font: str,
) -> list[Any]:
    if not scenario.deposit_implementation:
        return []
    rows: list[list[Any]] = [
        [
            _paragraph("Ngân hàng và sản phẩm", styles["table_header"]),
            _paragraph("Kỳ hạn / lãi suất", styles["table_header"]),
            _paragraph("Số vốn / lãi kỳ hạn", styles["table_header"]),
            _paragraph("Điều kiện và nguồn", styles["table_header"]),
        ]
    ]
    for item in scenario.deposit_implementation:
        conditions = "<br/>".join(f"• {_html(value)}" for value in item.conditions)
        rows.append(
            [
                _rich(
                    f"<b>{_html(item.bank)}</b><br/>{_html(item.product_name)}",
                    styles["table_cell"],
                ),
                _rich(
                    f"<b>{_html(item.tenor_months or 'N/A')} tháng</b><br/>"
                    f"{_html(_percent(item.annual_rate))}/năm<br/>"
                    f"{_html(item.selected_segment or 'Phân khúc phổ thông')}",
                    styles["table_cell"],
                ),
                _rich(
                    f"<b>{_html(_money(item.amount))}</b><br/>"
                    f"Lãi kỳ hạn: {_html(_money(item.term_interest_amount or 0))}<br/>"
                    f"Đáo hạn: {_html(_money(item.maturity_amount or item.amount))}",
                    styles["table_cell_right"],
                ),
                _rich(
                    f"{conditions}<br/><font color='#65766F'>"
                    f"{_html(item.source_reference)}<br/>"
                    f"{_html(_date_time(item.data_timestamp))}</font>",
                    styles["small"],
                ),
            ]
        )
    return [
        _paragraph("Hướng dẫn triển khai tiền gửi", styles["h2"]),
        _paragraph(
            "Các con số dưới đây là điều kiện cụ thể đã đi qua optimizer. "
            "Lãi suất phải được xác nhận lại tại ngân hàng trước khi thực hiện.",
            styles["body"],
        ),
        _base_table(
            rows,
            [41 * mm, 31 * mm, 43 * mm, 55 * mm],
            font,
        ),
    ]


def _risk_story(
    scenario: Any,
    styles: dict[str, ParagraphStyle],
    font: str,
) -> list[Any]:
    risk = scenario.risk_metrics
    rows = [
        [
            _paragraph("Chỉ số", styles["table_header"]),
            _paragraph("Kết quả", styles["table_header"]),
            _paragraph("Cách đọc", styles["table_header"]),
        ],
        [
            _paragraph("VaR 95%", styles["table_cell"]),
            _paragraph(_money(risk.var_95_amount), styles["table_cell_right"]),
            _paragraph(
                "Mức lỗ mô hình tại ngưỡng 95%; không phải mức lỗ tối đa.",
                styles["table_cell"],
            ),
        ],
        [
            _paragraph("CVaR 95%", styles["table_cell"]),
            _paragraph(_money(risk.cvar_95_amount), styles["table_cell_right"]),
            _paragraph(
                "Mức lỗ trung bình của nhóm kịch bản xấu hơn ngưỡng VaR.",
                styles["table_cell"],
            ),
        ],
        [
            _paragraph("Trần rủi ro", styles["table_cell"]),
            _paragraph(_percent(risk.risk_ceiling), styles["table_cell_right"]),
            _paragraph(
                "Đạt" if risk.within_risk_ceiling else "Không đạt",
                styles["table_cell"],
            ),
        ],
        [
            _paragraph("Tập trung lớn nhất", styles["table_cell"]),
            _paragraph(
                _percent(risk.largest_asset_class_weight),
                styles["table_cell_right"],
            ),
            _paragraph(
                f"HHI {risk.concentration_hhi:.3f}; tỷ trọng cao làm tăng phụ thuộc vào một nhóm.",
                styles["table_cell"],
            ),
        ],
    ]
    stress_rows: list[list[Any]] = [
        [
            _paragraph("Kịch bản bất lợi", styles["table_header"]),
            _paragraph("Tác động ước tính", styles["table_header"]),
            _paragraph("Giả định", styles["table_header"]),
        ]
    ]
    for item in risk.stress_tests:
        stress_rows.append(
            [
                _paragraph(item.scenario_name, styles["table_cell"]),
                _rich(
                    f"<b>{_html(_money(item.estimated_change_amount))}</b><br/>"
                    f"{_html(_percent(item.estimated_change_pct))}",
                    styles["table_cell_right"],
                ),
                _paragraph(item.assumptions, styles["table_cell"]),
            ]
        )
    story: list[Any] = [
        _paragraph("Rủi ro và kịch bản bất lợi", styles["h2"]),
        _base_table(
            rows,
            [37 * mm, 35 * mm, 98 * mm],
            font,
        ),
    ]
    if len(stress_rows) > 1:
        story.extend(
            [
                Spacer(1, 3 * mm),
                _base_table(
                    stress_rows,
                    [45 * mm, 36 * mm, 89 * mm],
                    font,
                ),
            ]
        )
    return story


def _scenario_story(
    scenario: Any,
    index: int,
    styles: dict[str, ParagraphStyle],
    font: str,
) -> list[Any]:
    role = (
        "PHƯƠNG ÁN KHUYẾN NGHỊ"
        if scenario.recommendation_role == "RECOMMENDED"
        else "LỰA CHỌN THAY THẾ"
        if scenario.recommendation_role == "ALTERNATIVE"
        else "PHƯƠNG ÁN SO SÁNH"
    )
    story: list[Any] = [
        PageBreak(),
        _paragraph(role, styles["cover_label"]),
        _rich(
            f"{index:02d}. {_html(scenario.name)}",
            styles["title"],
        ),
        _paragraph(scenario.objective_description, styles["subtitle"]),
        _kpi_table(scenario, styles, font),
        _paragraph("Phân bổ được phát hành", styles["h2"]),
        _allocation_table(scenario, styles, font),
        _rich(
            f"<b>Độ phức tạp vận hành:</b> "
            f"{scenario.operational_complexity_score:.1f}/100 - "
            f"{scenario.complexity_breakdown.distinct_product_count} sản phẩm, "
            f"{scenario.complexity_breakdown.distinct_provider_count} tổ chức, "
            f"{scenario.complexity_breakdown.distinct_maturity_count} kỳ hạn. "
            f"Chi phí mô hình {_html(_money(scenario.total_cost_amount))}.",
            styles["small"],
        ),
    ]
    story.extend(_deposit_story(scenario, styles, font))
    story.extend(_allocation_explanation_story(scenario, styles))
    story.extend(_risk_story(scenario, styles, font))
    if scenario.trade_offs:
        story.append(_paragraph("Đánh đổi cần chấp nhận", styles["h2"]))
        story.extend(
            _bullet_items(
                scenario.trade_offs,
                styles["body"],
                color="#D5A93F",
            )
        )
    return story


def _memo_section(
    title: str,
    values: Iterable[Any],
    styles: dict[str, ParagraphStyle],
    *,
    source: bool = False,
    color: str = "#1F6655",
) -> list[Any]:
    filtered = [value for value in values if _clean(value).strip()]
    if not filtered:
        return []
    return [
        _paragraph(title, styles["h3"]),
        *_bullet_items(
            filtered,
            styles["source"] if source else styles["body"],
            color=color,
        ),
    ]


def _advisor_memos_story(
    released: ReleasedOutput,
    styles: dict[str, ParagraphStyle],
    font: str,
) -> list[Any]:
    if str(released.output_release_type) != "ADVISORY_SELECTED":
        return []
    product_contexts: dict[str, tuple[Any, Any, Any | None]] = {}
    for scenario in released.scenarios:
        explanation_by_product = {
            detail.product_id: detail
            for detail in scenario.allocation_explanations
            if detail.product_id
        }
        for allocation in scenario.allocations:
            product_id = getattr(allocation, "product_id", None)
            if product_id and product_id not in product_contexts:
                product_contexts[product_id] = (
                    allocation,
                    scenario,
                    explanation_by_product.get(product_id),
                )
    if not product_contexts:
        return []

    story: list[Any] = [
        PageBreak(),
        _paragraph("PHỤ LỤC ADVISOR", styles["cover_label"]),
        _paragraph("Phân tích chi tiết từng sản phẩm", styles["title"]),
        _paragraph(
            "Mỗi luận điểm dưới đây nối trực tiếp tỷ trọng optimizer với dữ liệu sản phẩm, "
            "bối cảnh thị trường, rủi ro, lựa chọn thay thế và điều kiện triển khai. "
            "Nguồn và thời điểm được ghi rõ để người đọc có thể kiểm tra lại.",
            styles["subtitle"],
        ),
    ]
    for position, (allocation, scenario, explanation) in enumerate(
        product_contexts.values(),
        start=1,
    ):
        try:
            memo = build_investment_memo(
                allocation=allocation,
                explanation=explanation,
                scenario=scenario,
            )
        except Exception as exc:
            memo = None
            memo_error = (
                "Không thể dựng phần nghiên cứu mở rộng tại thời điểm xuất báo cáo: "
                f"{type(exc).__name__}. Các số liệu optimizer bên dưới vẫn được giữ nguyên."
            )
        else:
            memo_error = ""
        story.extend(
            [
                HRFlowable(width="100%", thickness=0.6, color=LINE, spaceBefore=8, spaceAfter=7),
                KeepTogether(
                    [
                        _rich(
                            f"<font color='#D5A93F'>{position:02d}</font>&nbsp;&nbsp;"
                            f"{_html(allocation.product_name)}",
                            styles["h2"],
                        ),
                        _rich(
                            f"<b>{_html(allocation.provider)}</b> | "
                            f"{_html(_asset_label(allocation.asset_class))} | "
                            f"Phương án {_html(scenario.name)}",
                            styles["small"],
                        ),
                        _rich(
                            f"<b>Phân bổ:</b> {_html(_money(allocation.amount))} "
                            f"({_html(_percent(allocation.weight))}) | "
                            f"<b>LN kỳ vọng:</b> "
                            f"{_html(_percent(allocation.expected_return_rate))}/năm | "
                            f"<b>Chi phí:</b> "
                            f"{_html(_money(allocation.transaction_cost_amount))}",
                            styles["body"],
                        ),
                    ]
                ),
            ]
        )
        if memo is None:
            story.append(_paragraph(memo_error, styles["body"]))
            continue
        evidence_title = {
            "DEPOSIT": "Lãi suất, kỳ hạn và điều kiện ngân hàng",
            "GOLD": "Giá trong nước, chart vàng thế giới và vĩ mô",
            "EQUITY": "Doanh nghiệp, định giá, kỹ thuật, tin tức và vĩ mô",
            "ETF": "Chỉ số, giá, kỹ thuật và bối cảnh thị trường",
            "BOND_FUND": "NAV, lãi suất và danh mục tài sản cơ sở",
            "CASH": "Bối cảnh thanh khoản",
        }.get(
            str(getattr(allocation.asset_class, "value", allocation.asset_class)),
            "Dữ liệu sản phẩm và bối cảnh thị trường",
        )
        story.extend(_memo_section("Luận điểm đầu tư", memo.thesis, styles))
        story.extend(_memo_section("Chuỗi chứng minh định lượng", memo.proof_chain, styles))
        story.extend(
            _memo_section(
                evidence_title,
                memo.market_evidence,
                styles,
            )
        )
        story.extend(_memo_section("Động lực có thể hỗ trợ", memo.catalysts, styles))
        story.extend(
            _memo_section(
                "Rủi ro và điều kiện vô hiệu luận điểm",
                memo.risks,
                styles,
                color="#A14B36",
            )
        )
        story.extend(_memo_section("Các lựa chọn thay thế", memo.alternatives, styles))
        story.extend(_memo_section("Điều kiện thực hiện", memo.implementation, styles))
        story.extend(
            _memo_section(
                "Nguồn và thời điểm cập nhật",
                memo.sources,
                styles,
                source=True,
            )
        )
        story.extend(
            _memo_section(
                "Giới hạn dữ liệu / giả định cần kiểm tra lại",
                memo.limitations,
                styles,
                color="#D5A93F",
            )
        )
    return story


def _monitoring_story(
    released: ReleasedOutput,
    styles: dict[str, ParagraphStyle],
    font: str,
) -> list[Any]:
    if not released.scenarios:
        return []
    scenario = released.scenarios[0]
    story: list[Any] = [
        PageBreak(),
        _paragraph("KẾ HOẠCH SAU KHI LỰA CHỌN", styles["cover_label"]),
        _paragraph("Theo dõi, tính lại và rút vốn", styles["title"]),
        _paragraph(
            "Hệ thống không dừng ở thời điểm phát hành phương án. Các thay đổi dưới đây "
            "là tín hiệu để tái định giá, kiểm tra lại ràng buộc và so sánh phương án mới.",
            styles["subtitle"],
        ),
    ]
    if scenario.monitoring_triggers:
        rows: list[list[Any]] = [
            [
                _paragraph("Sự kiện kích hoạt", styles["table_header"]),
                _paragraph("Điều kiện hiện tại", styles["table_header"]),
                _paragraph("Hành động", styles["table_header"]),
            ]
        ]
        for item in scenario.monitoring_triggers:
            rows.append(
                [
                    _paragraph(
                        MONITORING_LABELS.get(item.trigger_type, item.trigger_type),
                        styles["table_cell"],
                    ),
                    _rich(
                        f"{_html(item.trigger_condition)}<br/>"
                        f"<font color='#65766F'>{_html(item.current_reference)}</font>",
                        styles["table_cell"],
                    ),
                    _paragraph(item.action, styles["table_cell"]),
                ]
            )
        story.extend(
            [
                _paragraph("Khi nào hệ thống tính lại", styles["h2"]),
                _base_table(rows, [43 * mm, 61 * mm, 66 * mm], font),
            ]
        )
    if scenario.withdrawal_options:
        rows = [
            [
                _paragraph("Ưu tiên", styles["table_header"]),
                _paragraph("Phương án rút vốn", styles["table_header"]),
                _paragraph("Số tiền khả dụng", styles["table_header"]),
                _paragraph("Chi phí và tác động", styles["table_header"]),
            ]
        ]
        for item in sorted(scenario.withdrawal_options, key=lambda value: value.priority):
            conditions = "; ".join(item.conditions)
            rows.append(
                [
                    _paragraph(str(item.priority), styles["table_cell_right"]),
                    _rich(
                        f"<b>{_html(WITHDRAWAL_LABELS.get(item.option_type, item.title))}</b>"
                        f"<br/>{_html(conditions)}",
                        styles["table_cell"],
                    ),
                    _paragraph(_money(item.available_amount), styles["table_cell_right"]),
                    _rich(
                        f"<b>Chi phí:</b> {_html(item.estimated_cost)}<br/>"
                        f"<b>Ảnh hưởng:</b> {_html(item.portfolio_impact)}",
                        styles["table_cell"],
                    ),
                ]
            )
        story.extend(
            [
                _paragraph("Thứ tự xem xét khi cần rút vốn", styles["h2"]),
                _base_table(
                    rows,
                    [16 * mm, 52 * mm, 35 * mm, 67 * mm],
                    font,
                ),
            ]
        )
    return story


def _selection_story(
    released: ReleasedOutput,
    styles: dict[str, ParagraphStyle],
    font: str,
) -> list[Any]:
    if not released.selection_decisions:
        return []
    status_order = {
        "SELECTED_INTERNAL": 0,
        "ELIGIBLE_NOT_SELECTED": 1,
        "REJECTED": 2,
    }
    decisions = sorted(
        released.selection_decisions,
        key=lambda item: (
            status_order.get(str(item.status), 9),
            _asset_label(item.asset_class),
            item.product_name or item.product_id,
        ),
    )
    rows: list[list[Any]] = [
        [
            _paragraph("Sản phẩm", styles["table_header"]),
            _paragraph("Kết quả", styles["table_header"]),
            _paragraph("Vì sao được chọn hoặc bị loại", styles["table_header"]),
        ]
    ]
    for decision in decisions:
        status_key = str(decision.status)
        facts: list[str] = []
        if decision.expected_return is not None:
            facts.append(f"LN mô hình {_percent(decision.expected_return)}")
        if decision.volatility is not None:
            facts.append(f"biến động {_percent(decision.volatility)}")
        if decision.liquidity_score is not None:
            facts.append(f"thanh khoản {decision.liquidity_score}/100")
        if decision.minimum_investment is not None:
            facts.append(f"vốn tối thiểu {_money(decision.minimum_investment)}")
        reason_text = "<br/>".join(
            f"• {_html(reason)}" for reason in decision.reasons
        )
        codes = ", ".join(decision.reason_codes)
        rows.append(
            [
                _rich(
                    f"<b>{_html(decision.product_name or decision.product_id)}</b><br/>"
                    f"{_html(decision.provider or '')}<br/>"
                    f"<font color='#65766F'>{_html(_asset_label(decision.asset_class))} | "
                    f"{_html(decision.product_id)}</font>",
                    styles["table_cell"],
                ),
                _rich(
                    f"<b>{_html(STATUS_LABELS.get(status_key, status_key))}</b><br/>"
                    f"{_html('; '.join(facts))}",
                    styles["table_cell"],
                ),
                _rich(
                    f"{reason_text}<br/><font color='#65766F'>"
                    f"Mã kiểm soát: {_html(codes)}"
                    + (
                        f"<br/>Dữ liệu: {_html(_date_time(decision.data_timestamp))}"
                        if decision.data_timestamp
                        else ""
                    )
                    + "</font>",
                    styles["table_cell"],
                ),
            ]
        )
    table = _base_table(rows, [59 * mm, 38 * mm, 73 * mm], font)
    for row_index, decision in enumerate(decisions, start=1):
        status_key = str(decision.status)
        if status_key == "REJECTED":
            table.setStyle(
                TableStyle([("BACKGROUND", (0, row_index), (-1, row_index), REJECT_BG)])
            )
        elif status_key == "SELECTED_INTERNAL":
            table.setStyle(
                TableStyle([("BACKGROUND", (0, row_index), (-1, row_index), BRAND_MINT)])
            )
    return [
        PageBreak(),
        _paragraph("PHỤ LỤC KIỂM DUYỆT", styles["cover_label"]),
        _paragraph("Vì sao sản phẩm được chọn hoặc bị loại", styles["title"]),
        _paragraph(
            "Trạng thái phản ánh kết quả sau khi đồng thời xét vốn tối thiểu, thời gian "
            "khóa vốn, phân khúc khách hàng, rủi ro, thanh khoản, giới hạn tập trung và "
            "độ phức tạp vận hành. 'Đủ điều kiện - chưa chọn' không có nghĩa là sản phẩm xấu.",
            styles["subtitle"],
        ),
        table,
    ]


def _assumptions_story(
    released: ReleasedOutput,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    sources = list(
        dict.fromkeys(
            source
            for scenario in released.scenarios
            for source in scenario.source_summary
            if source
        )
    )
    result_assumptions = list(
        dict.fromkeys(
            item
            for scenario in released.scenarios
            for item in scenario.assumptions_that_change_result
            if item
        )
    )
    story: list[Any] = [
        PageBreak(),
        _paragraph("MINH BẠCH DỮ LIỆU", styles["cover_label"]),
        _paragraph("Nguồn, giả định và cảnh báo", styles["title"]),
    ]
    if sources:
        story.extend(
            [
                _paragraph("Nguồn và thời điểm cập nhật", styles["h2"]),
                *_bullet_items(sources, styles["source"]),
            ]
        )
    if result_assumptions:
        story.extend(
            [
                _paragraph("Những giả định có thể làm thay đổi kết quả", styles["h2"]),
                *_bullet_items(
                    result_assumptions,
                    styles["body"],
                    color="#D5A93F",
                ),
            ]
        )
    all_assumptions = list(dict.fromkeys([*released.assumptions]))
    if all_assumptions:
        story.extend(
            [
                _paragraph("Giả định mô hình", styles["h2"]),
                *_bullet_items(all_assumptions, styles["body"]),
            ]
        )
    if released.warnings:
        story.extend(
            [
                _paragraph("Cảnh báo bắt buộc", styles["h2"]),
                *_bullet_items(
                    released.warnings,
                    styles["body"],
                    color="#A14B36",
                ),
            ]
        )
    story.extend(
        [
            Spacer(1, 5 * mm),
            Table(
                [
                    [
                        _paragraph(
                            "Báo cáo không cam kết lợi nhuận và không tự tạo lệnh giao dịch. "
                            "Giá, lãi suất, NAV, điều kiện sản phẩm và tin tức phải được xác "
                            "nhận lại tại thời điểm thực hiện. Mọi quyết định cuối cùng cần "
                            "được người dùng xác nhận.",
                            styles["disclaimer"],
                        )
                    ]
                ],
                colWidths=[170 * mm],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), WARNING_BG),
                        ("BOX", (0, 0), (-1, -1), 0.5, BRAND_GOLD),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                ),
            ),
        ]
    )
    return story


def generate_recommendation_pdf(released: ReleasedOutput) -> bytes:
    font, bold_font = _register_fonts()
    styles = _styles(font, bold_font)
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=17 * mm,
        title=f"Monopoly AI - Báo cáo danh mục {released.recommendation_id}",
        subject="Báo cáo so sánh phương án và phân tích sản phẩm",
        author="Monopoly AI Portfolio Conversation Lab",
        creator="Monopoly AI Report Service",
        keywords="portfolio, advisory, risk, allocation, Vietnam",
        pageCompression=1,
    )

    release_key = str(released.output_release_type)
    mode_key = str(released.legal_operating_mode)
    story: list[Any] = [
        _paragraph("MONOPOLY AI · PORTFOLIO CONVERSATION LAB", styles["cover_label"]),
        _paragraph("Báo cáo phân bổ tài sản", styles["title"]),
        _paragraph(
            (
                "Báo cáo Advisor: tỷ trọng, sản phẩm, luận điểm, rủi ro, điều kiện thực "
                "hiện và bằng chứng được trình bày trong cùng một chuỗi kiểm chứng."
                if release_key == "ADVISORY_SELECTED"
                else "Báo cáo so sánh định lượng theo nhóm tài sản, phục vụ nghiên cứu "
                "và giáo dục tài chính."
            ),
            styles["subtitle"],
        ),
        _metadata_table(released, styles, font),
    ]
    if released.blocked_message:
        story.extend(
            [
                Spacer(1, 7 * mm),
                _paragraph("Kết quả chưa được phát hành", styles["h2"]),
                _paragraph(released.blocked_message, styles["body"]),
            ]
        )
    story.extend(_financial_plan_story(released, styles, font))
    if released.scenarios:
        story.extend(_comparison_story(released, styles, font))
        for index, scenario in enumerate(released.scenarios, start=1):
            story.extend(_scenario_story(scenario, index, styles, font))
        story.extend(_advisor_memos_story(released, styles, font))
        story.extend(_monitoring_story(released, styles, font))
    story.extend(_selection_story(released, styles, font))
    story.extend(_assumptions_story(released, styles))

    def header_footer(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(BRAND_GOLD)
        canvas.setLineWidth(0.7)
        canvas.line(20 * mm, height - 12 * mm, width - 20 * mm, height - 12 * mm)
        canvas.setFont(bold_font, 7)
        canvas.setFillColor(BRAND_DARK)
        canvas.drawString(20 * mm, height - 9 * mm, "MONOPOLY AI")
        canvas.setFont(font, 6.5)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(
            width - 20 * mm,
            height - 9 * mm,
            MODE_LABELS.get(mode_key, mode_key),
        )
        canvas.line(20 * mm, 11 * mm, width - 20 * mm, 11 * mm)
        canvas.drawString(
            20 * mm,
            7.5 * mm,
            f"{released.recommendation_id} · {released.data_snapshot}",
        )
        canvas.drawRightString(width - 20 * mm, 7.5 * mm, f"Trang {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    return buffer.getvalue()
