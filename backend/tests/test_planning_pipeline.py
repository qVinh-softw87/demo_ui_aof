from __future__ import annotations

import asyncio
from io import BytesIO

from httpx import ASGITransport, AsyncClient
from pypdf import PdfReader

from backend.app.main import app, default_planning_request
from backend.app.models import (
    LegalOperatingMode,
    OutputReleaseType,
    PlanningRequest,
    SelectionStatus,
)
from backend.app.services.chat import (
    build_replanning_explanation,
    interpret_follow_up,
    resolve_scenario_id,
)
from backend.app.services.orchestrator import run_planning_pipeline
from backend.app.services.reports import generate_recommendation_pdf


def test_research_pipeline_returns_distinct_feasible_compare_only_scenarios() -> None:
    request = default_planning_request()
    response, full = run_planning_pipeline(request, persist=False)

    released = response.released_output
    assert released.output_release_type == OutputReleaseType.COMPARE_ONLY
    assert len(released.scenarios) == 3
    assert not full.infeasibility.is_infeasible
    assert full.bounded_resolve.converged
    assert not full.bounded_resolve.cycle_detected
    assert 1 <= len(full.bounded_resolve.iterations) <= 3
    assert full.bounded_resolve.iterations[-1].status == "STABLE"
    assert released.selection_decisions == full.selection_decisions
    statuses = {decision.status for decision in released.selection_decisions}
    assert SelectionStatus.SELECTED_INTERNAL in statuses
    assert SelectionStatus.REJECTED in statuses

    signatures = set()
    for internal, public in zip(full.scenarios, released.scenarios, strict=True):
        assert internal.allocated_amount + internal.residual_cash == internal.investable_capital
        assert internal.risk_metrics.within_risk_ceiling
        assert public.allocation_granularity == "ASSET_CLASS"
        assert all(not hasattr(item, "product_id") for item in public.allocations)
        assert len(public.allocation_explanations) == len(public.allocations)
        assert {
            item.asset_class for item in public.allocation_explanations
        } == {
            item.asset_class for item in public.allocations
        }
        assert all(
            item.portfolio_role
            and item.allocation_reason
            and item.limiting_factor
            and item.change_trigger
            and item.expected_return_and_risk
            and item.cost_and_liquidity
            and item.execution_conditions
            and item.adverse_scenario
            and item.data_evidence
            and item.result_sensitive_assumptions
            for item in public.allocation_explanations
        )
        assert len(public.monitoring_triggers) == 7
        assert len(public.withdrawal_options) == 4
        assert public.source_summary
        assert public.assumptions_that_change_result
        if any(
            allocation.asset_class.value == "DEPOSIT"
            for allocation in internal.product_allocations
        ):
            assert public.deposit_implementation
            assert all(
                item.bank
                and item.amount > 0
                and item.annual_rate > 0
                and item.conditions
                and item.data_timestamp
                for item in public.deposit_implementation
            )
        signatures.add(
            tuple((str(item.asset_class), item.amount) for item in public.allocations)
        )
    assert len(signatures) == 3


def test_licensed_mode_without_complete_evidence_is_blocked_after_full_calculation() -> None:
    payload = default_planning_request().model_dump()
    payload["requested_mode"] = LegalOperatingMode.LICENSED_ADVISORY
    request = PlanningRequest.model_validate(payload)

    response, full = run_planning_pipeline(request, persist=False)

    assert full.scenarios, "Optimizer must still run before the release policy."
    assert response.released_output.output_release_type == OutputReleaseType.BLOCKED
    assert response.released_output.scenarios == []


