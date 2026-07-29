from __future__ import annotations

import numpy as np

from backend.app.main import default_planning_request
from backend.app.models import LegalOperatingMode, PlanningRequest
from backend.app.services.chat import interpret_follow_up
from backend.app.services.market_data import _return_over, _rsi14
from backend.app.services.orchestrator import run_planning_pipeline


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
