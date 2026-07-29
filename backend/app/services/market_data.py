from __future__ import annotations

import csv
import html
import io
import json
import logging
import math
import re
from contextlib import redirect_stdout
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Callable
from zoneinfo import ZoneInfo

import httpx
import numpy as np
from bs4 import BeautifulSoup

from backend.app.db.market_data import (
    latest_observations,
    list_source_status,
    save_source_result,
)
from backend.app.db.sqlite import (
    restrict_mock_products,
    restrict_products_by_source,
    upsert_asset_products,
)
from backend.app.models import (
    AllocationRuleType,
    AllocationSegment,
    AssetClass,
    AssetProduct,
    QualifyingBalanceScope,
    RightsStatus,
    RoundingRule,
    UncertaintyBounds,
    ValueProvenance,
    VerificationStatus,
)


logger = logging.getLogger("monopoly.market_data")
VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
USER_AGENT = "MonopolyAI-DelayedData/2.0 (+local research system)"


@dataclass
class ConnectorResult:
    source_id: str
    display_name: str
    category: str
    source_url: str
    cadence: str
    stale_after_seconds: int
    observed_at: datetime
    observations: list[dict[str, Any]]
    products: list[AssetProduct] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def _client(timeout: float = 35.0) -> httpx.Client:
    return httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "vi,en;q=0.8"},
    )


def _parse_vietnam_datetime(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%d/%m/%Y %H:%M:%S").replace(
        tzinfo=VIETNAM_TZ
    )


def _parse_percent(value: Any) -> float | None:
    if value is None:
        return None
    cleaned = str(value).strip().replace("%", "").replace(",", ".")
    if not cleaned or cleaned in {"N/A", "0", "Chưa có"}:
        return None
    try:
        return float(cleaned) / 100
    except ValueError:
        return None


def _gold_product(
    *,
    product_id: str,
    product_name: str,
    provider: str,
    buy_price: float,
    sell_price: float,
    minimum_investment: float,
    timestamp: datetime,
    source_url: str,
) -> AssetProduct:
    spread = max(0.0, (buy_price - sell_price) / buy_price)
    return AssetProduct(
        product_id=product_id,
        asset_class=AssetClass.GOLD,
        provider=provider,
        product_name=product_name,
        source_reference=(
            f"{source_url} — giá mua/bán chính thức; lợi nhuận kỳ vọng và "
            "biến động vẫn là giả định mô hình."
        ),
        data_timestamp=timestamp,
        buy_price=buy_price,
        sell_price=sell_price,
        expected_return=0.05,
        volatility=0.20,
        liquidity_score=82,
        minimum_investment=minimum_investment,
        transaction_cost=spread,
        lockup_period=0,
        early_exit_penalty=0,
        eligibility_conditions={"market": "Vietnam", "quote": "delayed_official"},
        risk_level="MEDIUM",
        timing_score=None,
        data_confidence=88,
        max_weight_hint=0.25,
        execution_instruction=(
            "Chỉ dùng giá công bố để so sánh trong chế độ giáo dục; xác nhận lại "
            "giá tại đơn vị cung cấp trước mọi giao dịch ngoài hệ thống."
        ),
        allocation_rule_type=AllocationRuleType.DISCRETE_UNIT,
        qualifying_balance_scope=QualifyingBalanceScope.PER_CONTRACT,
        rounding_rule=RoundingRule.WHOLE_UNIT,
        repricing_required=True,
        source_registry_id="PNJ_OFFICIAL_DELAYED_GOLD",
        rights_status=RightsStatus.APPROVED,
        value_provenance=ValueProvenance.OFFICIAL_API,
        verification_status=VerificationStatus.PARTIALLY_VERIFIED,
    )


def fetch_pnj_gold() -> ConnectorResult:
    source_url = "https://edge-api.pnj.io/ecom-frontend/v1/get-gold-price?zone=00"
    with _client() as client:
        response = client.get(source_url)
        response.raise_for_status()
        payload = response.json()
    observed_at = _parse_vietnam_datetime(payload["updateDate"])
    wanted = {"SJC", "N24K"}
    rows = [row for row in payload["data"] if row.get("masp") in wanted]
    if len(rows) != len(wanted):
        raise ValueError("PNJ response is missing required SJC/N24K quotes")

    observations: list[dict[str, Any]] = []
    products: list[AssetProduct] = []
    for row in rows:
        code = row["masp"]
        buy_per_chi = float(row["giaban"]) * 1_000
        sell_per_chi = float(row["giamua"]) * 1_000
        observations.extend(
            [
                {
                    "series_key": f"{code}_BUY",
                    "label": f"{row['tensp']} — giá khách hàng mua",
                    "value": buy_per_chi,
                    "unit": "VND/chi",
                    "observed_at": observed_at,
                    "raw": row,
                },
                {
                    "series_key": f"{code}_SELL",
                    "label": f"{row['tensp']} — giá khách hàng bán",
                    "value": sell_per_chi,
                    "unit": "VND/chi",
                    "observed_at": observed_at,
                    "raw": row,
                },
            ]
        )
        if code == "SJC":
            products.append(
                _gold_product(
                    product_id="gold-sjc-pnj-delayed",
                    product_name="Vàng miếng SJC 999.9 — đơn vị giao dịch 1 lượng, giá PNJ chậm",
                    provider="PNJ (phân phối SJC)",
                    buy_price=buy_per_chi * 10,
                    sell_price=sell_per_chi * 10,
                    minimum_investment=buy_per_chi * 10,
                    timestamp=observed_at,
                    source_url=source_url,
                )
            )
        else:
            products.append(
                _gold_product(
                    product_id="gold-ring-pnj-delayed",
                    product_name="Vàng nhẫn tròn PNJ 999.9 — đơn vị giao dịch 1 chỉ, giá chậm",
                    provider="PNJ",
                    buy_price=buy_per_chi,
                    sell_price=sell_per_chi,
                    minimum_investment=buy_per_chi,
                    timestamp=observed_at,
                    source_url=source_url,
                )
            )
    return ConnectorResult(
        source_id="PNJ_GOLD",
        display_name="PNJ — Giá vàng",
        category="GOLD",
        source_url=source_url,
        cadence="Theo ngày",
        stale_after_seconds=3 * 24 * 3600,
        observed_at=observed_at,
        observations=observations,
        products=products,
        metadata={"branch": payload.get("chinhanh"), "official": True},
    )


