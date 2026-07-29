from __future__ import annotations

import io
import math
import re
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from threading import Lock
from time import monotonic
from typing import Any

import numpy as np

from backend.app.db.market_data import latest_observations, list_source_status


VNSTOCK_FREE_DOCS = "https://vnstocks.com/docs/vnstock"
CACHE_TTL_SECONDS = 30 * 60


@dataclass(slots=True)
class EquityResearchResult:
    ticker: str
    company_name: str
    company_facts: list[str] = field(default_factory=list)
    investment_thesis: list[str] = field(default_factory=list)
    price_facts: list[str] = field(default_factory=list)
    technical_facts: list[str] = field(default_factory=list)
    fundamental_facts: list[str] = field(default_factory=list)
    earnings_facts: list[str] = field(default_factory=list)
    valuation_facts: list[str] = field(default_factory=list)
    quality_facts: list[str] = field(default_factory=list)
    analyst_views: list[str] = field(default_factory=list)
    catalysts: list[str] = field(default_factory=list)
    risk_facts: list[str] = field(default_factory=list)
    news_facts: list[str] = field(default_factory=list)
    macro_facts: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    observed_at: datetime | None = None


_CACHE: dict[str, tuple[float, EquityResearchResult]] = {}
_CACHE_LOCK = Lock()


_COMPANY_FALLBACKS = {
    "ACB": ("Ngân hàng TMCP Á Châu", "Ngân hàng thương mại"),
    "FPT": ("Công ty Cổ phần FPT", "Công nghệ thông tin và dịch vụ số"),
    "GVR": ("Tập đoàn Công nghiệp Cao su Việt Nam - CTCP", "Cao su và khu công nghiệp"),
    "HPG": ("Công ty Cổ phần Tập đoàn Hòa Phát", "Thép và sản xuất công nghiệp"),
    "MWG": ("Công ty Cổ phần Đầu tư Thế Giới Di Động", "Bán lẻ"),
    "SHB": ("Ngân hàng TMCP Sài Gòn - Hà Nội", "Ngân hàng"),
    "VCB": ("Ngân hàng TMCP Ngoại thương Việt Nam", "Ngân hàng"),
    "VNM": ("Công ty Cổ phần Sữa Việt Nam", "Thực phẩm và đồ uống"),
}


