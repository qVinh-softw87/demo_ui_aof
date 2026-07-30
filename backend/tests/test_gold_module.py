from __future__ import annotations

import numpy as np
import pytest

from backend.app.main import default_planning_request
from backend.app.models import LegalOperatingMode, PlanningRequest
from backend.app.services.chat import interpret_follow_up
from backend.app.services.market_data import (
    PNJ_GOLD_API_URL,
    PNJ_GOLD_PAGE_URL,
    _pnj_gold_result_from_payload,
    _return_over,
    _rsi14,
)
from backend.app.services.orchestrator import run_planning_pipeline


def _pnj_payload() -> dict:
    return {
        "data": [
            {
                "masp": "SJC",
                "tensp": "Vàng miếng SJC 999.9",
                "giaban": 14_170,
                "giamua": 13_770,
            },
            {
                "masp": "N24K",
                "tensp": "Nhẫn Trơn PNJ 999.9",
                "giaban": 14_160,
                "giamua": 13_670,
            },
        ],
        "chinhanh": "hochiminh",
        "updateDate": "30/07/2026 13:51:46",
    }


def test_pnj_gold_source_uses_public_page_and_validates_quote_units() -> None:
    result = _pnj_gold_result_from_payload(_pnj_payload())
    products = {product.product_id: product for product in result.products}

    assert result.source_id == "PNJ_GOLD"
    assert result.source_url == PNJ_GOLD_PAGE_URL
    assert result.metadata["api_url"] == PNJ_GOLD_API_URL
    assert result.metadata["quote_unit"] == "1.000 VND/chi"
    assert products["gold-ring-pnj-delayed"].minimum_investment == 14_160_000
    assert products["gold-sjc-pnj-delayed"].minimum_investment == 141_700_000
    assert all(
        product.source_registry_id == result.source_id
        for product in result.products
    )
    assert all(
        PNJ_GOLD_PAGE_URL in product.source_reference
        for product in result.products
    )


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("giaban", 120),
        ("giamua", 200_000),
    ],
)
def test_pnj_gold_rejects_implausible_quote_units(
    field_name: str,
    bad_value: int,
) -> None:
    payload = _pnj_payload()
    payload["data"][0][field_name] = bad_value

    with pytest.raises(ValueError, match="implausible"):
        _pnj_gold_result_from_payload(payload)


def test_pnj_gold_rejects_inverted_customer_buy_and_sell_prices() -> None:
    payload = _pnj_payload()
    payload["data"][0]["giaban"] = 13_000
    payload["data"][0]["giamua"] = 14_000

    with pytest.raises(ValueError, match="below sell-back"):
        _pnj_gold_result_from_payload(payload)


def test_world_gold_chart_metrics_are_computed_from_daily_closes() -> None:
    rows = [
        {
            "timestamp": index,
            "close": 3_000 + index * 5,
        }
        for index in range(80)
    ]
    closes = np.asarray([row["close"] for row in rows], dtype=float)

    assert _return_over(rows, 21) > 0
    assert 50 < _rsi14(closes) <= 100


def test_optimizer_allocates_whole_physical_gold_units_when_feasible() -> None:
    request = default_planning_request()
    _, full = run_planning_pipeline(request, persist=False)

    assert len(full.scenarios) == 3
    for scenario in full.scenarios:
        gold = [
            item for item in scenario.product_allocations
            if item.asset_class.value == "GOLD"
        ]
        assert gold
        assert all(item.estimated_units and item.estimated_units >= 1 for item in gold)
        assert all("STRATEGIC_GOLD_DIVERSIFIER_FLOOR" in item.reason_codes for item in gold)
        assert all(
            round((item.reference_price or 0) * (item.estimated_units or 0))
            == item.amount
            for item in gold
        )


def test_advisor_chat_explains_gold_with_local_global_technical_and_macro_sections() -> None:
    payload = default_planning_request().model_dump()
    payload["requested_mode"] = LegalOperatingMode.LICENSED_ADVISORY
    payload["legal_evidence"] = {
        "licensed_entity_verified": True,
        "advisory_contract_verified": True,
        "responsible_advisor_verified": True,
    }
    request = PlanningRequest.model_validate(payload)
    response, _ = run_planning_pipeline(request, persist=False)
    active = response.released_output.scenarios[1]

    reply, revised = interpret_follow_up(
        request,
        "Vì sao có vàng, phân tích giá SJC, chart vàng thế giới và vĩ mô?",
        response.released_output,
        active.scenario_id,
    )

    assert revised is None
    assert reply.intent == "EXPLAIN_GOLD_ALLOCATION"
    titles = {section.title for section in reply.sections}
    assert "Giá SJC/vàng nhẫn trong nước" in titles
    assert "Chart vàng thế giới" in titles
    assert "Phân tích kỹ thuật vàng thế giới" in titles
    assert "Vĩ mô tác động đến vàng" in titles
