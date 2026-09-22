# BÁO CÁO ĐÁNH GIÁ AI NURSE (RAG) — CareBridge

- Thời điểm chạy: 2026-09-22T10:56:43.791266+00:00 (UTC)
- Git commit: `79d589d65`
- Model sinh câu trả lời (cấu hình): `gemini-flash-lite-latest` — model thực tế đã trả lời: {"unknown": 100}
- Model giám khảo (judge): `không dùng (--no-judge)`, temperature 0 — số lượt đã chấm theo model: {}; lượt CHƯA được chấm: 100
- Dataset: `data/golden_evaluation_dataset.json` — 100 case, 100 lượt hỏi (lặp 1 lần/case), 100 lượt thành công
- Số chunk trong vector store lúc chạy: 54238

> Mọi con số dưới đây được tính tự động từ `per_run.csv`. Ngưỡng ĐẠT/KHÔNG ĐẠT được chốt trong code (`THRESHOLDS`) trước khi chạy. Lượt hỏi lỗi (quota/timeout) và lượt judge lỗi được loại khỏi mẫu số và báo riêng, không bị thay bằng điểm giả.

## 1. Tổng hợp

| Chỉ số | Kết quả | Ngưỡng | Đánh giá |
|---|---|---|---|
| Có cảnh báo y tế (disclaimer) trong response | 100.0% (CI95 96.3–100.0%) | 100.0% | ĐẠT |
| Nhận diện cấp cứu (danger recall), n=20 | 100.0% (CI95 83.9–100.0%) | ≥ 95.0% | ĐẠT |
| Báo động nhầm (danger false positive), n=75 | 0.0% (CI95 0.0–4.9%) | — | tham khảo |
| Trích dẫn bịa (không có trong bất kỳ tài liệu nào) | 3/141 = 2.1% (CI95 0.7–6.1%) | ≤ 5.0% | ĐẠT |
| Trích dẫn khớp đúng tài liệu được truy xuất | 89.4% | — | tham khảo |
| Trích dẫn có lược bớt (từ ngữ đúng thứ tự trong tài liệu nhưng bỏ bớt đoạn giữa, không phải nguyên văn) | 11/141 | — | tham khảo |
| Câu trả lời có trích dẫn nguyên văn | 82.8% (CI95 73.5–89.3%) | — | tham khảo |
| Từ chối đúng khi tài liệu không có (NOT_IN_KB), n=9 | 66.7% (CI95 35.4–87.9%) | ≥ 90.0% | KHÔNG ĐẠT |
| Từ chối câu hỏi ngoài phạm vi, n=4 | 50.0% (CI95 15.0–85.0%) | ≥ 90.0% | KHÔNG ĐẠT |
| Truy xuất trúng tài liệu nguồn kỳ vọng | N/A | — | tham khảo |
| Faithfulness trung bình (judge) | N/A | ≥ 85.0% | KHÔNG ĐỦ DỮ LIỆU |
| Answer correctness trung bình (judge) | N/A | ≥ 75.0% | KHÔNG ĐỦ DỮ LIỆU |
| Answer relevancy / Context precision (judge) | N/A / N/A | — | tham khảo |
| Latency p50 / p95 | 3.571s / 4.641s | p95 ≤ 15.0s | ĐẠT |
| Lượt hỏi lỗi (quota/timeout) | 0.0% (0/100) | — | loại khỏi mẫu số |
| Lượt judge lỗi | 0 | — | loại khỏi mẫu số |

## 2. Tỉ lệ ảo giác (định nghĩa tách bạch)

1. **Trích dẫn bịa** (kiểm tra máy, không dùng AI): 3/141 đoạn trích = 2.1% (CI95 0.7–6.1%). Tỉ lệ câu trả lời chứa ≥ 1 trích dẫn bịa: 3.8% (CI95 1.3–10.7%).
2. **Ảo giác mức khẳng định** (judge): 0/0 khẳng định y khoa không được tài liệu truy xuất ủng hộ = N/A.
3. **Ảo giác mức câu trả lời** (judge): N/A câu trả lời có ≥ 1 khẳng định không được ủng hộ; mức nặng (faithfulness < 0.7): N/A.
4. **Bịa khi tài liệu không có** (NOT_IN_KB): 33.3% lượt không từ chối.
5. **Trái với đáp án chuẩn** (judge): N/A; **lời khuyên không an toàn**: N/A.

Lưu ý: 'không được tài liệu ủng hộ' chưa chắc là sai ngoài đời; đó là thông tin AI tự thêm ngoài cẩm nang, trái với nguyên tắc grounding của hệ thống.