# Các snapshot nghiên cứu dưới đây chỉ chứa dữ kiện đã gắn nguồn và ngày công bố.
# Giá/MA/RSI vẫn được lấy động từ chuỗi OHLCV; snapshot không được dùng như feed giao dịch.
_CURATED_RESEARCH: dict[str, dict[str, list[str]]] = {
    "ACB": {
        "investment_thesis": [
            (
                "Luận điểm chính là sự cân bằng giữa định giá, phục hồi lợi nhuận và chất lượng "
                "tài sản: ACB không được biện minh chỉ vì thuộc nhóm ngân hàng hay vì giá đang tăng."
            ),
            (
                "Hai tổ chức phân tích cùng đánh giá tích cực nhưng dùng giả định và giá mục tiêu "
                "khác nhau; hệ thống giữ riêng từng quan điểm thay vì tạo một con số đồng thuận giả."
            ),
        ],
        "earnings_facts": [
            (
                "SSI (12/05/2026) dự phóng lợi nhuận trước thuế 2026 khoảng 22,3 nghìn tỷ đồng, "
                "tăng 14,2% so với cùng kỳ; thu nhập phí tăng 14,4% và chi phí tín dụng giảm 35,7%."
            ),
            (
                "KAFI qua VOV (16/07/2026) dự phóng tăng trưởng tín dụng 17,2%, lợi nhuận trước "
                "thuế 22.618 tỷ đồng, tăng 15,8%; quý I đã hoàn thành khoảng 24% kế hoạch năm."
            ),
            (
                "KAFI giả định NIM quanh 2,95%, thu nhập ngoài lãi tăng 14% và chi phí tín dụng "
                "giảm về 0,45%; đây là các giả định cần theo dõi, không phải kết quả đã chắc chắn."
            ),
        ],
        "valuation_facts": [
            (
                "SSI (12/05/2026) ghi nhận ACB giao dịch khoảng 1,07 lần P/B 2026E, thấp hơn "
                "mức lịch sử dài hạn khoảng 1,5 lần; giá mục tiêu 27.500 đồng dựa trên P/B mục "
                "tiêu 1,3 lần."
            ),
            (
                "KAFI qua VOV (16/07/2026) đưa giá mục tiêu 29.500 đồng. Dải 27.500–29.500 đồng "
                "là hai kịch bản của hai tổ chức, không phải giá trị nội tại chắc chắn."
            ),
            (
                "Mức 31.000 đồng và khuyến nghị MUA trên trang SSI là báo cáo ngày 23/01/2025; "
                "không được dùng thay cho báo cáo SSI mới hơn ngày 12/05/2026."
            ),
        ],
        "quality_facts": [
            (
                "SSI đánh giá nợ xấu của ACB được duy trì quanh 1% và tỷ lệ bao phủ nợ xấu trên "
                "100%; đây là bộ đệm quan trọng khi môi trường tín dụng xấu đi."
            ),
            (
                "Mô hình bán lẻ/SME và chuẩn cấp tín dụng thận trọng hỗ trợ chất lượng tài sản, "
                "nhưng chiến lược mở rộng sang doanh nghiệp lớn và FDI cần được kiểm tra xem có "
                "làm giảm lợi suất tài sản hay tăng rủi ro tập trung hay không."
            ),
        ],
        "analyst_views": [
            (
                "SSI · 12/05/2026 · KHẢ QUAN · mục tiêu 12 tháng 27.500 đồng/cp · upside công bố "
                "20,9% · lợi suất cổ tức dự phóng khoảng 3%."
            ),
            (
                "KAFI (được VOV dẫn lại) · 16/07/2026 · KHẢ QUAN · mục tiêu 29.500 đồng/cp · "
                "upside công bố 29%."
            ),
        ],
        "catalysts": [
            (
                "Lợi nhuận trở lại tăng trưởng hai chữ số trong 2026, thu nhập phí phục hồi và "
                "chi phí tín dụng giảm nhanh hơn dự kiến."
            ),
            (
                "Thị trường định giá lại P/B khi chất lượng tài sản tiếp tục ổn định và chiến lược "
                "C1425 tạo tăng trưởng mà không làm suy giảm ROE."
            ),
        ],
        "risk_facts": [
            (
                "NIM thấp hơn giả định vì chi phí huy động tăng hoặc cạnh tranh lãi suất cho vay; "
                "khi đó tăng trưởng tín dụng cao chưa chắc chuyển thành tăng trưởng lợi nhuận."
            ),
            (
                "Nợ xấu hoặc chi phí tín dụng tăng trở lại; thu nhập phí và ACBS không đạt kế "
                "hoạch; chiến lược doanh nghiệp lớn/FDI làm giảm biên sinh lời."
            ),
            (
                "Luận điểm mất hiệu lực hoặc suy yếu nếu P/B không còn rẻ so với lịch sử, giá vượt đáng "
                "kể vùng mục tiêu trong khi dự báo lợi nhuận không được nâng, hoặc xu hướng kỹ "
                "thuật chuyển xấu với thanh khoản lớn."
            ),
        ],
        "sources": [
            (
                "SSI Research · 12/05/2026 · ACB (KHẢ QUAN, mục tiêu 27.500 đồng/cp): "
                "https://www.ssi.com.vn/khach-hang-ca-nhan/bao-cao-cong-ty?keyword=ACB&page=1"
            ),
            (
                "VOV dẫn báo cáo KAFI · 16/07/2026 · ACB mục tiêu 29.500 đồng/cp: "
                "https://vov.vn/thi-truong/mot-so-co-phieu-can-quan-tam-167-co-hoi-dau-tu-tiem-nang-voi-phr-va-acb-post1315618.vov"
            ),
        ],
    }
}


def _records(frame: Any) -> list[dict[str, Any]]:
    if frame is None:
        return []
    try:
        working = frame.copy()
        if hasattr(working, "columns"):
            working.columns = [
                "_".join(str(part) for part in column if str(part) not in {"", "None"})
                if isinstance(column, tuple)
                else str(column)
                for column in working.columns
            ]
        return [dict(row) for row in working.to_dict("records")]
    except Exception:
        try:
            return [dict(frame.to_dict())]
        except Exception:
            return []


