# PHỤ LỤC D. BỔ SUNG ĐẶC TẢ — CHI PHÍ BẤT TIỆN VẬN HÀNH
## (Operational Complexity Cost)

**Áp dụng cho:** Bản đặc tả chi tiết "HỆ THỐNG AI RESEARCH ĐA TÁC TỬ HỖ TRỢ PHÂN BỔ DANH MỤC ĐA TÀI SẢN" (đội Monopoly, AQ2026-176).

**Vị trí chèn vào tài liệu gốc:** Phụ lục này bổ sung/mở rộng trực tiếp cho Mục 2 (Nguyên tắc thiết kế và quy trình xử lý chung), Mục 3 (Mô hình dữ liệu), Mục 9 (Tối ưu hóa liên tài sản), Mục 11 (Yêu cầu chức năng xuyên suốt), Mục 13 (Quy tắc an toàn và giải thích), Mục 14 (Kịch bản kiểm thử) và Phụ lục A/B của tài liệu gốc. Đánh số kế tiếp (FR-COM-30 trở đi, NFR-17 trở đi) để không xung đột với mã đã có.

**Ngày lập:** 30/07/2026.

**Lý do bổ sung:** Khi vốn khả dụng nhỏ so với số lượng sản phẩm trong danh mục, việc phân bổ dàn trải giữa nhiều tổ chức/sản phẩm/kỳ hạn tạo ra một loại chi phí thực tế nhưng phi tài chính thuần túy (chi phí quản lý, theo dõi, thao tác) mà bản đặc tả gốc mới chỉ đề cập ở dạng ràng buộc cứng (FR-COM-04 — Complexity budget: "Giới hạn số sản phẩm, ngân hàng và app"). Phụ lục này nâng cấp yêu cầu đó thành một **chiều đánh đổi định lượng**, xuất hiện trong mọi kịch bản đầu ra, thay vì chỉ là một giới hạn bật/tắt.

---

## D.1. Mục đích và nguyên tắc áp dụng

- Không thay đổi số lượng kịch bản đầu ra đã quy định ở FR-COM-25 (vẫn 2–3 nghiệm khả thi). Chi phí bất tiện vận hành là **một trục mục tiêu bổ sung bên trong mỗi kịch bản**, song song với lợi nhuận kỳ vọng, rủi ro và thanh khoản — không phải một kịch bản riêng.
- Không được dùng để nới lỏng hoặc thay thế các gate pháp lý/dữ liệu đã có (Legal Perimeter Gate, Output Policy Engine, Core Data Feasibility Gate ở Mục 3.2 tài liệu gốc). Đây thuần túy là một tiêu chí trong lớp tối ưu hóa và giải thích.
- Master Optimizer (Mục 9 tài liệu gốc) vẫn là nơi duy nhất tính số liệu; Explanation layer chỉ đọc kết quả đã tính, đúng nguyên tắc chung của toàn hệ thống (Mục 2.3, bước 12–13).

## D.2. Định nghĩa `operational_complexity_score`

Thang điểm 0–100 (càng cao càng bất tiện), tính từ full calculation output của Master Optimizer sau bước 8 (Mục 2.3 tài liệu gốc), trước khi qua Compliance/Legal Release Gate:

| Thành phần | Mô tả | Ghi chú |
|---|---|---|
| `distinct_provider_count` | Số tổ chức/nhà cung cấp khác nhau trong danh mục (mỗi ngân hàng, sàn kim loại quý, công ty quản lý quỹ... tính riêng) | Lấy từ trường `provider` trong `AssetProduct` |
| `distinct_product_count` | Số `product_id` khác nhau người dùng phải mở/theo dõi | |
| `fragment_product_count` | Số sản phẩm có `allocated_amount` < `threshold_pct` × vốn khả dụng C | `threshold_pct` là tham số cấu hình (đề xuất mặc định 10–15%), không hard-code |
| `distinct_maturity_count` | Số kỳ hạn/ngày đáo hạn khác nhau cần theo dõi đồng thời | |