def _deposit_product(
    *,
    tenor_months: int,
    rate: float,
    observed_at: datetime,
    source_url: str,
) -> AssetProduct:
    liquidity_score = {6: 82, 12: 72, 24: 60}[tenor_months]
    return AssetProduct(
        product_id=f"deposit-vietcombank-{tenor_months}m-delayed",
        asset_class=AssetClass.DEPOSIT,
        provider="Vietcombank",
        product_name=f"Tiền gửi trực tuyến VND {tenor_months} tháng — lãi suất chậm",
        source_reference=(
            f"{source_url} — lãi suất VND cá nhân chính thức; mức đầu tư tối thiểu, "
            "thanh khoản và phạt rút trước hạn là giả định thận trọng của mô hình."
        ),
        data_timestamp=observed_at,
        expected_return=rate,
        volatility=0.005,
        liquidity_score=liquidity_score,
        minimum_investment=1_000_000,
        transaction_cost=0,
        lockup_period=round(tenor_months * 365 / 12),
        early_exit_penalty=rate,
        eligibility_conditions={
            "channel": "online",
            "currency": "VND",
            "customer_segment": "retail",
        },
        risk_level="LOW",
        data_confidence=92,
        max_weight_hint=0.85 if tenor_months <= 12 else 0.65,
        execution_instruction=(
            "Dùng để so sánh; phải xác nhận điều kiện tài khoản và lãi suất tại "
            "Vietcombank trước khi gửi tiền."
        ),
        allocation_rule_type=AllocationRuleType.FIXED_RETURN,
        qualifying_balance_scope=QualifyingBalanceScope.PER_CONTRACT,
        rounding_rule=RoundingRule.VND_1M,
        repricing_required=True,
        source_registry_id="VIETCOMBANK_OFFICIAL_INTEREST_RATE",
        rights_status=RightsStatus.APPROVED,
        value_provenance=ValueProvenance.OFFICIAL_API,
        verification_status=VerificationStatus.PARTIALLY_VERIFIED,
    )


def fetch_vietcombank_rates() -> ConnectorResult:
    source_url = (
        "https://vietcombank.com.vn/vi-VN/KHCN/Cong-cu-Tien-ich/"
        "KHCN---Lai-suat"
    )
    with _client() as client:
        response = client.get(source_url)
        response.raise_for_status()
        page = response.text
    match = re.search(
        r'id="currentDataInterestRate"\s+value="([^"]+)"',
        page,
        flags=re.IGNORECASE,
    )
    if not match:
        raise ValueError("Vietcombank page does not expose currentDataInterestRate")
    payload = json.loads(html.unescape(match.group(1)))
    observed_at = datetime.fromisoformat(payload["UpdatedDate"])
    tenors = {6, 12, 24}
    rows: list[tuple[int, dict[str, Any]]] = []
    for row in payload["Data"]:
        tenor_match = re.fullmatch(r"(\d+)-months", row.get("tenor", ""))
        if (
            row.get("tenorType") == "Online"
            and row.get("currencyCode") == "VND"
            and tenor_match
            and int(tenor_match.group(1)) in tenors
            and row.get("rates") is not None
        ):
            rows.append((int(tenor_match.group(1)), row))
    if {tenor for tenor, _ in rows} != tenors:
        raise ValueError("Vietcombank response is missing required VND tenors")
    observations = [
        {
            "series_key": f"ONLINE_VND_{tenor}M",
            "label": f"Tiền gửi trực tuyến VND {tenor} tháng",
            "value": float(row["rates"]),
            "unit": "annual_rate_decimal",
            "observed_at": observed_at,
            "raw": row,
        }
        for tenor, row in rows
    ]
    products = [
        _deposit_product(
            tenor_months=tenor,
            rate=float(row["rates"]),
            observed_at=observed_at,
            source_url=source_url,
        )
        for tenor, row in rows
    ]
    return ConnectorResult(
        source_id="VIETCOMBANK_RATES",
        display_name="Vietcombank — Lãi suất",
        category="DEPOSIT",
        source_url=source_url,
        cadence="Khi ngân hàng cập nhật",
        stale_after_seconds=21 * 24 * 3600,
        observed_at=observed_at,
        observations=observations,
        products=products,
        metadata={"account_type": payload.get("AccountType"), "official": True},
    )


DEPOSIT_TENORS = (1, 3, 6, 12, 18, 24, 36)
TARGET_DEPOSIT_BANKS = ("MBBank", "Techcombank", "VPBank")


def _first_number(value: str) -> float:
    match = re.search(r"\d+(?:[.,]\d+)?", value)
    if not match:
        raise ValueError(f"Missing numeric rate in {value!r}")
    return float(match.group(0).replace(",", "."))


