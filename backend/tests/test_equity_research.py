from datetime import date, timedelta

from backend.app.services.equity_research import (
    _CACHE,
    _company_identity,
    _technical_analysis,
    get_equity_research,
)


def test_technical_analysis_computes_price_trend_and_rsi() -> None:
    start = date(2026, 1, 1)
    rows = [
        {
            "time": (start + timedelta(days=index)).isoformat(),
            "close": 20 + index * 0.1,
            "volume": 1_000_000 + index * 1_000,
        }
        for index in range(80)
    ]

    price_facts, technical_facts, observed_at = _technical_analysis(
        rows,
        fallback_price=27_900,
    )

    assert observed_at is not None
    assert any("27.900 VND" in item for item in price_facts)
    assert any("xu hướng tăng" in item for item in technical_facts)
    assert any("RSI 14 phiên" in item for item in technical_facts)
    assert any("Vùng giá quan sát 20 phiên" in item for item in technical_facts)


def test_technical_analysis_scales_vnstock_thousand_vnd_without_fallback() -> None:
    start = date(2026, 4, 1)
    rows = [
        {
            "time": (start + timedelta(days=index)).isoformat(),
            "close": 21.0 + index * 0.02,
        }
        for index in range(70)
    ]

    price_facts, technical_facts, _ = _technical_analysis(rows, fallback_price=None)

    assert any("22.380 VND" in item for item in price_facts)
    assert any("MA20" in item and "VND" in item for item in technical_facts)


def test_company_identity_uses_verified_fields_and_safe_fallback() -> None:
    company_name, facts = _company_identity(
        "GVR",
        [
            {
                "company_name": "Tập đoàn Công nghiệp Cao su Việt Nam - CTCP",
                "industry": "Cao su",
                "exchange": "HOSE",
                "outstanding_share": 4_000_000_000,
            }
        ],
    )

    assert company_name.startswith("Tập đoàn Công nghiệp Cao su")
    assert any("HOSE" in item for item in facts)
    assert any("Cao su" in item for item in facts)

    fallback_name, fallback_facts = _company_identity("FPT", [])
    assert fallback_name == "Công ty Cổ phần FPT"
    assert any("Công nghệ" in item for item in fallback_facts)


def test_acb_research_memo_uses_latest_dated_views_and_downside(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.services.equity_research.list_source_status",
        lambda: [],
    )
    _CACHE.clear()

    result = get_equity_research("ACB", fallback_price=22_750)
    memo = " ".join(
        result.investment_thesis
        + result.earnings_facts
        + result.valuation_facts
        + result.quality_facts
        + result.analyst_views
        + result.catalysts
        + result.risk_facts
        + result.sources
    )

    assert result.company_name == "Ngân hàng TMCP Á Châu"
    assert "SSI" in memo and "12/05/2026" in memo
    assert "27.500 đồng" in memo
    assert "KAFI" in memo and "29.500 đồng" in memo
    assert "23/01/2025" in memo and "không được dùng" in memo
    assert "nợ xấu" in memo.lower()
    assert "NIM" in memo
    assert "mất hiệu lực" in memo
