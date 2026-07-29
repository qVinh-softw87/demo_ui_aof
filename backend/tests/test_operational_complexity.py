from __future__ import annotations

import asyncio
from datetime import datetime

from httpx import ASGITransport, AsyncClient

from backend.app.main import app, default_planning_request
from backend.app.models import AssetClass, ProductAllocation
from backend.app.services.complexity import (
    calculate_operational_complexity,
    explain_complexity_payload,
    get_complexity_config,
)
from backend.app.services.orchestrator import run_planning_pipeline


def _allocation(index: int, amount: int, provider: str) -> ProductAllocation:
    return ProductAllocation(
        product_id=f"test-product-{index}",
        product_name=f"Sản phẩm {index}",
        provider=provider,
        asset_class=AssetClass.DEPOSIT if index < 4 else AssetClass.BOND_FUND,
        amount=amount,
        weight=amount / 20_000_000,
        expected_return_rate=0.05,
        expected_return_amount=round(amount * 0.05),
        transaction_cost_amount=0,
        liquidity_score=80,
        execution_instruction="Test only",
        source_reference="TEST",
        data_timestamp=datetime.now().astimezone(),
    )


def test_small_capital_many_products_has_high_auditable_warning() -> None:
    allocations = [
        _allocation(index, 4_000_000, f"provider-{min(index, 4)}")
        for index in range(1, 6)
    ]
    score, breakdown, warning = calculate_operational_complexity(
        allocations,
        20_000_000,
        {item.product_id: index * 30 for index, item in enumerate(allocations, 1)},
    )

    assert score >= get_complexity_config().warning_threshold
    assert warning is True
    assert breakdown.distinct_provider_count == 4
    assert breakdown.distinct_product_count == 5
    assert breakdown.smallest_allocation_amount == 4_000_000


def test_consolidate_resolves_only_selected_scenario_and_is_bounded_to_three() -> None:
    async def exercise() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/recommendations",
                json=default_planning_request().model_dump(mode="json"),
            )
            assert created.status_code == 200, created.text
            payload = created.json()
            recommendation_id = payload["released_output"]["recommendation_id"]
            scenarios = payload["released_output"]["scenarios"]
            target = scenarios[1]
            untouched_before = [scenarios[0], scenarios[2]]
            endpoint = (
                f"/api/v1/recommendations/{recommendation_id}/scenarios/"
                f"{target['scenario_id']}/consolidate"
            )

            first = await client.post(endpoint)
            assert first.status_code == 200, first.text
            updated = first.json()["released_output"]["scenarios"]
            assert [updated[0], updated[2]] == untouched_before
            assert updated[1]["complexity_resolve_count"] == 1
            assert len(updated[1]["allocations"]) <= len(target["allocations"])

            second = await client.post(endpoint)
            third = await client.post(endpoint)
            fourth = await client.post(endpoint)
            assert second.status_code == 200
            assert third.status_code == 200
            assert third.json()["released_output"]["scenarios"][1]["complexity_resolve_count"] == 3
            assert fourth.status_code == 409

    asyncio.run(exercise())


def test_explanation_refuses_to_invent_missing_complexity_data() -> None:
    message = explain_complexity_payload(
        {"complexity_breakdown": {"distinct_product_count": 5}},
        "RESEARCH_EDUCATION",
    )
    assert "Thiếu operational_complexity_score" in message
    assert "không được tự ước lượng" in message


def test_fragmentation_reason_code_is_never_liquidity_mismatch() -> None:
    _, full = run_planning_pipeline(default_planning_request(), persist=False)
    decisions = [
        decision
        for scenario in full.scenarios
        for decision in scenario.selection_decisions
        if decision.product_id in scenario.complexity_excluded_product_ids
    ]

    assert decisions
    assert all(
        decision.reason_codes == ["EXCLUDED_TO_REDUCE_FRAGMENTATION"]
        for decision in decisions
    )
    assert all(
        "LIQUIDITY_MISMATCH" not in decision.reason_codes
        for decision in decisions
    )