def _bank_deposit_product(
    *,
    bank: str,
    tenor_months: int,
    rate: float,
    observed_at: datetime,
    source_url: str,
) -> AssetProduct:
    if bank == "Techcombank":
        minimum = 3_000_000_000
        maximum = None
        customer_segment = "private"
        amount_condition = "Khách hàng Private, số tiền từ 3 tỷ VND"
        balance_scope = QualifyingBalanceScope.CUSTOMER_AUM
    else:
        minimum = 1_000_000
        maximum = 999_999_999
        customer_segment = "retail"
        amount_condition = "Số tiền dưới 1 tỷ VND theo phạm vi bảng tham khảo"
        balance_scope = (
            QualifyingBalanceScope.TOTAL_NEW_MONEY
            if bank == "VPBank"
            else QualifyingBalanceScope.PER_CONTRACT
        )
    liquidity_score = max(45, 91 - tenor_months * 2)
    upper_bound = maximum + 1 if maximum is not None else None
    rate_decimal = rate / 100
    slug = bank.lower().replace("bank", "bank")
    return AssetProduct(
        product_id=f"deposit-{slug}-online-{tenor_months}m-delayed",
        asset_class=AssetClass.DEPOSIT,
        provider=bank,
        product_name=f"Tiền gửi online {tenor_months} tháng — {bank}",
        source_reference=(
            f"{source_url} — bảng so sánh tiền gửi online lĩnh lãi cuối kỳ; "
            f"điều kiện áp dụng: {amount_condition}. Cần xác nhận lại trên ứng dụng "
            "ngân hàng trước khi mở khoản tiền gửi."
        ),
        data_timestamp=observed_at,
        expected_return=rate_decimal,
        volatility=0.004,
        liquidity_score=liquidity_score,
        minimum_investment=minimum,
        maximum_investment=maximum,
        transaction_cost=0,
        lockup_period=round(tenor_months * 365 / 12),
        early_exit_penalty=max(0, rate_decimal - 0.001),
        eligibility_conditions={
            "channel": "online",
            "currency": "VND",
            "customer_segment": customer_segment,
            "tenor_months": tenor_months,
            "interest_payment": "end_of_term",
            "amount_condition": amount_condition,
        },
        risk_level="LOW",
        data_confidence=78,
        max_weight_hint=0.75 if tenor_months <= 12 else 0.60,
        execution_instruction=(
            "So sánh theo kỳ hạn, số vốn và phân khúc khách hàng; xác nhận lại "
            "lãi suất, điều kiện ưu đãi và quy tắc rút trước hạn trên kênh chính thức."
        ),
        product_base_id=f"deposit-{slug}-online",
        allocation_rule_type=AllocationRuleType.WHOLE_BALANCE_TIER,
        allocation_segments=[
            AllocationSegment(
                lower_bound=minimum,
                upper_bound=upper_bound,
                return_rate=rate_decimal,
                cost=0,
                condition=amount_condition,
            )
        ],
        qualifying_balance_scope=balance_scope,
        rounding_rule=RoundingRule.VND_1M,
        repricing_required=True,
        source_registry_id="TECHCOMBANK_CROSS_BANK_RATE_TABLE",
        rights_status=RightsStatus.APPROVED,
        value_provenance=ValueProvenance.MANUAL_VERIFIED,
        verification_status=VerificationStatus.PARTIALLY_VERIFIED,
        uncertainty_bounds=UncertaintyBounds(
            lower=max(0, rate_decimal - 0.003),
            upper=rate_decimal + 0.003,
            confidence_level=0.78,
            note="Lãi suất có thể thay đổi theo số tiền, phân khúc và chính sách tại thời điểm mở sổ.",
        ),
    )


def fetch_target_bank_rates() -> ConnectorResult:
    source_url = (
        "https://techcombank.com/thong-tin/blog/"
        "lai-suat-tiet-kiem?lead=dgmkt-paid-ads"
    )
    with _client() as client:
        response = client.get(source_url)
        response.raise_for_status()
        page = response.text
    soup = BeautifulSoup(page, "html.parser")
    modified_meta = soup.find(
        "meta",
        attrs={"itemprop": lambda value: value and "dateModified" in value},
    )
    observed_at = (
        datetime.fromisoformat(str(modified_meta.get("content")))
        if modified_meta and modified_meta.get("content")
        else datetime.now(VIETNAM_TZ)
    )
    online_rows: dict[str, list[str]] = {}
    for table in soup.find_all("table"):
        rows = [
            [
                cell.get_text(" ", strip=True)
                for cell in row.find_all(["th", "td"])
            ]
            for row in table.find_all("tr")
        ]
        if not rows or rows[0][:2] != ["Ngân hàng", "1 tháng"]:
            continue
        bank_rows = {
            row[0]: row[1:]
            for row in rows[1:]
            if len(row) >= len(DEPOSIT_TENORS) + 1
        }
        if all(bank in bank_rows for bank in TARGET_DEPOSIT_BANKS):
            online_rows = bank_rows
    if not online_rows:
        raise ValueError("Techcombank page does not expose the target online-rate table")

    observations: list[dict[str, Any]] = []
    products: list[AssetProduct] = []
    for bank in TARGET_DEPOSIT_BANKS:
        values = online_rows[bank]
        for tenor, raw_rate in zip(DEPOSIT_TENORS, values, strict=True):
            rate = _first_number(raw_rate)
            observations.append(
                {
                    "series_key": f"{bank.upper()}_ONLINE_{tenor}M",
                    "label": f"{bank} online {tenor} tháng",
                    "value": rate / 100,
                    "unit": "annual_rate_decimal",
                    "observed_at": observed_at,
                    "bank": bank,
                    "tenor_months": tenor,
                    "raw": raw_rate,
                }
            )
            products.append(
                _bank_deposit_product(
                    bank=bank,
                    tenor_months=tenor,
                    rate=rate,
                    observed_at=observed_at,
                    source_url=source_url,
                )
            )
    return ConnectorResult(
        source_id="TARGET_BANK_DEPOSIT_RATES",
        display_name="MBBank · Techcombank · VPBank — Lãi suất online",
        category="DEPOSIT",
        source_url=source_url,
        cadence="Theo ngày; xác nhận lại khi mở sổ",
        stale_after_seconds=7 * 24 * 3600,
        observed_at=observed_at,
        observations=observations,
        products=products,
        metadata={
            "official_page_owner": "Techcombank",
            "cross_bank_reference": True,
            "banks": list(TARGET_DEPOSIT_BANKS),
            "tenors": list(DEPOSIT_TENORS),
            "official": False,
            "usage_scope": "RESEARCH_EDUCATION",
        },
    )


