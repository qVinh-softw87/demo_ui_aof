# Checklist nghiệm thu

## Phase A — Data foundation

- [x] `AssetProduct` đủ trường đặc tả và cấm extra fields.
- [x] Amount-dependent product bắt buộc có `allocation_segments`.
- [x] `USER_REPORTED` bắt buộc có uncertainty bounds.
- [x] Mock data đủ CASH, GOLD, SILVER, DEPOSIT, EQUITY/ETF, BOND FUND và TPCP reference.
- [x] VN30 đọc từ snapshot JSON, không hard-code basket trong source Python.
- [x] SQLite migrations, seed và product registry API.

## Phase B — Asset agents

- [x] Agent riêng cho từng lớp tài sản.
- [x] Eligibility lọc rights, reference-only, minimum capital, horizon, liquidity, customer segment.
- [x] Sản phẩm bị loại có `reason_codes`.
- [x] Feasible segments được giữ nguyên đến optimizer.

## Phase C — Risk & optimizer

- [x] CP-SAT dùng biến integer/binary.
- [x] Giải coupled product amount + asset-class constraints.
- [x] Tier, minimum, maximum, rounding và discrete unit.
- [x] Ba scenario khác trade-off và không trùng signature cho hồ sơ demo.
- [x] Volatility, VaR, CVaR, Sharpe, HHI, liquidity và stress tests.
- [x] Risk capacity ceiling được kiểm tra trước release.
- [x] Infeasibility report trả conflict codes + safe fallback, không tự nới ràng buộc.
- [x] Bounded re-solve tối đa 3 vòng, có state signature, convergence và cycle detection.
- [x] Thời gian hồ sơ demo thấp hơn P95 mục tiêu 30 giây trên máy phát triển.

## Phase D — Legal/compliance

- [x] Ba legal modes.
- [x] Licensed mode thiếu đủ ba bằng chứng chuyển sang blocked.
- [x] Optimizer vẫn chạy trong blocked mode.
- [x] Research mode chỉ phát hành compare-only ở asset-class granularity.
- [x] Output Policy chỉ chọn trường đã tính, không tính lại.

## Phase E — Explanation/chat

- [x] Explanation Agent chỉ nhận released schema.
- [x] Structured output đúng contract.
- [x] OpenAI API tùy chọn; fallback không làm hỏng demo.
- [x] Follow-up “nạp thêm/rút” tạo PlanningRequest mới và chạy lại toàn pipeline.
- [x] Không cam kết lợi nhuận hoặc tạo lệnh mua/bán.

## Phase F — Frontend/demo

- [x] React responsive dashboard.
- [x] Form hồ sơ và vốn khả dụng.
- [x] Scenario tabs, KPI, donut, comparison chart, stress test.
- [x] Chat follow-up.
- [x] Human confirmation.
- [x] Audit trail 13 bước.
- [x] Bảng giải thích sản phẩm được chọn/đủ điều kiện/bị loại với reason codes.
- [x] Xuất báo cáo PDF đa trang, Unicode tiếng Việt và human-readable sources.
- [x] Production build và FastAPI static serving.

## Kiểm thử tự động

- [x] Contract/governance tests.
- [x] Eligibility/segment tests.
- [x] Distinct scenario/risk/reconciliation tests.
- [x] Legal perimeter test.
- [x] Chat cash-flow parser test.
- [x] API persistence/audit/confirmation integration test.
- [x] Password hashing có salt và kiểm tra mật khẩu.
- [x] Đăng ký/đăng nhập/token và API bắt buộc xác thực.
- [x] Security headers và request ID.

## Production hardening

- [x] Tài khoản người dùng, owner isolation và vai trò admin/user.
- [x] Lịch sử recommendation và lịch sử chat theo người dùng.
- [x] PDF, audit, chat, confirmation được kiểm tra quyền sở hữu.
- [x] Rate limiting, request-size limit, CSP, HSTS và lỗi production không lộ stack trace.
- [x] API event log có request ID, status code và latency.
- [x] Migration registry, SQLite WAL và busy timeout.
- [x] Health/readiness endpoints và Docker healthcheck.
- [x] Script production tự sinh khóa ký phiên.
- [x] Groq/OpenAI provider abstraction với deterministic fallback.
- [x] Giao diện đăng nhập/đăng ký và Bearer token cho toàn bộ API riêng tư.
- [x] Trung tâm hồ sơ tách khỏi chatbot với 5 nhóm dữ liệu và nhiều mục tiêu.
- [x] Hồ sơ mở rộng được lưu bền vững theo tài khoản.
- [x] Giới hạn số sản phẩm và mức chấp nhận khóa vốn đi vào optimizer/eligibility.
