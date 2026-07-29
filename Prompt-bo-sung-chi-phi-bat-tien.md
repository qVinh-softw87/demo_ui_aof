# PROMPT BỔ SUNG
## Thêm chiều "Chi phí bất tiện vận hành" (Operational Inconvenience Cost) vào 3 kịch bản phân bổ

> Dùng tiếp nối prompt gốc "Prompt-xay-dung-chatbot-AI-Quantum-Challenge.md". Dán đoạn dưới đây cho Claude Code để chỉnh sửa Master Optimizer + Explanation Agent + UI hiện có, **không phải viết lại từ đầu**.

---

## 1. VẤN ĐỀ CẦN SỬA

Hệ thống hiện tại tạo 3 kịch bản (Đệm an toàn / Cân bằng / Tăng trưởng có kiểm soát) chỉ khác nhau ở soft-objective lợi nhuận–rủi ro–thanh khoản. Nhưng optimizer đang **bỏ sót một loại chi phí thực tế**: khi vốn khả dụng nhỏ (ví dụ 20 triệu VNĐ) mà bị chia vào quá nhiều sản phẩm/nhà cung cấp khác nhau, người dùng phải:

- Mở/quản lý nhiều tài khoản, nhiều app (ngân hàng A, ngân hàng B, sàn vàng, sàn chứng khoán...).
- Theo dõi nhiều kỳ hạn, nhiều ngày đáo hạn, nhiều mức phí khác nhau.
- Chịu tỷ lệ phí/chi phí cố định trên mỗi giao dịch cao hơn tương đối khi số tiền mỗi phần nhỏ.

Đây là chi phí có thật nhưng **phi tài chính thuần túy** (không nằm trong `transaction_cost` của từng sản phẩm), cần được mô hình hóa như một chiều đánh đổi riêng, hiển thị tường minh trong cả 3 kịch bản — không phải một kịch bản thứ 4 riêng biệt.

Yêu cầu này thực chất là mở rộng của **FR-COM-04 (Complexity budget)** đã có trong đặc tả gốc ("Giới hạn số sản phẩm, ngân hàng và app theo preference người dùng") — hiện đang là ràng buộc cứng (hard cap), cần nâng thành **một điểm số liên tục** để tối ưu hóa và giải thích được, không chỉ là on/off.

---

## 2. YÊU CẦU THAY ĐỔI

### 2.1. Định nghĩa `operational_complexity_score` (0–100, càng cao càng bất tiện)

Thêm field mới vào output của mỗi kịch bản, tính từ full calculation output của optimizer (không phải LLM tự ước lượng), dựa trên các yếu tố:

- **Số lượng provider/tổ chức khác nhau** trong danh mục (mỗi ngân hàng, mỗi sàn giao dịch, mỗi nhà cung cấp vàng/bạc tính là 1 điểm chạm).
- **Số lượng sản phẩm khác nhau** (product_id riêng biệt) người dùng phải mở/theo dõi.
- **Tỷ lệ phân mảnh so với vốn khả dụng**: tổng vốn C càng nhỏ mà số sản phẩm càng nhiều thì mức phạt càng cao — dùng ví dụ ngưỡng: nếu allocated_amount của một sản phẩm < một tỷ lệ nào đó của C (ví dụ dưới 10–15% C) thì sản phẩm đó bị tính là "phân bổ vụn" (fragment), cộng thêm điểm phạt.
- **Số kỳ hạn/ngày đáo hạn khác nhau** cần theo dõi (VD 3 tháng, 6 tháng, 12 tháng cùng lúc).

Công thức gợi ý (có thể điều chỉnh, nhưng phải minh bạch, có thể audit):

```
operational_complexity_score =
    w1 * count_distinct_providers +
    w2 * count_distinct_products +
    w3 * count_fragment_products (allocated_amount < threshold_pct * C) +
    w4 * count_distinct_maturities
    → chuẩn hóa về thang 0–100
```

Trọng số `w1..w4` và `threshold_pct` phải là tham số cấu hình được (config), không hard-code trong logic nghiệp vụ rải rác.

### 2.2. Đưa vào Master Optimizer như một chiều mục tiêu chính thức

- Với mỗi kịch bản trong 3 kịch bản hiện có (Safety/Balanced/Growth), optimizer phải giải bài toán multi-objective gồm **4 chiều**: lợi nhuận kỳ vọng, rủi ro, thanh khoản, và **chi phí bất tiện vận hành** — không chỉ 3 chiều như hiện tại.
- Không tạo thêm kịch bản thứ 4. Thay vào đó: trong **mỗi** kịch bản, nếu vốn khả dụng nhỏ hơn một ngưỡng cấu hình (ví dụ dưới 50 triệu VNĐ — cần làm tham số, không hard-code số này), optimizer phải **tự động ưu tiên giảm phân mảnh** (gộp bớt sản phẩm/provider) miễn là không vi phạm risk ceiling và mục tiêu lợi nhuận của kịch bản đó. Đây là ràng buộc "Should" chứ không phải "Must" — nếu việc gộp làm giảm đáng kể lợi nhuận kỳ vọng hoặc vi phạm đa dạng hóa tối thiểu, phải trả về trade-off rõ ràng thay vì ép gộp bằng mọi giá.
- Bảo toàn nguyên tắc bounded re-solve hiện có (tối đa 3 lần giải) — thêm chiều này không được phá vỡ cơ chế cycle detection đã có.