def _vnstock_products(
    *,
    members: list[str],
    etfs: list[str],
    quotes: Any,
    observed_at: datetime,
    expected_return: float,
    index_volatility: float,
    source_url: str,
) -> tuple[list[dict[str, Any]], list[AssetProduct]]:
    observations: list[dict[str, Any]] = []
    products: list[AssetProduct] = []
    quote_rows = {
        str(row["symbol"]): row
        for row in quotes.to_dict("records")
        if row.get("symbol")
    }
    for symbol in [*members, *etfs]:
        row = quote_rows.get(symbol)
        if not row:
            continue
        price = float(row.get("close_price") or row.get("reference_price") or 0)
        if price <= 0:
            continue
        is_etf = symbol in etfs
        asset_class = AssetClass.ETF if is_etf else AssetClass.EQUITY
        volatility = index_volatility if is_etf else min(0.50, index_volatility * 1.35)
        observations.append(
            {
                "series_key": f"{symbol}_CLOSE",
                "label": f"{symbol} — giá gần nhất",
                "value": price,
                "unit": "VND/share",
                "observed_at": observed_at,
                "symbol": symbol,
                "exchange": row.get("exchange"),
                "reference_price": row.get("reference_price"),
                "raw": row,
            }
        )
        products.append(
            AssetProduct(
                product_id=(
                    f"vn30-etf-{symbol.lower()}-vnstock"
                    if is_etf
                    else f"vn30-equity-{symbol.lower()}-vnstock"
                ),
                asset_class=asset_class,
                provider="HOSE · Vnstock research connector",
                product_name=(
                    f"{symbol} — ETF theo dõi VN30"
                    if is_etf
                    else f"{symbol} — thành phần VN30 động"
                ),
                source_reference=(
                    f"{source_url} — Vnstock 4, nguồn KBS/VCI; chỉ dùng trong "
                    "RESEARCH_EDUCATION, không phải feed giao dịch được cấp phép."
                ),
                data_timestamp=observed_at,
                buy_price=price,
                sell_price=price,
                expected_return=expected_return,
                volatility=volatility,
                liquidity_score=78 if is_etf else 72,
                minimum_investment=price * 100,
                transaction_cost=0.0018,
                lockup_period=0,
                early_exit_penalty=0,
                eligibility_conditions={
                    "universe": "VN30 dynamic",
                    "ticker": symbol,
                    "market": "HOSE",
                    "no_margin": True,
                    "no_short_selling": True,
                    "usage_scope": "RESEARCH_EDUCATION",
                },
                risk_level="HIGH",
                data_confidence=72,
                max_weight_hint=0.16 if is_etf else 0.08,
                execution_instruction=(
                    "Chỉ dùng nội bộ để tính và so sánh nhóm tài sản; chế độ nghiên cứu "
                    "không phát hành lệnh mua mã kèm số tiền cá nhân hóa."
                ),
                allocation_rule_type=AllocationRuleType.DISCRETE_UNIT,
                qualifying_balance_scope=QualifyingBalanceScope.PER_CONTRACT,
                rounding_rule=RoundingRule.BOARD_LOT_100,
                repricing_required=True,
                source_registry_id="VNSTOCK_RESEARCH_VN30",
                rights_status=RightsStatus.APPROVED,
                value_provenance=ValueProvenance.DERIVED,
                verification_status=VerificationStatus.PARTIALLY_VERIFIED,
                uncertainty_bounds=UncertaintyBounds(
                    lower=max(-0.10, expected_return - 0.06),
                    upper=min(0.30, expected_return + 0.06),
                    confidence_level=0.60,
                    note="Expected return và volatility suy ra từ lịch sử chỉ số VN30, không phải dự báo từng mã.",
                ),
            )
        )
    return observations, products