def test_licensed_advisory_releases_product_level_evidence_and_monitoring() -> None:
    payload = default_planning_request().model_dump()
    payload["requested_mode"] = LegalOperatingMode.LICENSED_ADVISORY
    payload["legal_evidence"] = {
        "licensed_entity_verified": True,
        "advisory_contract_verified": True,
        "responsible_advisor_verified": True,
    }
    request = PlanningRequest.model_validate(payload)

    response, _ = run_planning_pipeline(request, persist=False)
    released = response.released_output

    assert released.output_release_type == OutputReleaseType.ADVISORY_SELECTED
    assert len(released.scenarios) == 3
    assert released.scenarios[0].recommendation_role == "RECOMMENDED"
    assert all(
        scenario.recommendation_role == "ALTERNATIVE"
        for scenario in released.scenarios[1:]
    )
    for scenario in released.scenarios:
        assert scenario.allocation_granularity == "PRODUCT"
        assert all(hasattr(item, "product_id") for item in scenario.allocations)
        assert len(scenario.allocation_explanations) == len(scenario.allocations)
        assert all(
            item.product_id
            and item.product_name
            and item.provider
            and item.data_evidence
            and item.execution_conditions
            for item in scenario.allocation_explanations
        )
        assert len(scenario.monitoring_triggers) == 7
        assert len(scenario.withdrawal_options) == 4
        assert len(scenario.source_summary) == len(scenario.allocations)


def test_advisor_pdf_is_unicode_readable_and_contains_decision_evidence() -> None:
    payload = default_planning_request().model_dump()
    payload["requested_mode"] = LegalOperatingMode.LICENSED_ADVISORY
    payload["legal_evidence"] = {
        "licensed_entity_verified": True,
        "advisory_contract_verified": True,
        "responsible_advisor_verified": True,
    }
    response, _ = run_planning_pipeline(
        PlanningRequest.model_validate(payload),
        persist=False,
    )

    pdf_bytes = generate_recommendation_pdf(response.released_output)
    reader = PdfReader(BytesIO(pdf_bytes))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(reader.pages) >= 8
    assert "Báo cáo phân bổ tài sản" in extracted
    assert "Vì sao hình thành tỷ trọng" in extracted
    assert "Phân tích chi tiết từng sản phẩm" in extracted
    assert "Rủi ro và điều kiện vô hiệu luận điểm" in extracted
    assert "Vì sao sản phẩm được chọn hoặc bị loại" in extracted
    assert "Nguồn và thời điểm cập nhật" in extracted
    assert "BĂ¡o cĂ¡o" not in extracted
    assert "\ufffd" not in extracted


def test_follow_up_cash_flow_is_parsed_and_replanned() -> None:
    request = default_planning_request()
    reply, revised = interpret_follow_up(
        request,
        "Nếu tôi nạp thêm 50 triệu thì sao?",
    )
    assert reply.intent == "ADD_CAPITAL"
    assert reply.replanning_required
    assert revised is not None
    assert revised.profile.total_assets == request.profile.total_assets + 50_000_000

    reply, revised = interpret_follow_up(
        request,
        "Tôi cần rút 20 triệu trong 3 tháng tới",
    )
    assert reply.intent == "WITHDRAWAL_NEED"
    assert revised is not None
    assert revised.profile.liquidity_need == 20_000_000
    assert revised.profile.liquidity_need_months == 3


def test_replan_explains_before_after_and_follow_up_change_question() -> None:
    request = default_planning_request()
    request = request.model_copy(
        update={
            "profile": request.profile.model_copy(
                update={
                    "liquidity_need": 60_000_000,
                    "liquidity_need_months": 6,
                }
            )
        }
    )
    before, _ = run_planning_pipeline(request, persist=False)
    active = before.released_output.scenarios[0]
    reply, revised = interpret_follow_up(
        request,
        "Tôi cần rút 20 triệu",
        before.released_output,
        active.scenario_id,
    )
    assert revised is not None

    after, _ = run_planning_pipeline(revised, persist=False)
    reply.replanned_recommendation = after
    reply = build_replanning_explanation(
        reply,
        original=request,
        revised=revised,
        before_output=before.released_output,
        after_output=after.released_output,
        active_scenario_id=active.scenario_id,
    )

    assert reply.focused_scenario_id
    assert len(reply.sections) == 5
    assert "[PORTFOLIO_CHANGE]" not in reply.message
    assert "60.000.000 VND" in reply.sections[0].body
    assert "20.000.000 VND" in reply.sections[0].body
    assert "nghiệm tối ưu vẫn giống phương án cũ" in reply.sections[1].body
    assert "Không có khoản phân bổ nào thay đổi" in reply.sections[2].body
    assert "Lưu ý: hệ thống đang hiểu" in reply.sections[4].body

    history_content = "\n".join(
        ["[PORTFOLIO_CHANGE]", reply.message]
        + [f"{section.title}: {section.body}" for section in reply.sections]
    )[:1_200]
    follow_up, follow_up_revised = interpret_follow_up(
        revised,
        "Đã thay đổi gì so với trước?",
        after.released_output,
        reply.focused_scenario_id,
        [{"role": "assistant", "content": history_content}],
    )

    assert follow_up_revised is None
    assert follow_up.intent == "EXPLAIN_REPLANNING_CHANGE"
    assert "danh mục không đổi" in follow_up.sections[0].body
    assert "60.000.000 VND" in follow_up.sections[0].body