Công thức tổng hợp (tham số hóa, có thể hiệu chỉnh theo dữ liệu backtest sau này):

```
raw_score = w1·distinct_provider_count + w2·distinct_product_count
          + w3·fragment_product_count + w4·distinct_maturity_count
operational_complexity_score = normalize(raw_score, 0, 100)
```

`w1..w4` và `threshold_pct` lưu trong config có version, tuân theo nguyên tắc truy vết ở NFR-05/NFR-06 tài liệu gốc (mọi kết quả gắn `recommendation_id`, `data_snapshot`, `model version` — cấu hình trọng số này cũng phải có version riêng để tái lập được).

## D.3. Cập nhật mô hình dữ liệu

### D.3.1. Bổ sung vào cấu trúc đầu ra mỗi kịch bản (scenario object)

| Trường mới | Kiểu | Bắt buộc | Ý nghĩa |
|---|---|---|---|
| `operational_complexity_score` | 0–100 | Có | Điểm bất tiện vận hành của kịch bản, tính theo D.2 |
| `complexity_breakdown` | JSON | Có | Chi tiết `distinct_provider_count`, `distinct_product_count`, `fragment_product_count`, `distinct_maturity_count` để giải thích và audit |
| `complexity_config_version` | String | Có | Version của bộ trọng số `w1..w4`/`threshold_pct` dùng để tính, phục vụ tái lập (đồng bộ nguyên tắc NFR-16 — calculation-release integrity) |
| `fragmentation_warning` | Boolean | Có | Đánh dấu true khi `operational_complexity_score` vượt ngưỡng cấu hình cho vốn khả dụng nhỏ |

### D.3.2. Bổ sung `reason_code` mới cho sản phẩm bị loại khỏi kịch bản (dùng trong cấu trúc "Explain selected & rejected" ở Mục 2.3 bước 13 và Phụ lục B)

| reason_code mới | Ý nghĩa | Phân biệt với reason_code hiện có |
|---|---|---|
| `EXCLUDED_TO_REDUCE_FRAGMENTATION` | Sản phẩm bị loại không phải vì thiếu điều kiện hay rủi ro, mà vì optimizer ưu tiên gộp giảm số lượng sản phẩm/provider | Phải tách biệt hoàn toàn với `LIQUIDITY_MISMATCH`, các reason code về eligibility đã có trong Mục 3/11 tài liệu gốc — không được gộp chung để tránh người dùng hiểu nhầm sản phẩm "không đủ điều kiện" |

## D.4. Cập nhật quy trình xử lý chuẩn (Mục 2.3 tài liệu gốc)

Chèn thêm vào **bước 8 (Master Optimizer)**: ngoài mã hóa bậc/lô/đơn vị/minimum, optimizer giải bài toán multi-objective 4 chiều (lợi nhuận – rủi ro – thanh khoản – độ phức tạp vận hành) thay vì 3 chiều như hiện tại.

Chèn thêm một **luồng tùy chọn sau bước 13 (Explanation)**: nếu người dùng chọn "Gộp bớt sản phẩm" cho một kịch bản cụ thể, hệ thống quay lại bước 8 với trọng số `w1..w4` được điều chỉnh tăng, chạy trong giới hạn bounded re-solve đã quy định ở FR-COM-15/FR-COM-22 (tối đa 3 lần, có state signature và cycle detection) — **chỉ re-solve kịch bản đang xem**, không ảnh hưởng tới các kịch bản còn lại trong tập 2–3 nghiệm.

## D.5. Yêu cầu chức năng bổ sung (tiếp nối Mục 11 tài liệu gốc)