def fetch_vnstock_vn30() -> ConnectorResult:
    source_url = "https://vnstocks.com/docs/vnstock/tra-cuu-thong-tin-tham-chieu-reference"
    capture = io.StringIO()
    with redirect_stdout(capture):
        from vnstock import Market, Reference

        reference = Reference()
        members_series = reference.index.members("VN30")
        etf_series = reference.etf.list()
        members = sorted({str(value) for value in members_series.dropna().tolist()})
        etfs = sorted(
            {
                str(value)
                for value in etf_series.dropna().tolist()
                if "VN30" in str(value) or str(value).endswith("V30")
            }
        )
        if len(members) < 25:
            raise ValueError(f"Vnstock returned only {len(members)} VN30 members")
        market = Market()
        quotes = market.quote([*members, *etfs])
        history = market.index("VN30").ohlcv(length=260, interval="1D")
    closes = np.asarray(history["close"].dropna(), dtype=float)
    if closes.size < 60:
        raise ValueError("Vnstock VN30 history is too short for risk parameters")
    log_returns = np.diff(np.log(closes))
    expected_return = float(np.clip(np.mean(log_returns) * 252, -0.05, 0.18))
    index_volatility = float(np.clip(np.std(log_returns, ddof=1) * np.sqrt(252), 0.12, 0.38))
    quote_times = [
        int(value)
        for value in quotes.get("time", []).tolist()
        if value is not None and str(value) != "nan"
    ]
    observed_at = (
        datetime.fromtimestamp(max(quote_times) / 1000, tz=VIETNAM_TZ)
        if quote_times
        else datetime.now(VIETNAM_TZ)
    )
    observations, products = _vnstock_products(
        members=members,
        etfs=etfs,
        quotes=quotes,
        observed_at=observed_at,
        expected_return=expected_return,
        index_volatility=index_volatility,
        source_url=source_url,
    )
    observations.extend(
        [
            {
                "series_key": "VN30_EXPECTED_RETURN_DERIVED",
                "label": "VN30 — lợi nhuận năm hóa suy ra từ lịch sử",
                "value": expected_return,
                "unit": "annual_rate_decimal",
                "observed_at": observed_at,
            },
            {
                "series_key": "VN30_VOLATILITY_DERIVED",
                "label": "VN30 — biến động năm hóa suy ra từ lịch sử",
                "value": index_volatility,
                "unit": "annual_volatility_decimal",
                "observed_at": observed_at,
            },
        ]
    )
    return ConnectorResult(
        source_id="VNSTOCK_VN30",
        display_name="Vnstock — VN30 động và giá thị trường",
        category="EQUITY",
        source_url=source_url,
        cadence="Cuối ngày/chậm; tối đa theo giới hạn cộng đồng",
        stale_after_seconds=3 * 24 * 3600,
        observed_at=observed_at,
        observations=observations,
        products=products,
        metadata={
            "library": "vnstock",
            "library_version_family": "4.x",
            "underlying_sources": ["KBS", "VCI"],
            "member_count": len(members),
            "etf_count": len(etfs),
            "official": False,
            "usage_scope": "RESEARCH_EDUCATION",
            "license": "personal/non-commercial research",
        },
    )


def fetch_vcbf_nav() -> ConnectorResult:
    source_url = (
        "https://www.vcbf.com/quy-mo/cac-quy-mo/"
        "quy-dau-tu-can-bang-chien-luoc-vcbf/"
    )
    with _client() as client:
        response = client.get(source_url)
        response.raise_for_status()
        page = response.text
    match = re.search(
        r"var dataJson=JSON\.parse\('(?P<payload>.*?)'\);",
        page,
        flags=re.DOTALL,
    )
    if not match:
        raise ValueError("VCBF page does not expose the NAV data payload")
    payload = json.loads(match.group("payload"))
    observations: list[dict[str, Any]] = []
    observed_dates: list[datetime] = []
    labels = {
        "fif_data": "VCBF-FIF Quỹ đầu tư trái phiếu",
        "tbf_data": "VCBF-TBF Quỹ cân bằng",
        "bcf_data": "VCBF-BCF Quỹ cổ phiếu",
    }
    for key, label in labels.items():
        row = payload[key]
        date_match = re.search(r"(\d{2}/\d{2}/\d{4})", str(row.get("date")))
        if not date_match:
            continue
        observed_at = datetime.strptime(
            date_match.group(1),
            "%d/%m/%Y",
        ).replace(tzinfo=VIETNAM_TZ)
        observed_dates.append(observed_at)
        nav = float(str(row["price"]).replace(",", ""))
        observations.append(
            {
                "series_key": key.removesuffix("_data").upper() + "_NAV",
                "label": label,
                "value": nav,
                "unit": "VND/fund_unit",
                "observed_at": observed_at,
                "return_1y": _parse_percent(row.get("nav_val_ytd")),
                "return_3y_annualized": _parse_percent(row.get("nav_val_3ytd")),
                "raw": row,
            }
        )
    if not observations:
        raise ValueError("VCBF NAV payload did not contain dated observations")
    fif = next(item for item in observations if item["series_key"] == "FIF_NAV")
    expected_return = (
        fif.get("return_3y_annualized")
        or fif.get("return_1y")
        or 0.06
    )
    products = [
        AssetProduct(
            product_id="bond-fund-vcbf-fif-delayed",
            asset_class=AssetClass.BOND_FUND,
            provider="VCBF",
            product_name="Quỹ đầu tư trái phiếu VCBF-FIF — NAV chậm",
            source_reference=(
                f"{source_url} — NAV và hiệu suất công bố chính thức; biến động, "
                "thanh khoản và chi phí là giả định mô hình cần xác nhận."
            ),
            data_timestamp=fif["observed_at"],
            buy_price=float(fif["value"]),
            sell_price=float(fif["value"]),
            expected_return=float(expected_return),
            volatility=0.045,
            liquidity_score=68,
            minimum_investment=1_000_000,
            transaction_cost=0.002,
            lockup_period=7,
            early_exit_penalty=0.005,
            eligibility_conditions={"currency": "VND", "fund_type": "bond"},
            risk_level="MEDIUM",
            data_confidence=86,
            max_weight_hint=0.55,
            execution_instruction=(
                "Chỉ dùng để so sánh; đọc bản cáo bạch và xác nhận NAV/phí tại VCBF "
                "trước mọi giao dịch ngoài hệ thống."
            ),
            allocation_rule_type=AllocationRuleType.FIXED_RETURN,
            qualifying_balance_scope=QualifyingBalanceScope.PER_CONTRACT,
            rounding_rule=RoundingRule.VND_100K,
            repricing_required=True,
            source_registry_id="VCBF_OFFICIAL_NAV",
            rights_status=RightsStatus.APPROVED,
            value_provenance=ValueProvenance.OFFICIAL_API,
            verification_status=VerificationStatus.PARTIALLY_VERIFIED,
        )
    ]
    return ConnectorResult(
        source_id="VCBF_NAV",
        display_name="VCBF — NAV quỹ",
        category="FUND",
        source_url=source_url,
        cadence="Theo ngày/tuần",
        stale_after_seconds=14 * 24 * 3600,
        observed_at=max(observed_dates),
        observations=observations,
        products=products,
        metadata={"official": True, "fund_count": len(observations)},
    )