def test_advisor_replan_names_changed_products_not_only_asset_classes() -> None:
    payload = default_planning_request().model_dump()
    payload["requested_mode"] = LegalOperatingMode.LICENSED_ADVISORY
    payload["legal_evidence"] = {
        "licensed_entity_verified": True,
        "advisory_contract_verified": True,
        "responsible_advisor_verified": True,
    }
    request = PlanningRequest.model_validate(payload)
    before, _ = run_planning_pipeline(request, persist=False)
    active = before.released_output.scenarios[1]
    reply, revised = interpret_follow_up(
        request,
        "Nạp thêm 50 triệu",
        before.released_output,
        active.scenario_id,
    )
    assert revised is not None

    after, _ = run_planning_pipeline(revised, persist=False)
    reply = build_replanning_explanation(
        reply,
        original=request,
        revised=revised,
        before_output=before.released_output,
        after_output=after.released_output,
        active_scenario_id=active.scenario_id,
    )

    assert reply.sections[2].title == "3. Sản phẩm thay đổi cụ thể"
    assert any(
        allocation.product_name in reply.sections[2].body
        for allocation in active.allocations
    )
    assert "50.000.000 VND" in reply.sections[0].body


def test_chat_api_returns_replanning_memo_instead_of_generic_acknowledgement() -> None:
    async def exercise_api() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            planned = await client.post(
                "/api/v1/recommendations",
                json=default_planning_request().model_dump(mode="json"),
            )
            assert planned.status_code == 200, planned.text
            released = planned.json()["released_output"]

            replanned = await client.post(
                "/api/v1/chat",
                json={
                    "recommendation_id": released["recommendation_id"],
                    "active_scenario_id": released["scenarios"][0]["scenario_id"],
                    "message": "Tôi cần rút 20 triệu",
                    "conversation_history": [],
                },
            )
            assert replanned.status_code == 200, replanned.text
            payload = replanned.json()
            assert payload["replanning_required"]
            assert payload["replanned_recommendation"]
            assert len(payload["sections"]) == 5
            assert "danh mục không đổi" in payload["message"]
            assert payload["focused_scenario_id"] != released["scenarios"][0]["scenario_id"]

            follow_up = await client.post(
                "/api/v1/chat",
                json={
                    "recommendation_id": payload["recommendation_id"],
                    "active_scenario_id": payload["focused_scenario_id"],
                    "message": "Đã thay đổi gì?",
                    "conversation_history": [],
                },
            )
            assert follow_up.status_code == 200, follow_up.text
            follow_up_payload = follow_up.json()
            assert follow_up_payload["intent"] == "EXPLAIN_REPLANNING_CHANGE"
            assert "danh mục không đổi" in follow_up_payload["sections"][0]["body"]

    asyncio.run(exercise_api())


def test_chat_explains_active_scenario_with_structured_evidence() -> None:
    request = default_planning_request()
    response, _ = run_planning_pipeline(request, persist=False)
    active = response.released_output.scenarios[1]

    reply, revised = interpret_follow_up(
        request,
        "Rủi ro lớn nhất là gì?",
        response.released_output,
        active.scenario_id,
    )

    assert revised is None
    assert reply.intent == "EXPLAIN"
    assert not reply.replanning_required
    assert active.name in reply.message
    assert len(reply.sections) >= 2
    assert any("VaR 95%" in section.body for section in reply.sections)
    assert reply.suggested_questions