def _key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def _normalized_record(row: dict[str, Any]) -> dict[str, Any]:
    return {_key(key): value for key, value in row.items()}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "nan", "none"}
    return True


def _pick(row: dict[str, Any], *candidates: str) -> Any:
    normalized = _normalized_record(row)
    for candidate in candidates:
        key = _key(candidate)
        if key in normalized and _present(normalized[key]):
            return normalized[key]
    for candidate in candidates:
        key = _key(candidate)
        for existing_key, value in normalized.items():
            if existing_key.endswith(key) and _present(value):
                return value
    return None


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _money(value: float) -> str:
    return f"{round(value):,}".replace(",", ".") + " VND"


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%".replace(".", ",")


def _rsi(closes: np.ndarray, period: int = 14) -> float | None:
    if closes.size <= period:
        return None
    changes = np.diff(closes[-(period + 1):])
    gains = np.clip(changes, 0, None).mean()
    losses = -np.clip(changes, None, 0).mean()
    if losses == 0:
        return 100.0
    return float(100 - 100 / (1 + gains / losses))


def _company_identity(ticker: str, overview_rows: list[dict[str, Any]]) -> tuple[str, list[str]]:
    fallback_name, fallback_industry = _COMPANY_FALLBACKS.get(
        ticker,
        (f"Doanh nghiệp niêm yết mã {ticker}", "Ngành chưa được nguồn miễn phí xác nhận"),
    )
    if not overview_rows:
        return fallback_name, [f"Mã {ticker}; ngành tham chiếu: {fallback_industry}."]
    row = overview_rows[0]
    name = str(
        _pick(row, "company_name", "organ_name", "short_name", "company_profile")
        or fallback_name
    )
    facts = []
    industry = _pick(row, "industry", "industry_name", "icb_name3", "sector")
    exchange = _pick(row, "exchange", "com_group_code", "stock_exchange")
    outstanding = _number(_pick(row, "outstanding_share", "issue_share", "shares_outstanding"))
    facts.append(f"Mã {ticker}" + (f" niêm yết tại {exchange}" if exchange else "") + ".")
    facts.append(f"Ngành/lĩnh vực: {industry or fallback_industry}.")
    if outstanding:
        facts.append(f"Cổ phiếu lưu hành theo nguồn: {outstanding:,.0f}.".replace(",", "."))
    return name, facts


