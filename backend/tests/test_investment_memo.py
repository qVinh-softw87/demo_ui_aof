from __future__ import annotations

import pytest

from backend.app.main import default_planning_request
from backend.app.models import LegalOperatingMode, PlanningRequest
from backend.app.services.chat import interpret_follow_up
from backend.app.services.investment_memo import build_investment_memo
from backend.app.services.orchestrator import run_planning_pipeline


@pytest.fixture(scope="module")
def advisor_result():
    payload = default_planning_request().model_dump()
    payload["requested_mode"] = LegalOperatingMode.LICENSED_ADVISORY
    payload["legal_evidence"] = {
        "licensed_entity_verified": True,
        "advisory_contract_verified": True,
        "responsible_advisor_verified": True,
    }
    request = PlanningRequest.model_validate(payload)
    response, _ = run_planning_pipeline(request, persist=False)
    return request, response.released_output


def _allocation_and_scenario(released, asset_class: str):
    for scenario in released.scenarios:
        for allocation in scenario.allocations:
            if allocation.asset_class.value == asset_class:
                return allocation, scenario
    raise AssertionError(f"No selected {asset_class} product in Advisor scenarios")


@pytest.mark.parametrize(
    "asset_class",
    ["CASH", "DEPOSIT", "GOLD", "BOND_FUND", "ETF", "EQUITY"],
)
def test_every_selected_product_builds_evidence_first_memo(
    advisor_result,
    asset_class: str,
) -> None:
    _, released = advisor_result
    allocation, scenario = _allocation_and_scenario(released, asset_class)
    explanation = next(
        item
        for item in scenario.allocation_explanations
        if item.product_id == allocation.product_id
    )

    memo = build_investment_memo(
        allocation=allocation,
        explanation=explanation,
        scenario=scenario,
    )

    assert memo.thesis
    assert memo.proof_chain
    assert any(str(allocation.amount)[:3] in item.replace(".", "") for item in memo.proof_chain)
    assert memo.risks
    assert memo.alternatives
    assert memo.implementation
    assert memo.sources


def test_deposit_memo_proves_rate_interest_maturity_and_compares_banks(
    advisor_result,
) -> None:
    _, released = advisor_result
    allocation, scenario = _allocation_and_scenario(released, "DEPOSIT")
    explanation = next(
        item
        for item in scenario.allocation_explanations
        if item.product_id == allocation.product_id
    )

    memo = build_investment_memo(
        allocation=allocation,
        explanation=explanation,
        scenario=scenario,
    )
    evidence = " ".join(memo.market_evidence + memo.alternatives)

    assert "lãi suất tham chiếu" in evidence
    assert "lãi cuối kỳ" in evidence
    assert "giá trị đáo hạn" in evidence
    assert any(bank in evidence for bank in ["MBBank", "Techcombank", "VPBank"])


def test_gold_and_bond_fund_memos_use_market_specific_evidence(
    advisor_result,
) -> None:
    _, released = advisor_result
    gold, gold_scenario = _allocation_and_scenario(released, "GOLD")
    gold_explanation = next(
        item
        for item in gold_scenario.allocation_explanations
        if item.product_id == gold.product_id
    )
    gold_memo = build_investment_memo(
        allocation=gold,
        explanation=gold_explanation,
        scenario=gold_scenario,
    )
    gold_text = " ".join(gold_memo.market_evidence + gold_memo.risks)
    assert "COMEX" in gold_text
    assert "DXY" in gold_text
    assert "Chênh lệch mua–bán" in gold_text

    bond, bond_scenario = _allocation_and_scenario(released, "BOND_FUND")
    bond_explanation = next(
        item
        for item in bond_scenario.allocation_explanations
        if item.product_id == bond.product_id
    )
    bond_memo = build_investment_memo(
        allocation=bond,
        explanation=bond_explanation,
        scenario=bond_scenario,
    )
    bond_text = " ".join(bond_memo.market_evidence + bond_memo.risks)
    assert "NAV" in bond_text
    assert "lãi suất" in bond_text.lower()
    assert "rủi ro tín dụng" in bond_text.lower()


@pytest.mark.parametrize(
    "asset_class",
    ["CASH", "DEPOSIT", "GOLD", "BOND_FUND", "ETF", "EQUITY"],
)
def test_chat_returns_same_investment_memo_contract_for_every_product(
    advisor_result,
    asset_class: str,
) -> None:
    request, released = advisor_result
    allocation, scenario = _allocation_and_scenario(released, asset_class)

    reply, revised = interpret_follow_up(
        request,
        f"Vì sao chọn {allocation.product_name}? Hãy đưa luận điểm và chứng minh.",
        released,
        scenario.scenario_id,
    )
    titles = {section.title for section in reply.sections}

    assert revised is None
    assert reply.intent == "EXPLAIN_PRODUCT_ALLOCATION"
    assert allocation.product_name in reply.message
    assert {
        "Kết luận và luận điểm đầu tư",
        "Số vốn và số lượng minh họa",
        "Dẫn chứng sản phẩm và thị trường",
        "Chất xúc tác cần theo dõi",
        "Rủi ro và điều kiện làm luận điểm mất hiệu lực",
        "So sánh với phương án thay thế",
        "Điều kiện thực hiện và tính lại",
        "Nguồn, thời điểm và giới hạn",
    }.issubset(titles)
    assert all(len(section.body) <= 1_500 for section in reply.sections)


def test_advisor_general_answer_keeps_panorama_instead_of_truncating(
    advisor_result,
) -> None:
    request, released = advisor_result
    scenario = released.scenarios[0]

    reply, revised = interpret_follow_up(
        request,
        "Hãy đánh giá toàn cảnh phương án này như một chuyên gia đầu tư.",
        released,
        scenario.scenario_id,
    )
    titles = {section.title for section in reply.sections}

    assert revised is None
    assert {
        "Toàn cảnh phù hợp với hồ sơ và mục tiêu",
        "Cấu trúc danh mục và động lực lợi nhuận",
        "Rủi ro toàn danh mục và kịch bản bất lợi",
        "Bối cảnh dữ liệu, thị trường và giả định",
        "Đánh đổi và điều kiện phải tái đánh giá",
    }.issubset(titles)