def test_chat_resolves_natural_scenario_references() -> None:
    request = default_planning_request()
    response, _ = run_planning_pipeline(request, persist=False)
    scenarios = response.released_output.scenarios

    assert (
        resolve_scenario_id(
            response.released_output,
            "Còn phương án cân bằng thì sao?",
            scenarios[0].scenario_id,
        )
        == scenarios[1].scenario_id
    )
    assert (
        resolve_scenario_id(
            response.released_output,
            "Giải thích phương án thứ ba giúp tôi",
            scenarios[0].scenario_id,
        )
        == scenarios[2].scenario_id
    )

    weakness_reply, revised = interpret_follow_up(
        request,
        "Vậy điểm yếu lớn nhất của nó là gì?",
        response.released_output,
        scenarios[1].scenario_id,
        [
            {
                "role": "user",
                "content": "Phương án cân bằng hợp với người như thế nào?",
            },
            {
                "role": "assistant",
                "content": "Phương án này cân bằng thanh khoản, ổn định và tăng trưởng.",
            },
        ],
    )
    assert revised is None
    assert any(
        section.title == "Đánh đổi cần chấp nhận"
        for section in weakness_reply.sections
    )


def test_chat_names_bank_tenor_and_amount_from_released_optimizer_output() -> None:
    request = default_planning_request()
    response, _ = run_planning_pipeline(request, persist=False)
    active = response.released_output.scenarios[0]

    reply, revised = interpret_follow_up(
        request,
        "Là gửi ngân hàng nào, kỳ hạn nào và số vốn bao nhiêu?",
        response.released_output,
        active.scenario_id,
    )

    assert revised is None
    assert reply.intent == "EXPLAIN_DEPOSIT_IMPLEMENTATION"
    assert reply.generated_by == "DATA_REGISTRY"
    assert active.deposit_implementation
    assert len(reply.sections) == len(active.deposit_implementation)
    assert all(
        any(item.bank in section.title for item in active.deposit_implementation)
        and "Lãi suất tham chiếu" in section.body
        for section in reply.sections
    )


def test_chat_explains_each_asset_class_with_amount_role_and_limits() -> None:
    request = default_planning_request()
    response, _ = run_planning_pipeline(request, persist=False)
    active = response.released_output.scenarios[0]

    reply, revised = interpret_follow_up(
        request,
        "Giải thích cụ thể cách phân bổ tài sản",
        response.released_output,
        active.scenario_id,
    )

    assert revised is None
    allocation_sections = [
        section
        for section in reply.sections
        if "Vai trò:" in section.body and "Điểm giới hạn:" in section.body
    ]
    assert len(allocation_sections) == len(active.allocations)
    assert all(
        any(str(allocation.amount)[:3] in section.title.replace(".", "") for section in allocation_sections)
        for allocation in active.allocations
    )


def test_chat_can_converse_before_a_recommendation_exists() -> None:
    request = default_planning_request()

    reply, revised = interpret_follow_up(
        request,
        "Xin chào, bạn có thể giúp tôi những gì?",
    )

    assert revised is None
    assert reply.intent == "EXPLAIN"
    assert not reply.replanning_required
    assert "Chào" in reply.message
    assert len(reply.sections) >= 1
    assert reply.suggested_questions


def test_chat_answers_data_provenance_from_registry_without_llm_inference() -> None:
    request = default_planning_request()
    response, _ = run_planning_pipeline(request, persist=False)

    reply, revised = interpret_follow_up(
        request,
        "Dữ liệu này lấy từ đâu và cập nhật lúc nào?",
        response.released_output,
        response.released_output.scenarios[0].scenario_id,
    )

    assert revised is None
    assert reply.intent == "DATA_PROVENANCE"
    assert reply.generated_by == "DATA_REGISTRY"
    assert response.released_output.data_snapshot in reply.message
    assert any("Nguồn và thời điểm quan sát" == section.title for section in reply.sections)