def _yahoo_daily_chart(client: httpx.Client, symbol: str) -> list[dict[str, Any]]:
    response = client.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
        params={"range": "1y", "interval": "1d", "events": "history"},
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    payload = response.json()["chart"]
    if payload.get("error") or not payload.get("result"):
        raise ValueError(f"Yahoo Finance returned no chart for {symbol}")
    result = payload["result"][0]
    timestamps = result.get("timestamp") or []
    closes = (
        result.get("indicators", {})
        .get("quote", [{}])[0]
        .get("close", [])
    )
    rows = [
        {"timestamp": int(timestamp), "close": float(close)}
        for timestamp, close in zip(timestamps, closes, strict=False)
        if close is not None and math.isfinite(float(close))
    ]
    if len(rows) < 60:
        raise ValueError(f"Yahoo Finance returned only {len(rows)} rows for {symbol}")
    return rows


def _return_over(rows: list[dict[str, Any]], sessions: int) -> float:
    if len(rows) <= sessions:
        return 0.0
    return rows[-1]["close"] / rows[-sessions - 1]["close"] - 1


def _rsi14(closes: np.ndarray) -> float:
    changes = np.diff(closes[-15:])
    gains = np.clip(changes, 0, None)
    losses = np.clip(-changes, 0, None)
    average_gain = float(gains.mean())
    average_loss = float(losses.mean())
    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0
    relative_strength = average_gain / average_loss
    return 100 - 100 / (1 + relative_strength)