### 2.3. Hiển thị trong UI/output — cho cả 3 kịch bản

Với mỗi trong 3 kịch bản đã có, bổ sung:

- Một chỉ số hiển thị ngang hàng với "Lợi nhuận kỳ vọng / Biến động / VaR 95% / Thanh khoản" hiện tại: **"Độ phức tạp vận hành"** (thang 0–100, có mô tả kèm theo, ví dụ: "Bạn cần theo dõi 5 sản phẩm tại 3 tổ chức khác nhau").
- Trong bảng "Vì sao sản phẩm được chọn hoặc bị loại" (Explain selected & rejected): nếu một sản phẩm bị loại **vì lý do gộp giảm phân mảnh** (không phải vì không đủ điều kiện), phải có `reason_code` riêng, ví dụ `EXCLUDED_TO_REDUCE_FRAGMENTATION`, khác với `LIQUIDITY_MISMATCH` hay các reason code khác đã có — không được gộp chung reason code khiến người dùng hiểu nhầm là sản phẩm không đủ điều kiện.
- Nếu vốn nhỏ khiến độ phức tạp cao, hệ thống nên chủ động đưa ra một **cảnh báo/gợi ý trong phần giải thích** (không phải kịch bản riêng), ví dụ dạng: "Với 20 triệu VNĐ, việc chia vào 5 sản phẩm khiến mỗi phần dưới 4 triệu — chi phí quản lý có thể lớn hơn lợi ích đa dạng hóa mang lại. Bạn có thể xem phương án gộp bớt xuống 2–3 sản phẩm ở nút bên dưới." Kèm theo đó là **một nút/toggle "Gộp bớt sản phẩm"** cho từng kịch bản, khi bật sẽ gọi lại optimizer với trọng số `w1..w4` được đẩy cao hơn (re-solve trong giới hạn 3 lần đã quy định), không tạo kịch bản mới mà **cập nhật lại chính kịch bản đang xem**.

### 2.4. Explanation Agent (LLM)

- LLM chỉ được đọc `operational_complexity_score` + danh sách provider/product/maturity đã tính sẵn từ optimizer để diễn giải bằng ngôn ngữ tự nhiên — **không được tự ước lượng hoặc tự đưa ra con số "bất tiện"**, đúng nguyên tắc chung của toàn hệ thống (LLM chỉ diễn giải, không tự tính).
- Prompt template cho Explanation Agent cần thêm một block hướng dẫn: khi `operational_complexity_score` vượt ngưỡng cấu hình, LLM phải nêu rõ đây là đánh đổi thêm (ngoài lợi nhuận/rủi ro/thanh khoản), không được diễn đạt như một khuyến nghị hành động ("bạn nên gộp lại") ở chế độ `RESEARCH_EDUCATION` — chỉ được trình bày là thông tin so sánh, giữ đúng ranh giới COMPARE_ONLY.

---

## 3. TIÊU CHÍ NGHIỆM THU CHO PHẦN BỔ SUNG NÀY

| Mã | Yêu cầu | Tiêu chí chấp nhận |
|---|---|---|
| FR-COM-04-EXT-1 | Tính operational_complexity_score | Mỗi kịch bản trong output có field này, tính từ full calculation output, có thể trace ngược ra công thức + trọng số |
| FR-COM-04-EXT-2 | Không tạo kịch bản thứ 4 | Số lượng kịch bản gốc vẫn là 2–3 theo FR-COM-25; chi phí bất tiện là 1 chiều bên trong mỗi kịch bản, không phải scenario riêng |
| FR-COM-04-EXT-3 | Toggle "Gộp bớt sản phẩm" | Bấm toggle re-solve đúng kịch bản đang xem, tuân thủ bounded re-solve (≤3 lần), không đổi optimizer objective gốc của các kịch bản khác |
| FR-COM-04-EXT-4 | Reason code riêng cho loại trừ vì gộp | Sản phẩm bị loại để giảm phân mảnh có `EXCLUDED_TO_REDUCE_FRAGMENTATION`, không trộn với reason code về eligibility/risk |
| FR-COM-04-EXT-5 | LLM không tự ước lượng độ phức tạp | Test: xóa field operational_complexity_score khỏi input của Explanation Agent → agent phải báo thiếu dữ liệu, không tự bịa số |
| FR-COM-04-EXT-6 | Không vượt ranh giới legal mode | Ở RESEARCH_EDUCATION, phần giải thích về độ phức tạp không được viết dưới dạng mệnh lệnh hành động cá nhân hóa |

---

## 4. VÍ DỤ CỤ THỂ (dùng để test bằng tay)

Vốn khả dụng: 20.000.000 VNĐ.

- **Trước khi sửa:** optimizer có thể trả về kịch bản "Cân bằng" chia vào 5 sản phẩm (tiền gửi NH A, tiền gửi NH B, vàng, quỹ trái phiếu, ETF), mỗi phần ~4 triệu, không có cảnh báo nào.
- **Sau khi sửa:** cùng kịch bản đó phải hiển thị thêm `operational_complexity_score` cao (ví dụ 68/100), giải thích rõ "5 sản phẩm tại 4 tổ chức, phần nhỏ nhất 3,2 triệu (~16% vốn)", có nút "Gộp bớt sản phẩm" — khi bấm, optimizer trả về phương án gộp còn 2–3 sản phẩm, hiển thị delta lợi nhuận kỳ vọng bị đánh đổi (nếu có) so với phương án gốc.