def _technical_analysis(
    history_rows: list[dict[str, Any]],
    fallback_price: float | None,
) -> tuple[list[str], list[str], datetime | None]:
    if not history_rows:
        price = [f"Giá tham chiếu trong phương án: {_money(fallback_price)}."] if fallback_price else []
        return price, [], None

    sortable: list[tuple[datetime, dict[str, Any]]] = []
    for index, row in enumerate(history_rows):
        raw_time = _pick(row, "time", "date", "trading_date")
        try:
            parsed = datetime.fromisoformat(str(raw_time).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            parsed = datetime.min + timedelta(days=index)
        sortable.append((parsed, row))
    sortable.sort(key=lambda item: item[0])
    rows = [item[1] for item in sortable]
    closes = np.asarray([_number(_pick(row, "close", "close_price")) or np.nan for row in rows])
    valid = np.isfinite(closes) & (closes > 0)
    closes = closes[valid]
    if closes.size == 0:
        return [], [], None

    # Vnstock Quote.history biểu diễn giá cổ phiếu Việt Nam theo nghìn đồng
    # (ví dụ ACB 22,3 nghĩa là 22.300 VND), trong khi allocation dùng VND đầy đủ.
    # Dùng ngưỡng độc lập với fallback_price để câu hỏi về một mã chưa được chọn
    # vẫn không hiển thị sai 22 VND/cổ phiếu.
    scale = 1000.0 if closes[-1] < 1000 else 1.0
    closes *= scale
    latest = float(closes[-1])
    observed_at = sortable[-1][0] if sortable else None
    returns = np.diff(np.log(closes)) if closes.size > 1 else np.asarray([])
    sma20 = float(closes[-20:].mean()) if closes.size >= 20 else None
    sma50 = float(closes[-50:].mean()) if closes.size >= 50 else None
    rsi14 = _rsi(closes)
    return_1m = latest / closes[-21] - 1 if closes.size >= 21 else None
    return_3m = latest / closes[-61] - 1 if closes.size >= 61 else None
    annual_vol = float(returns[-60:].std(ddof=1) * np.sqrt(252)) if returns.size >= 20 else None
    low20 = float(closes[-20:].min()) if closes.size >= 20 else None
    high20 = float(closes[-20:].max()) if closes.size >= 20 else None

    price_facts = [f"Giá đóng cửa gần nhất: {_money(latest)}."]
    if return_1m is not None:
        price_facts.append(f"Biến động 1 tháng: {_pct(return_1m)}.")
    if return_3m is not None:
        price_facts.append(f"Biến động 3 tháng: {_pct(return_3m)}.")

    technical: list[str] = []
    if sma20 is not None and sma50 is not None:
        if latest > sma20 > sma50:
            trend = "xu hướng tăng ngắn–trung hạn"
        elif latest < sma20 < sma50:
            trend = "xu hướng giảm ngắn–trung hạn"
        else:
            trend = "xu hướng đan xen/chưa xác nhận"
        technical.append(
            f"Xu hướng: {trend}; giá {_money(latest)}, MA20 {_money(sma20)}, MA50 {_money(sma50)}."
        )
    if rsi14 is not None:
        zone = "quá mua" if rsi14 >= 70 else "quá bán" if rsi14 <= 30 else "trung tính"
        technical.append(f"RSI 14 phiên: {rsi14:.1f}/100, vùng {zone}.")
    if low20 is not None and high20 is not None:
        technical.append(
            f"Vùng giá quan sát 20 phiên: {_money(low20)}–{_money(high20)}; đây là vùng tham chiếu, không phải điểm mua/bán."
        )
    if annual_vol is not None:
        technical.append(f"Biến động năm hóa từ 60 phiên gần nhất: {_pct(annual_vol)}.")
    return price_facts, technical, observed_at


def _fundamental_analysis(ratio_rows: list[dict[str, Any]]) -> list[str]:
    if not ratio_rows:
        return []
    row = ratio_rows[-1]
    metrics = [
        ("P/E", _pick(row, "pe", "price_to_earnings"), "lần"),
        ("P/B", _pick(row, "pb", "price_to_book"), "lần"),
        ("ROE", _pick(row, "roe", "return_on_equity"), "%"),
        ("ROA", _pick(row, "roa", "return_on_assets"), "%"),
        ("Nợ/VCSH", _pick(row, "debt_to_equity", "debt_equity"), "lần"),
    ]
    facts = []
    for label, raw_value, unit in metrics:
        value = _number(raw_value)
        if value is None:
            continue
        if unit == "%" and abs(value) <= 2:
            value *= 100
        facts.append(f"{label}: {value:.2f}{unit}".replace(".", ","))
    return facts


def _news_analysis(news_rows: list[dict[str, Any]]) -> list[str]:
    facts: list[str] = []
    for row in news_rows[:5]:
        title = _pick(row, "title", "news_title", "headline")
        if not title:
            continue
        published = _pick(row, "publish_date", "published_at", "date", "time")
        source = _pick(row, "source", "source_name", "news_source")
        suffix = " · ".join(str(value) for value in [published, source] if value)
        facts.append(f"{title}" + (f" ({suffix})" if suffix else ""))
    return facts


def _macro_context() -> list[str]:
    facts: list[str] = []
    try:
        rows = [row for row in latest_observations() if row.get("source_id") == "WORLD_BANK_MACRO"]
    except Exception:
        return facts
    for row in rows[:4]:
        value = _number(row.get("value"))
        rendered = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if value is not None else "chưa có giá trị"
        facts.append(f"{row.get('label')}: {rendered} {row.get('unit') or ''} (quan sát {row.get('observed_at')}).")
    return facts


def _fetch_vnstock(ticker: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    from vnstock import Company, Finance, Quote

    start = (date.today() - timedelta(days=420)).isoformat()
    end = date.today().isoformat()
    errors: list[str] = []
    history_rows: list[dict[str, Any]] = []
    overview_rows: list[dict[str, Any]] = []
    news_rows: list[dict[str, Any]] = []
    ratio_rows: list[dict[str, Any]] = []

    for source in ("KBS", "VCI"):
        if history_rows:
            break
        try:
            with redirect_stdout(io.StringIO()):
                history_rows = _records(Quote(source=source, symbol=ticker).history(start=start, end=end, interval="1D"))
        except Exception as exc:
            errors.append(f"Giá {source}: {type(exc).__name__}")
    for source in ("KBS", "VCI"):
        if overview_rows and news_rows:
            break
        try:
            with redirect_stdout(io.StringIO()):
                company = Company(source=source, symbol=ticker)
                if not overview_rows:
                    overview_rows = _records(company.overview())
                if not news_rows:
                    news_rows = _records(company.news())
        except Exception as exc:
            errors.append(f"Doanh nghiệp/tin tức {source}: {type(exc).__name__}")
    for source in ("KBS", "VCI"):
        if ratio_rows:
            break
        try:
            with redirect_stdout(io.StringIO()):
                ratio_rows = _records(Finance(source=source, symbol=ticker, period="quarter").ratio())
        except Exception as exc:
            errors.append(f"Chỉ số tài chính {source}: {type(exc).__name__}")
    return history_rows, overview_rows, news_rows, ratio_rows, errors


def get_equity_research(ticker: str, fallback_price: float | None = None) -> EquityResearchResult:
    normalized_ticker = re.sub(r"[^A-Z0-9]", "", ticker.upper())
    with _CACHE_LOCK:
        cached = _CACHE.get(normalized_ticker)
        if cached and monotonic() - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]

    source_status = next(
        (
            row.get("status")
            for row in list_source_status()
            if row.get("source_id") == "VNSTOCK_VN30"
        ),
        None,
    )
    if source_status == "CONNECTED":
        try:
            history, overview, news, ratios, errors = _fetch_vnstock(normalized_ticker)
        except Exception as exc:
            history, overview, news, ratios = [], [], [], []
            errors = [f"Không khởi tạo được nguồn Vnstock Free: {type(exc).__name__}"]
    else:
        history, overview, news, ratios = [], [], [], []
        errors = [
            f"Nguồn Vnstock Free đang ở trạng thái {source_status or 'CHƯA KHỞI TẠO'}; "
            "không gọi lặp lại nguồn đang lỗi trong luồng chat."
        ]

    company_name, company_facts = _company_identity(normalized_ticker, overview)
    price_facts, technical_facts, observed_at = _technical_analysis(history, fallback_price)
    curated = _CURATED_RESEARCH.get(normalized_ticker, {})
    result = EquityResearchResult(
        ticker=normalized_ticker,
        company_name=company_name,
        company_facts=company_facts,
        investment_thesis=list(curated.get("investment_thesis", [])),
        price_facts=price_facts,
        technical_facts=technical_facts,
        fundamental_facts=_fundamental_analysis(ratios),
        earnings_facts=list(curated.get("earnings_facts", [])),
        valuation_facts=list(curated.get("valuation_facts", [])),
        quality_facts=list(curated.get("quality_facts", [])),
        analyst_views=list(curated.get("analyst_views", [])),
        catalysts=list(curated.get("catalysts", [])),
        risk_facts=list(curated.get("risk_facts", [])),
        news_facts=_news_analysis(news),
        macro_facts=_macro_context(),
        sources=[
            f"Vnstock Free (KBS/VCI, dữ liệu có độ trễ): {VNSTOCK_FREE_DOCS}",
            "World Bank API (bối cảnh vĩ mô, tần suất theo chỉ tiêu)",
            *curated.get("sources", []),
        ],
        limitations=errors,
        observed_at=observed_at,
    )
    if not result.technical_facts:
        result.limitations.append("Chưa lấy được chuỗi OHLCV nên chưa thể kết luận MA, RSI và vùng giá.")
    if not result.fundamental_facts:
        result.limitations.append("Chưa lấy được chỉ số tài chính mới nhất; không suy đoán P/E, P/B, ROE.")
    if not result.news_facts:
        result.limitations.append("Chưa lấy được tin doanh nghiệp; không dùng tin giả định để giải thích lựa chọn.")
    with _CACHE_LOCK:
        _CACHE[normalized_ticker] = (monotonic(), result)
    return result