| Mã | Yêu cầu | Mô tả đặc tả | Ưu tiên | Tiêu chí chấp nhận |
|---|---|---|---|---|
| FR-COM-30 | Tính điểm phức tạp vận hành | Mỗi kịch bản có `operational_complexity_score` tính từ full calculation output | Must | Có thể trace ngược ra `complexity_breakdown` và `complexity_config_version` |
| FR-COM-31 | Không tạo kịch bản riêng cho chi phí bất tiện | Chi phí bất tiện là 1 trục trong mỗi kịch bản đã có, không sinh thêm kịch bản | Must | Số lượng kịch bản vẫn tuân FR-COM-25 (2–3 nghiệm) |
| FR-COM-32 | Tùy chọn gộp giảm phân mảnh theo kịch bản | Người dùng có thể yêu cầu re-solve một kịch bản cụ thể với trọng số phức tạp cao hơn | Should | Re-solve tuân FR-COM-15/22; không đổi objective của kịch bản khác |
| FR-COM-33 | Reason code riêng cho loại trừ vì gộp | Sản phẩm bị loại để giảm phân mảnh có `EXCLUDED_TO_REDUCE_FRAGMENTATION` | Must | Không trộn với reason code eligibility/risk hiện có |
| FR-COM-34 | Cảnh báo phân mảnh khi vốn nhỏ | Khi `operational_complexity_score` vượt ngưỡng cấu hình so với vốn khả dụng, hệ thống đánh dấu `fragmentation_warning = true` | Must | Cảnh báo hiển thị đúng kịch bản liên quan, không áp dụng nhầm sang kịch bản khác |

## D.6. Yêu cầu phi chức năng bổ sung (tiếp nối Mục 12 tài liệu gốc)

| Mã | Nhóm | Yêu cầu |
|---|---|---|
| NFR-17 | Truy vết cấu hình | Bộ trọng số `w1..w4` và `threshold_pct` phải có version riêng (`complexity_config_version`), lưu cùng audit trail để tái lập kết quả cũ khi cần điều tra |
| NFR-18 | Giới hạn re-solve | Yêu cầu "Gộp bớt sản phẩm" tuân thủ đúng giới hạn bounded re-solve đã có (tối đa 3 lần/kịch bản), không mở thêm vòng lặp riêng ngoài cơ chế đã kiểm soát |

## D.7. Quy tắc an toàn và giải thích bổ sung (tiếp nối Mục 13 tài liệu gốc)

- Explanation Agent chỉ được đọc `operational_complexity_score` và `complexity_breakdown` đã tính sẵn; không được tự ước lượng hoặc suy diễn mức độ "bất tiện" bằng ngôn ngữ tự nhiên nếu thiếu dữ liệu này.
- Ở `legal_operating_mode = RESEARCH_EDUCATION`: nội dung giải thích về độ phức tạp chỉ được trình bày dưới dạng thông tin so sánh (COMPARE_ONLY), không được diễn đạt dưới dạng khuyến nghị hành động cá nhân hóa (ví dụ không viết "bạn nên gộp lại thành 2 sản phẩm" như một chỉ dẫn thực hiện) — giữ đúng ranh giới đã quy định ở Mục 1.4.1 tài liệu gốc.

## D.8. Kịch bản kiểm thử bổ sung (tiếp nối Mục 14 tài liệu gốc)

| Kịch bản | Input | Kỳ vọng |
|---|---|---|
| Vốn nhỏ, nhiều sản phẩm | Vốn khả dụng 20.000.000 VNĐ, optimizer trả về kịch bản chia 5 sản phẩm tại 4 tổ chức | `operational_complexity_score` cao, `fragmentation_warning = true`, giải thích nêu rõ số tổ chức/sản phẩm và tỷ lệ phần nhỏ nhất so với vốn |
| Gộp bớt theo yêu cầu | Người dùng bấm "Gộp bớt sản phẩm" trên kịch bản Cân bằng | Chỉ kịch bản Cân bằng được re-solve; số sản phẩm giảm còn 2–3; hiển thị delta lợi nhuận kỳ vọng nếu có đánh đổi; không vượt quá 3 lần re-solve |
| Thiếu dữ liệu điểm phức tạp | Xóa `operational_complexity_score` khỏi input của Explanation Agent | Agent phải báo thiếu dữ liệu, không tự bịa số hoặc mô tả định tính thay thế |
| Sai lệch reason code | Một sản phẩm bị loại vì lý do gộp nhưng đang bị gắn `LIQUIDITY_MISMATCH` | Test phải fail; chỉ được gắn `EXCLUDED_TO_REDUCE_FRAGMENTATION` cho đúng nguyên nhân |