def _fred_series(
    client: httpx.Client,
    series_id: str,
) -> list[tuple[datetime, float]]:
    response = client.get(
        "https://fred.stlouisfed.org/graph/fredgraph.csv",
        params={"id": series_id, "cosd": "2025-01-01"},
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    rows: list[tuple[datetime, float]] = []
    for row in csv.DictReader(io.StringIO(response.text)):
        raw_value = row.get(series_id)
        if raw_value in {None, "", "."}:
            continue
        observed = datetime.fromisoformat(row["observation_date"]).replace(
            tzinfo=timezone.utc
        )
        rows.append((observed, float(raw_value)))
    if not rows:
        raise ValueError(f"FRED returned no observations for {series_id}")
    return rows


def fetch_global_gold_market() -> ConnectorResult:
    """Free delayed world-gold chart and macro drivers used by the gold module."""

    source_url = "https://finance.yahoo.com/quote/GC=F/history/"
    with _client(timeout=65.0) as client:
        gold_rows = _yahoo_daily_chart(client, "GC=F")
        fx_rows = _yahoo_daily_chart(client, "VND=X")
        dollar_rows = _yahoo_daily_chart(client, "DX-Y.NYB")
        real_yield_rows = _fred_series(client, "DFII10")

    closes = np.asarray([row["close"] for row in gold_rows], dtype=float)
    log_returns = np.diff(np.log(closes[-61:]))
    annualized_volatility = float(np.std(log_returns, ddof=1) * np.sqrt(252))
    running_high = np.maximum.accumulate(closes)
    max_drawdown = float(np.min(closes / running_high - 1))
    latest_at = datetime.fromtimestamp(
        gold_rows[-1]["timestamp"], tz=timezone.utc
    )
    real_yield_change = (
        real_yield_rows[-1][1] - real_yield_rows[-64][1]
        if len(real_yield_rows) > 64
        else real_yield_rows[-1][1] - real_yield_rows[0][1]
    )

    metrics = [
        ("GC_F_PRICE", "Vàng thế giới COMEX gần nhất", closes[-1], "USD/troy_oz"),
        ("GC_F_RETURN_1M", "Vàng thế giới — lợi suất 1 tháng", _return_over(gold_rows, 21), "decimal_return"),
        ("GC_F_RETURN_3M", "Vàng thế giới — lợi suất 3 tháng", _return_over(gold_rows, 63), "decimal_return"),
        ("GC_F_RETURN_1Y", "Vàng thế giới — lợi suất 1 năm", _return_over(gold_rows, min(251, len(gold_rows) - 1)), "decimal_return"),
        ("GC_F_MA20", "Vàng thế giới — MA20", float(closes[-20:].mean()), "USD/troy_oz"),
        ("GC_F_MA50", "Vàng thế giới — MA50", float(closes[-50:].mean()), "USD/troy_oz"),
        ("GC_F_RSI14", "Vàng thế giới — RSI14", _rsi14(closes), "index_0_100"),
        ("GC_F_VOLATILITY_60D", "Vàng thế giới — biến động năm hóa 60 phiên", annualized_volatility, "annual_volatility_decimal"),
        ("GC_F_MAX_DRAWDOWN_1Y", "Vàng thế giới — sụt giảm tối đa 1 năm", max_drawdown, "decimal_return"),
        ("USDVND", "Tỷ giá USD/VND tham chiếu", fx_rows[-1]["close"], "VND_per_USD"),
        ("DXY", "Chỉ số sức mạnh USD", dollar_rows[-1]["close"], "index"),
        ("DXY_RETURN_3M", "Chỉ số USD — thay đổi 3 tháng", _return_over(dollar_rows, 63), "decimal_return"),
        ("US_REAL_YIELD_10Y", "Lợi suất thực Mỹ 10 năm", real_yield_rows[-1][1] / 100, "annual_rate_decimal"),
        ("US_REAL_YIELD_CHANGE_3M", "Lợi suất thực Mỹ 10 năm — thay đổi 3 tháng", real_yield_change / 100, "decimal_point_change"),
    ]
    observations = [
        {
            "series_key": key,
            "label": label,
            "value": float(value),
            "unit": unit,
            "observed_at": latest_at,
        }
        for key, label, value, unit in metrics
    ]
    chart = [
        {
            "date": datetime.fromtimestamp(row["timestamp"], tz=timezone.utc).date().isoformat(),
            "close": round(row["close"], 2),
        }
        for row in gold_rows[-180:]
    ]
    return ConnectorResult(
        source_id="GLOBAL_GOLD_MARKET",
        display_name="Vàng thế giới COMEX · USD/VND · FRED",
        category="GOLD",
        source_url=source_url,
        cadence="Cuối ngày/chậm",
        stale_after_seconds=3 * 24 * 3600,
        observed_at=latest_at,
        observations=observations,
        metadata={
            "research_only": True,
            "chart_symbol": "GC=F",
            "chart": chart,
            "fred_real_yield_series": "DFII10",
            "method": "MA20, MA50, RSI14, volatility 60 sessions and 1/3/12-month returns",
        },
    )


def fetch_world_bank_macro() -> ConnectorResult:
    source_url = (
        "https://api.worldbank.org/v2/country/VNM/indicator/"
        "FP.CPI.TOTL.ZG?format=json&per_page=10"
    )
    with _client(timeout=65.0) as client:
        response = client.get(source_url)
        response.raise_for_status()
        payload = response.json()
    rows = [row for row in payload[1] if row.get("value") is not None]
    if not rows:
        raise ValueError("World Bank CPI series returned no values")
    latest = max(rows, key=lambda row: int(row["date"]))
    observed_at = datetime(
        int(latest["date"]),
        12,
        31,
        tzinfo=timezone.utc,
    )
    observations = [
        {
            "series_key": "VNM_CPI_INFLATION",
            "label": "Lạm phát CPI Việt Nam",
            "value": float(latest["value"]) / 100,
            "unit": "annual_rate_decimal",
            "observed_at": observed_at,
            "raw": latest,
        }
    ]
    return ConnectorResult(
        source_id="WORLD_BANK_MACRO",
        display_name="World Bank — Vĩ mô Việt Nam",
        category="MACRO",
        source_url=source_url,
        cadence="Hằng năm",
        stale_after_seconds=550 * 24 * 3600,
        observed_at=observed_at,
        observations=observations,
        metadata={
            "official": True,
            "api_last_updated": payload[0].get("lastupdated"),
        },
    )


CONNECTORS: tuple[Callable[[], ConnectorResult], ...] = (
    fetch_pnj_gold,
    fetch_global_gold_market,
    fetch_target_bank_rates,
    fetch_vnstock_vn30,
    fetch_vcbf_nav,
    fetch_world_bank_macro,
)


def _source_id_for(connector: Callable[[], ConnectorResult]) -> str:
    return {
        fetch_pnj_gold: "PNJ_GOLD",
        fetch_global_gold_market: "GLOBAL_GOLD_MARKET",
        fetch_target_bank_rates: "TARGET_BANK_DEPOSIT_RATES",
        fetch_vnstock_vn30: "VNSTOCK_VN30",
        fetch_vcbf_nav: "VCBF_NAV",
        fetch_world_bank_macro: "WORLD_BANK_MACRO",
    }[connector]


def _source_defaults(source_id: str) -> dict[str, Any]:
    return {
        "GLOBAL_GOLD_MARKET": {
            "display_name": "Vàng thế giới COMEX · USD/VND · FRED",
            "category": "GOLD",
            "source_url": "https://finance.yahoo.com/quote/GC=F/history/",
            "cadence": "Cuối ngày/chậm",
            "stale_after_seconds": 3 * 24 * 3600,
        },
        "PNJ_GOLD": {
            "display_name": "PNJ — Giá vàng",
            "category": "GOLD",
            "source_url": "https://edge-api.pnj.io/ecom-frontend/v1/get-gold-price?zone=00",
            "cadence": "Theo ngày",
            "stale_after_seconds": 3 * 24 * 3600,
        },
        "TARGET_BANK_DEPOSIT_RATES": {
            "display_name": "MBBank · Techcombank · VPBank — Lãi suất online",
            "category": "DEPOSIT",
            "source_url": "https://techcombank.com/thong-tin/blog/lai-suat-tiet-kiem?lead=dgmkt-paid-ads",
            "cadence": "Theo ngày; xác nhận lại khi mở sổ",
            "stale_after_seconds": 7 * 24 * 3600,
        },
        "VNSTOCK_VN30": {
            "display_name": "Vnstock — VN30 động và giá thị trường",
            "category": "EQUITY",
            "source_url": "https://vnstocks.com/docs/vnstock/tra-cuu-thong-tin-tham-chieu-reference",
            "cadence": "Cuối ngày/chậm; theo giới hạn cộng đồng",
            "stale_after_seconds": 3 * 24 * 3600,
        },
        "VCBF_NAV": {
            "display_name": "VCBF — NAV quỹ",
            "category": "FUND",
            "source_url": "https://www.vcbf.com/quan-he-nha-dau-tu/bao-cao-cua-cac-quy-mo/bao-cao-thay-doi-gia-tri-tai-san-rong/",
            "cadence": "Theo ngày/tuần",
            "stale_after_seconds": 14 * 24 * 3600,
        },
        "WORLD_BANK_MACRO": {
            "display_name": "World Bank — Vĩ mô Việt Nam",
            "category": "MACRO",
            "source_url": "https://api.worldbank.org/v2/country/VNM/indicator/FP.CPI.TOTL.ZG",
            "cadence": "Hằng năm",
            "stale_after_seconds": 550 * 24 * 3600,
        },
    }[source_id]


def refresh_market_data() -> dict[str, Any]:
    attempted_at = datetime.now().astimezone()
    results: list[ConnectorResult] = []
    errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(CONNECTORS)) as executor:
        futures = {executor.submit(connector): connector for connector in CONNECTORS}
        for future in as_completed(futures):
            connector = futures[future]
            source_id = _source_id_for(connector)
            try:
                results.append(future.result())
            except Exception as exc:
                errors[source_id] = f"{type(exc).__name__}: {exc}"[:700]
                logger.warning("Market connector %s failed: %s", source_id, exc)

    products: list[AssetProduct] = []
    replaced_classes: set[str] = set()
    for result in results:
        save_source_result(
            source_id=result.source_id,
            display_name=result.display_name,
            category=result.category,
            source_url=result.source_url,
            cadence=result.cadence,
            status="CONNECTED",
            attempted_at=attempted_at,
            observed_at=result.observed_at,
            stale_after_seconds=result.stale_after_seconds,
            observations=result.observations,
            metadata=result.metadata,
        )
        products.extend(result.products)
        replaced_classes.update(str(product.asset_class) for product in result.products)

    for source_id, error in errors.items():
        defaults = _source_defaults(source_id)
        save_source_result(
            source_id=source_id,
            **defaults,
            status="ERROR",
            attempted_at=attempted_at,
            observed_at=None,
            observations=[],
            error=error,
        )

    successful_source_ids = {result.source_id for result in results}
    if "TARGET_BANK_DEPOSIT_RATES" in successful_source_ids:
        save_source_result(
            source_id="VIETCOMBANK_RATES",
            display_name="Vietcombank — nguồn tham chiếu cũ",
            category="DEPOSIT",
            source_url="https://vietcombank.com.vn/vi-VN/KHCN/Cong-cu-Tien-ich/KHCN---Lai-suat",
            cadence="Đã thay bằng ba ngân hàng trong đặc tả",
            status="RETIRED",
            attempted_at=attempted_at,
            observed_at=None,
            stale_after_seconds=21 * 24 * 3600,
            observations=[],
            metadata={"retired": True},
        )
        restrict_products_by_source({"VIETCOMBANK_OFFICIAL_INTEREST_RATE"})
    if "VNSTOCK_VN30" in successful_source_ids:
        save_source_result(
            source_id="HOSE_LICENSED_EOD",
            display_name="HOSE — feed được cấp quyền",
            category="EQUITY",
            source_url="https://www.hsx.vn/",
            cadence="Đã thay bằng Vnstock trong phạm vi nghiên cứu",
            status="RETIRED",
            attempted_at=attempted_at,
            observed_at=None,
            stale_after_seconds=3 * 24 * 3600,
            observations=[],
            metadata={"retired": True},
        )

    if products:
        upsert_asset_products(products)
        restrict_mock_products(replaced_classes)
    return market_data_summary()


