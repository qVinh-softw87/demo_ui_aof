# Phụ lục D — Checklist triển khai

Cập nhật: 30/07/2026

| Mã | Trạng thái | Vị trí triển khai |
|---|---|---|
| FR-COM-30 | Done | `backend/app/services/complexity.py::calculate_operational_complexity`; `backend/app/services/optimizer.py::_solve_one`; model `PortfolioScenario`/`ReleasedScenario` |
| FR-COM-31 | Done | `backend/app/services/optimizer.py::optimize_scenarios` vẫn chỉ duyệt ba `SCENARIO_CONFIGS`; không tạo scenario độ phức tạp riêng |
| FR-COM-32 | Done | API `POST /api/v1/recommendations/{id}/scenarios/{scenario_id}/consolidate`; `run_complexity_resolve`; `reoptimize_scenario_for_complexity`; nút UI trong `frontend/src/App.tsx` |
| FR-COM-33 | Done | `backend/app/services/orchestrator.py::_build_selection_decisions`; reason code `EXCLUDED_TO_REDUCE_FRAGMENTATION` theo từng scenario |
| FR-COM-34 | Done | `fragmentation_warning` tính trong `calculate_operational_complexity`; cảnh báo hiển thị trong `complexity-card` |
| NFR-17 | Done | Bộ trọng số đọc từ `backend/app/core/config.py`, version `operational-complexity-v1`; version/breakdown lưu trong full output, released output và audit `MasterOptimizer` |
| NFR-18 | Done | `complexity_resolve_count` giới hạn 0–3; lần thứ tư trả HTTP 409; mỗi lần vẫn chạy `verify_amount_dependent_state` với cycle detection hiện hữu |

## Tiêu chí D.8

- Vốn nhỏ/nhiều sản phẩm: `test_small_capital_many_products_has_high_auditable_warning`.
- Gộp đúng một kịch bản, tối đa ba lần: `test_consolidate_resolves_only_selected_scenario_and_is_bounded_to_three`.
- Thiếu dữ liệu complexity: `test_explanation_refuses_to_invent_missing_complexity_data`.
- Không trộn reason code: `test_fragmentation_reason_code_is_never_liquidity_mismatch` và Compliance Gate `COMPLEXITY_REASON_CODE_MISMATCH`.

## Cấu hình mặc định

- Provider weight: 24
- Product weight: 16
- Fragment weight: 22
- Maturity weight: 10
- Fragment threshold: 12% vốn khả dụng
- Small-capital threshold: 50.000.000 VND
- Warning threshold: 55/100
- Re-solve complexity boost: 25 mỗi lần, tối đa ba lần

Tất cả tham số trên có thể override bằng biến môi trường `AQ_COMPLEXITY_*`; không hard-code rải rác trong logic nghiệp vụ.