## D.9. Cập nhật Phụ lục A — Từ điển dữ liệu cốt lõi (tài liệu gốc)

Bổ sung các trường mới liệt kê ở D.3.1 và D.3.2 vào từ điển dữ liệu cốt lõi hiện có, cùng nhóm với các trường đầu ra kịch bản khác (lợi nhuận kỳ vọng, rủi ro, thanh khoản...).

## D.10. Cập nhật Phụ lục B — Mẫu đầu ra tư vấn (tài liệu gốc)

Mỗi mẫu đầu ra kịch bản (COMPARE_ONLY) cần bổ sung khối hiển thị:

```
Độ phức tạp vận hành: 68/100
- 5 sản phẩm tại 4 tổ chức khác nhau
- Phần nhỏ nhất: 3.200.000đ (~16% vốn khả dụng)
- Cảnh báo: có thể cân nhắc gộp bớt để giảm chi phí quản lý
[Nút: Gộp bớt sản phẩm cho kịch bản này]
```

---

## PROMPT KÈM THEO — DÙNG CHO CLAUDE CODE

Dán đoạn dưới đây cùng với Phụ lục D ở trên khi giao việc cho AI code assistant, để đảm bảo AI sửa đúng hệ thống cũ (không viết lại từ đầu, không tạo kịch bản thứ 4):

```
Bạn đang chỉnh sửa một hệ thống đã tồn tại (không viết lại từ đầu), gồm Master Optimizer
(OR-Tools MILP/MIQP), Explanation Agent (LLM), Output Policy Engine và giao diện chat/dashboard
hiển thị 2-3 kịch bản (Đệm an toàn / Cân bằng / Tăng trưởng có kiểm soát).

Nhiệm vụ: triển khai đầy đủ nội dung ở "PHỤ LỤC D. BỔ SUNG ĐẶC TẢ — CHI PHÍ BẤT TIỆN VẬN HÀNH"
đính kèm, gồm các mục D.1 đến D.10. Yêu cầu bắt buộc:

1. KHÔNG tạo thêm kịch bản thứ 4 — chi phí bất tiện vận hành là một trục trong mỗi kịch bản
   đã có (FR-COM-31).
2. Cập nhật Master Optimizer để giải bài toán 4 chiều (lợi nhuận - rủi ro - thanh khoản -
   operational_complexity_score) thay vì 3 chiều hiện tại (D.2, D.4).
3. Thêm các trường operational_complexity_score, complexity_breakdown, complexity_config_version,
   fragmentation_warning vào output mỗi kịch bản (D.3.1).
4. Thêm reason_code mới EXCLUDED_TO_REDUCE_FRAGMENTATION, tách biệt hoàn toàn khỏi các
   reason_code eligibility/risk đã có — không được gộp lẫn (D.3.2, FR-COM-33).
5. Thêm nút "Gộp bớt sản phẩm" cho từng kịch bản trên UI; khi bấm, chỉ re-solve đúng kịch bản
   đó, trong giới hạn bounded re-solve tối đa 3 lần đã có sẵn trong hệ thống (D.4, FR-COM-32,
   NFR-18) — không tạo cơ chế lặp riêng.
6. Explanation Agent chỉ đọc operational_complexity_score/complexity_breakdown đã tính sẵn,
   không tự ước lượng; ở legal_operating_mode = RESEARCH_EDUCATION không được diễn đạt dưới
   dạng khuyến nghị hành động cá nhân hóa (D.7).
7. Viết test cho đủ 4 kịch bản kiểm thử ở mục D.8, đặc biệt test "Sai lệch reason code" phải
   fail nếu có nhầm lẫn giữa EXCLUDED_TO_REDUCE_FRAGMENTATION và các reason_code khác.

Sau khi sửa xong, xuất checklist đối chiếu từng mã FR-COM-30..34 và NFR-17..18 ở trên với
trạng thái Done/Chưa xong, kèm vị trí file/hàm tương ứng để tôi review.
```