def test_research_chat_does_not_invent_fpt_product_allocation() -> None:
    request = default_planning_request()
    response, _ = run_planning_pipeline(request, persist=False)
    growth = response.released_output.scenarios[2]

    reply, revised = interpret_follow_up(
        request,
        "Tại sao ở tăng trưởng lại đầu tư FPT, đầu tư vào đấy bao nhiêu cổ phiếu?",
        response.released_output,
        growth.scenario_id,
    )

    assert revised is None
    assert reply.intent == "EXPLAIN_PRODUCT_ALLOCATION"
    assert "chưa thể khẳng định" in reply.message.lower()
    assert "không có quyết định chọn mã" in reply.message.lower()


def test_advisor_chat_explains_selected_equity_with_units_and_source() -> None:
    payload = default_planning_request().model_dump()
    payload["requested_mode"] = LegalOperatingMode.LICENSED_ADVISORY
    payload["legal_evidence"] = {
        "licensed_entity_verified": True,
        "advisory_contract_verified": True,
        "responsible_advisor_verified": True,
    }
    request = PlanningRequest.model_validate(payload)
    response, _ = run_planning_pipeline(request, persist=False)
    growth = response.released_output.scenarios[2]
    equity = next(
        item for item in growth.allocations if item.asset_class.value == "EQUITY"
    )
    ticker = equity.product_name.split("—", 1)[0].strip()

    reply, revised = interpret_follow_up(
        request,
        f"Tại sao phương án tăng trưởng chọn {ticker}, đầu tư bao nhiêu cổ phiếu?",
        response.released_output,
        growth.scenario_id,
    )

    assert revised is None
    assert reply.intent == "EXPLAIN_PRODUCT_ALLOCATION"
    assert equity.product_name in reply.message
    assert str(equity.amount)[:3] in reply.message.replace(".", "")
    assert any(section.title == "Số vốn và số lượng minh họa" for section in reply.sections)
    assert any(section.title == "Nguồn, thời điểm và giới hạn" for section in reply.sections)

    acb_reply, acb_revised = interpret_follow_up(
        request,
        "Tại sao mua ACB?",
        response.released_output,
        growth.scenario_id,
    )
    acb_text = " ".join(
        [acb_reply.message]
        + [f"{section.title} {section.body}" for section in acb_reply.sections]
    )
    assert acb_revised is None
    assert acb_reply.intent == "EXPLAIN_PRODUCT_ALLOCATION"
    assert "27.500 đồng" in acb_text
    assert "29.500 đồng" in acb_text
    assert "12/05/2026" in acb_text
    assert "rủi ro" in acb_text.lower()


def test_end_to_end_api_persists_audit_and_confirmation() -> None:
    async def exercise_api() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            result = await client.post(
                "/api/v1/recommendations",
                json=default_planning_request().model_dump(mode="json"),
            )
            assert result.status_code == 200, result.text
            payload = result.json()
            recommendation_id = payload["released_output"]["recommendation_id"]
            scenario_id = payload["released_output"]["scenarios"][0]["scenario_id"]

            audit = await client.get(
                f"/api/v1/recommendations/{recommendation_id}/audit"
            )
            assert audit.status_code == 200
            assert len(audit.json()) == 13

            confirmation = await client.post(
                f"/api/v1/recommendations/{recommendation_id}/confirm",
                json={
                    "scenario_id": scenario_id,
                    "confirmed": True,
                    "note": "Demo test only",
                },
            )
            assert confirmation.status_code == 200
            assert confirmation.json()["status"] == "HUMAN_CONFIRMED_FOR_DEMO_ONLY"

            report = await client.get(
                f"/api/v1/recommendations/{recommendation_id}/report.pdf"
            )
            assert report.status_code == 200
            assert report.headers["content-type"] == "application/pdf"
            assert report.content.startswith(b"%PDF")
            reader = PdfReader(BytesIO(report.content))
            assert len(reader.pages) >= 2
            extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
            assert recommendation_id in extracted
            assert "Mã kiểm soát" in extracted

    asyncio.run(exercise_api())