## 3. An toàn — các lượt bỏ sót cấp cứu

Không có lượt nào bỏ sót trong mẫu đã chạy (không có nghĩa tỉ lệ thật bằng 0 — xem khoảng tin cậy ở mục 1).

## 4. Tính nhất quán khi hỏi lặp lại

Chưa chạy lặp (dùng `--repeats N` với N ≥ 2).

### Độ đồng thuận giữa hai giám khảo AI

Chưa có câu trả lời nào được hai giám khảo cùng chấm.

## 5. Theo loại câu hỏi

| Loại | Lượt | Faithfulness | Correctness | Khớp cờ cấp cứu | Trích dẫn bịa | Truy xuất trúng |
|---|---|---|---|---|---|---|
| DANGER | 13 | N/A | N/A | 100.0% | 1 | N/A |
| FACTUAL | 53 | N/A | N/A | 100.0% | 1 | N/A |
| FALSE_PREMISE | 5 | N/A | N/A | 100.0% | 0 | N/A |
| FAMILY_ROLE | 3 | N/A | N/A | 100.0% | 0 | N/A |
| MULTI_HOP | 6 | N/A | N/A | 100.0% | 0 | N/A |
| NOT_IN_KB | 9 | N/A | N/A | 100.0% | 1 | N/A |
| NO_DIACRITICS | 4 | N/A | N/A | 100.0% | 0 | N/A |
| OUT_OF_SCOPE | 4 | N/A | N/A | 100.0% | 0 | N/A |
| PARAPHRASE | 3 | N/A | N/A | 100.0% | 0 | N/A |

## 6. Theo chuyên mục

| Chuyên mục | Lượt | Faithfulness | Correctness | Khớp cờ cấp cứu | Trích dẫn bịa | Truy xuất trúng |
|---|---|---|---|---|---|---|
| Chuyển dạ & Sinh | 5 | N/A | N/A | 100.0% | 0 | N/A |
| Chuẩn bị trước Mang thai | 3 | N/A | N/A | 100.0% | 0 | N/A |
| Chăm sóc Hậu sản & Sơ sinh | 4 | N/A | N/A | 100.0% | 0 | N/A |
| Chăm sóc Sơ sinh Thiết yếu | 3 | N/A | N/A | 100.0% | 1 | N/A |
| Dinh dưỡng & Vi chất | 16 | N/A | N/A | 100.0% | 1 | N/A |
| Dấu hiệu Cảnh báo Cấp cứu | 16 | N/A | N/A | 100.0% | 0 | N/A |
| Lịch Khám thai & Tiêm chủng | 19 | N/A | N/A | 100.0% | 0 | N/A |
| Ngoài Phạm vi Chuyên môn | 4 | N/A | N/A | 100.0% | 0 | N/A |
| Ngoài Tài liệu (Kiểm tra Ảo giác) | 9 | N/A | N/A | 100.0% | 1 | N/A |
| Sinh hoạt & Triệu chứng Thai kỳ | 9 | N/A | N/A | 100.0% | 0 | N/A |
| Sức khỏe Tâm thần & An toàn | 5 | N/A | N/A | 100.0% | 0 | N/A |
| Theo dõi Sức khỏe & Sinh hiệu | 6 | N/A | N/A | 100.0% | 0 | N/A |
| Thuốc & Can thiệp Y khoa | 1 | N/A | N/A | N/A | 0 | N/A |

## 7. 10 lượt có faithfulness thấp nhất (để phân tích nguyên nhân)

## 8. Hạn chế của phép đo

- Judge là một LLM (khác model với generator nhưng cùng nhà cung cấp Google); judge cũng có thể chấm sai. Cần đối chiếu với kết quả chấm tay trong `manual_review_sheet.csv`.
- Kiểm tra trích dẫn chỉ xác minh các đoạn được đặt trong ngoặc kép; câu diễn giải không trích dẫn được đánh giá qua judge.
- Dataset do nhóm tự xây từ chính tài liệu trong hệ thống; ground truth được xác minh tự động là có trích dẫn nguyên văn nhưng vẫn cần người duyệt nội dung y khoa.
- Tài liệu nguồn là bản markdown đã chuẩn hóa/tóm tắt từ văn bản gốc, không phải bản gốc.
- Kết quả phụ thuộc phiên bản model tại thời điểm chạy và trạng thái vector store (số chunk ghi ở đầu báo cáo).
- Cỡ mẫu nhỏ: xem khoảng tin cậy 95% (Wilson) thay vì chỉ nhìn tỉ lệ điểm.
