# Monopoly AI Portfolio Lab

Hệ thống hoàn chỉnh cho AI-Quantum Challenge 2026 — đội AQ2026-176, bài toán “Chatbot AI hỗ trợ tiết kiệm và đầu tư đa tài sản”. Ngoài pipeline AI/optimizer của cuộc thi, phiên bản 2.0 có xác thực, phân quyền, lịch sử hội thoại, bảo vệ API, quan sát vận hành và cấu hình triển khai production.

Hệ thống biến hồ sơ tài chính cá nhân thành 2–3 phương án đa tài sản có thể kiểm chứng. Mọi số tiền, tỷ trọng, lợi nhuận kỳ vọng và chỉ số rủi ro đều được tạo bởi rule engine/OR-Tools CP-SAT. LLM chỉ đọc `ReleasedOutput` đã qua Legal/Compliance Gate để diễn giải.

## Chạy nhanh trên Windows

Yêu cầu: CPython 3.13, Node.js 20+.

```powershell
.\run_demo.ps1
```

Mở [http://127.0.0.1:8000](http://127.0.0.1:8000). Tài liệu API ở [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Chạy ở chế độ production

Chế độ này bắt buộc đăng nhập, tự sinh khóa ký phiên an toàn vào `.env`, bật lỗi an toàn,
rate limit, security headers, readiness check và lưu dữ liệu bằng SQLite WAL:

```powershell
.\run_production.ps1
```

Tài khoản đăng ký đầu tiên là quản trị viên. Sau khi tạo tài khoản đầu tiên, nên đặt
`AQ_ALLOW_REGISTRATION=false` trong `.env` rồi khởi động lại nếu hệ thống không cho phép
người dùng tự đăng ký.

Triển khai bằng Docker:

```powershell
$env:AQ_AUTH_SECRET = -join ((1..64) | ForEach-Object { [char](Get-Random -Minimum 33 -Maximum 126) })
docker compose -f docker-compose.production.yml up --build -d
docker compose -f docker-compose.production.yml ps
```

Sao lưu dữ liệu local bằng cách dừng dịch vụ rồi sao chép file SQLite trong `runtime/`.
Với Docker production, sao lưu volume `portfolio-runtime`. Endpoint giám sát:
`GET /health` cho trạng thái ứng dụng và `GET /ready` cho khả năng phục vụ.

Chạy thủ công:

```powershell
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd install --prefix frontend
npm.cmd run build --prefix frontend
.\.venv313\Scripts\python.exe -m backend.scripts.migrate
.\.venv313\Scripts\python.exe -m backend.scripts.seed_mock_data
.\.venv313\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

Hoặc Docker:

```powershell
docker compose up --build
```

## Những gì đã hoàn thiện

- Phase A: schema `AssetProduct`, governance fields, snapshot VN30 ngoài source code, SQLite migrations và mock data.
- Phase B: Cash/Gold/Silver/Deposit/Equity/Bond agents, feasible segments và eligibility reason codes.
- Phase C: CP-SAT coupled optimizer, tier/lô/minimum/rounding, 3 objective profile, volatility, VaR, CVaR, Sharpe, concentration và stress test.
- Phase D: state machine `RESEARCH_EDUCATION`, `LICENSED_ADVISORY`, `BLOCKED`; release policy không tính lại số liệu.
- Phase E: Explanation Agent structured output; OpenAI Responses API tùy chọn và deterministic fallback; chat nạp/rút vốn lập lại kế hoạch.
- Phase F: React dashboard responsive, biểu đồ Recharts, chat, confirmation và màn hình audit 13 bước.
- Production: tài khoản, token ký HMAC, RBAC owner/admin, cô lập dữ liệu theo người dùng,
  lịch sử kế hoạch/chat, migration có phiên bản, SQLite WAL, rate limiting, giới hạn request,
  request ID, security headers, audit API, health/readiness và Docker healthcheck.
- Hồ sơ tài chính riêng gồm nhân khẩu học, dòng tiền/tài sản/nợ/bảo hiểm, nhiều mục tiêu,
  risk tolerance/risk capacity/drawdown và các tùy chọn độ phức tạp, theo dõi, khóa vốn.

Chi tiết kiến trúc: [docs/architecture.md](docs/architecture.md).
Checklist nghiệm thu: [docs/acceptance-checklist.md](docs/acceptance-checklist.md).

## API chính

- `POST /api/v1/recommendations` — chạy pipeline 13 bước.
- `GET /api/v1/recommendations/{id}` — lấy released output.
- `GET /api/v1/recommendations/{id}/audit` — audit trail.
- `POST /api/v1/recommendations/{id}/confirm` — xác nhận con người cho demo.
- `GET /api/v1/recommendations/{id}/report.pdf` — xuất báo cáo PDF có phương án, risk và reason codes.
- `POST /api/v1/chat` — hỏi thêm/nạp/rút và tái lập kế hoạch.
  Endpoint này cũng nhận `recommendation_id=null` để hội thoại, giải thích hồ sơ và
  hướng dẫn trước khi người dùng chạy phân tích.
- `GET /api/v1/products` — product registry.
- `GET /api/v1/internal/recommendations/{id}` — full calculation output phục vụ giám khảo/debug, không phải production public API.
- `POST /api/v1/auth/register` / `login` — đăng ký và đăng nhập.
- `GET /api/v1/auth/me` — danh tính hiện tại.
- `GET /api/v1/me/recommendations` — lịch sử kế hoạch của người dùng.
- `GET/PUT /api/v1/me/profile` — đọc và lưu hồ sơ tài chính mở rộng.
- `GET /api/v1/recommendations/{id}/messages` — lịch sử hội thoại bền vững.

## Explanation Agent qua OpenAI (tùy chọn)

Không có API key, hệ thống vẫn chạy đầy đủ bằng diễn giải deterministic. Muốn bật structured output qua OpenAI:

```powershell
.\configure_openai.ps1
.\run_demo.ps1
```

Script yêu cầu nhập khóa ở chế độ ẩn và lưu vào `.env` đã được `.gitignore` bảo vệ.
Không gửi khóa qua chat và không commit `.env`. Có thể dùng `.\configure_openai.ps1
-FromClipboard` sau khi tự sao chép khóa mới từ OpenAI Platform.

Explanation Agent và chatbot chỉ nhận JSON `ReleasedOutput`; không nhận full product
allocation bị ẩn, không có calculator/tool và không được sửa số. Số liệu trong câu trả
lời chat được dựng bởi lớp deterministic; OpenAI chỉ diễn đạt phần định tính bằng
structured output.

### Groq Free Tier (khuyến nghị cho demo)

Groq dùng endpoint tương thích OpenAI Chat Completions và hỗ trợ strict structured
output trên GPT-OSS. Cấu hình khóa theo cách nhập ẩn:

```powershell
.\configure_groq.ps1
.\run_demo.ps1
```

Hoặc sau khi đã bấm Copy trên Groq Console:

```powershell
.\configure_groq.ps1 -FromClipboard
```

Mặc định hệ thống dùng `openai/gpt-oss-20b`. Đặt `LLM_PROVIDER=groq`, `openai`,
hoặc `deterministic` để chọn provider; nếu provider lỗi, hệ thống tự dùng diễn giải
deterministic mà không làm gián đoạn optimizer.

## Kiểm thử

```powershell
.\.venv313\Scripts\python.exe -m pytest -q
npm.cmd run build --prefix frontend
```

Mock data chỉ dùng cho cuộc thi. Đây không phải tư vấn đầu tư, báo giá thật hoặc cam kết lợi nhuận. Hệ thống chủ động không có chức năng đặt lệnh, margin, bán khống hay tự động thay đổi danh mục.