def market_data_summary() -> dict[str, Any]:
    now = datetime.now().astimezone()
    sources = [
        source
        for source in list_source_status()
        if source["status"] != "RETIRED"
    ]
    connected = 0
    fallback = 0
    latest_success: datetime | None = None
    for source in sources:
        observed = (
            datetime.fromisoformat(source["observed_at"])
            if source.get("observed_at")
            else None
        )
        last_success = (
            datetime.fromisoformat(source["last_success_at"])
            if source.get("last_success_at")
            else None
        )
        age_seconds = (
            max(0, (now - observed.astimezone(now.tzinfo)).total_seconds())
            if observed
            else None
        )
        if source["status"] == "CONNECTED" and (
            age_seconds is None
            or age_seconds <= source["stale_after_seconds"]
        ):
            operational_status = "CONNECTED"
            connected += 1
        elif last_success is not None:
            operational_status = "STALE_FALLBACK"
            fallback += 1
        else:
            operational_status = source["status"]
        source["operational_status"] = operational_status
        source["age_seconds"] = round(age_seconds) if age_seconds is not None else None
        if last_success and (latest_success is None or last_success > latest_success):
            latest_success = last_success

    research_sources = [
        source
        for source in sources
        if source.get("metadata", {}).get("usage_scope") == "RESEARCH_EDUCATION"
        or source.get("metadata", {}).get("official") is False
    ]
    if connected == len(sources) and sources and research_sources:
        mode = "MIXED_OFFICIAL_AND_RESEARCH"
    elif connected == len(sources) and sources:
        mode = "OFFICIAL_DELAYED"
    elif connected or fallback:
        mode = "MIXED_DELAYED_WITH_FALLBACK"
    else:
        mode = "MOCK_FALLBACK"
    snapshot_material = "|".join(
        f"{source['source_id']}:{source.get('observed_at') or 'none'}"
        for source in sources
    )
    digest = sha256(snapshot_material.encode("utf-8")).hexdigest()[:8].upper()
    snapshot_id = f"DELAYED-{now:%Y%m%d}-{digest}" if connected else "MOCK_ASSET_PRODUCT_2026Q3"
    return {
        "mode": mode,
        "snapshot_id": snapshot_id,
        "connected_sources": connected,
        "fallback_sources": fallback,
        "total_sources": len(sources),
        "last_refresh_at": latest_success.isoformat() if latest_success else None,
        "sources": sources,
        "observations": latest_observations(),
    }
