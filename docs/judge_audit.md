# Judge audit — M2

## Quyết định từ calibration

Backend **REPLAY**: kết quả judge và nhãn người lấy nguyên từ hai CSV công khai, không gọi model thật và không sửa nhãn để làm đẹp điểm. Bảng audit bên dưới là phân tích của trợ lý dựa trên reply/ghi chú có sẵn; chưa phải vòng gán nhãn người độc lập mới.

**FAIL là lớp dương.** TP = người FAIL, judge FAIL; FP = người PASS, judge FAIL; FN = người FAIL, judge PASS; TN = cả hai PASS. Precision đo độ đúng khi judge báo lỗi; recall đo khả năng tìm đủ lỗi.

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0,6; P≥0,8; R≥0,7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0,757 | 0,857 | 0,800 | Có, đủ cả ba ngưỡng | Dùng có điều kiện cho tone trong phạm vi rubric công khai; không quyết định tiền hoặc approval |
| helpful | 100 | 0,375 | 1,000 | 0,300 | Không: κ và recall dưới ngưỡng | Loại khỏi gate; cần sửa rubric và kiểm lại trên held-out |

Số hiển thị làm tròn ba chữ số, nhưng quyết định đạt/ngã so trực tiếp giá trị chưa làm tròn. Trường hợp κ không xác định phải FAIL calibration; báo cáo JSON ghi `null`, không đưa NaN vào file JSON.

## Ma trận nhầm lẫn và tỷ lệ lỗi hiệu chỉnh

| Tiêu chí | TP | FP | FN | TN | Đồng thuận thô | Lỗi theo judge | Lỗi theo nhãn người | Rogan–Gladen |
|---|---|---|---|---|---|---|---|---|
| tone_ok | 24 | 4 | 6 | 66 | 90/100 = 90% | 28/100 = 28% | 30/100 = 30% | 30% |
| helpful | 9 | 0 | 21 | 70 | 79/100 = 79% | 9/100 = 9% | 30/100 = 30% | 30% |

- Tone: `P=24/(24+4)`, `R=24/(24+6)`. Đồng thuận ngẫu nhiên từ biên là 0,588, nên `κ=(0,90−0,588)/(1−0,588)=0,757142…`.
- Helpful: `P=9/(9+0)=1`, nhưng `R=9/(9+21)=0,3`. Đồng thuận ngẫu nhiên 0,664, nên `κ=(0,79−0,664)/(1−0,664)=0,375`.
- Rogan–Gladen: `(p_observed + specificity − 1)/(sensitivity + specificity − 1)`, chặn kết quả trong `[0,1]`. Tone có sensitivity=0,8, specificity=66/70; helpful có sensitivity=0,3, specificity=1. Cả hai hiệu chỉnh ra 0,30 trên chính mẫu này.
- Helpful bỏ sót **21/30 lỗi (70%)**. Không có FP không có nghĩa judge an toàn: một gate dùng judge này vẫn cho lọt nhiều câu sai. Hiệu chỉnh tỷ lệ lỗi tổng thể không sửa được phán quyết sai của từng câu.
- Khi sensitivity + specificity = 1, phép hiệu chỉnh không xác định: code từ chối phép chia và calibration ghi tỷ lệ hiệu chỉnh `null`. Dữ liệu rỗng, số nhãn lệch nhau hoặc nhãn ngoài PASS/FAIL cũng bị từ chối.

## Audit 15 bất đồng và hành động sửa rubric

Trích nội dung từ `reply`, `note`, `human_failure` của CSV. Số tiền ledger ở các case helpful là thông tin trong cột `note` của bộ replay, không phải truy vấn một ledger người dùng thật. Case tone được xét theo quy ước giao tiếp của bộ dữ liệu LogiX, không áp đặt thành quy tắc ngôn ngữ cho mọi tình huống.

| # | Case / tiêu chí | Nội dung cần chú ý | Judge | Người | Ai đúng theo bằng chứng hiện có? | Hành động sửa rubric |
|---|---|---|---|---|---|---|
| 1 | H-008 / tone | “Em đã hoàn tiền cho anh rồi nha, anh check giúp em.” | PASS | FAIL | Người theo note: cả câu quá suồng sã với chuẩn CS của bộ dữ liệu; FN. | Thêm ví dụ phân biệt thân thiện và suồng sã; đánh giá cả câu, không chỉ từ lịch sự đầu câu. |
| 2 | H-017 / tone | “Dạ, bạn ơi … rồi nha.” | PASS | FAIL | Người theo note về xưng hô không phù hợp khách; FN. Tuổi khách không có trực tiếp trong reply. | Gắn quy tắc xưng hô với context được cung cấp; mặc định chuẩn CS `anh/chị`, tránh tự suy tuổi từ câu trả lời. |
| 3 | H-029 / tone | “Dạ, vui lòng chờ … không cần nhắn thêm.” | PASS | FAIL | Người: phần sau mang giọng ra lệnh dù mở đầu lịch sự; FN. | Không cho “Dạ/vui lòng” tự bảo đảm PASS; kiểm tra cả mệnh lệnh hạn chế khách phản hồi. |
| 4 | H-042 / tone | “Dạ, đơn O-808 đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ.” | FAIL | PASS | Người theo rubric tone: ngắn gọn, lịch sự; note cho biết judge phạt thiếu xin lỗi; FP. | Không bắt buộc câu xin lỗi trong mọi reply; không phạt chỉ vì ngắn. Tiền đúng/sai phải kiểm tra riêng. |
| 5 | H-051 / tone | “Dạ, LogiX đã refund 90.000đ … ạ.” | FAIL | PASS | Người: note nêu `refund` được CS LogiX cho phép; FP. | Ghi danh sách thuật ngữ được phép; không đánh FAIL chỉ vì một từ tiếng Anh hợp lệ. |
| 6 | H-063 / tone | “… đã hoàn 20.000đ và sẽ hoàn thêm …” | PASS | FAIL | Người theo note: có lời hứa hoàn thêm ngoài kết quả hệ thống; FN. | Thêm tiêu chí không hứa kết quả ngoài quyền/nguồn được cung cấp; kiểm tra tiền và quyền hoàn bằng code riêng. |
| 7 | H-070 / tone | “… đã hoàn 90.000đ … 😂😂” | PASS | FAIL | Người theo chuẩn ngữ cảnh khiếu nại: emoji cười không phù hợp; FN. | Nêu ngữ cảnh sử dụng emoji, kèm ví dụ khiếu nại; không đồng nhất cảm xúc tích cực với tone phù hợp. |
| 8 | H-081 / tone | Câu từ chối lịch sự; note ghi “nhãn người sai (đọc nhầm ticket) — judge đúng”. | FAIL | PASS | **Theo note: judge đúng, nhãn người cần rà soát.** Reply đơn lẻ không đủ xác minh ticket; không tự sửa nhãn khi tính điểm. | Chuyển chủ sở hữu nhãn adjudicate trên context gốc; tách tone khỏi đúng/sai chính sách. Nếu sửa nhãn, phát hành phiên bản mới và chạy lại calibration. |
| 9 | H-088 / tone | “Dạ, dạ, LogiX đã hoàn … ạ.” | FAIL | PASS | Người theo note: lỗi gõ/lặp nhẹ được chấp nhận; FP. | Đặt mức độ lỗi rõ: lặp nhẹ không tự động FAIL nếu không xúc phạm hoặc làm khó hiểu. |
| 10 | H-094 / tone | Reply tiếng Việt không dấu, có câu xin lỗi. | PASS | FAIL | Người theo chuẩn chất lượng tiếng Việt của bộ dữ liệu; FN. | Ghi rõ yêu cầu tiếng Việt có dấu cho reply CS; không lấy riêng từ “xin lỗi” làm tín hiệu PASS. |
| 11 | HL-015 / helpful | Reply 55.000đ; note ledger 40.000đ. | PASS | FAIL | Người theo note: sai số tiền; FN. | Bắt buộc groundedness theo ledger; giao phép so tiền cho code, tone tốt không bù được tiền sai. |
| 12 | HL-016 / helpful | Nhiều câu xin lỗi, reply 55.000đ; note ledger 35.000đ. | PASS | FAIL | Người theo note: lời văn dài không sửa được sai tiền; FN. | Thêm cặp ví dụ cùng lời văn nhưng khác số tiền; không thưởng độ dài hoặc số lần xin lỗi. |
| 13 | HL-020 / helpful | Reply 90.000đ; note ledger 120.000đ. | PASS | FAIL | Người theo note: báo thiếu tiền so ledger cũng là sai; FN. | So giá trị bằng nhau chính xác, không chỉ bắt số tiền bị nói quá. |
| 14 | HL-047 / helpful | “Ok bạn, đơn O-515 xử lý rồi nhé.” | PASS | FAIL | Người theo `human_failure`: sai xưng hô; câu cũng không nêu kết quả cụ thể; FN. | Tách checklist hữu ích, kết quả cụ thể và tone; quy định rõ thông tin tối thiểu thay vì chấm bằng cảm giác thân thiện. |
| 15 | HL-098 / helpful | Xin lỗi lặp lại, reply 120.000đ; note ledger 90.000đ. | PASS | FAIL | Người theo note: sai tiền dù diễn đạt lịch sự; FN. | Dùng ledger như điều kiện bắt buộc; thêm ví dụ adversarial có lời văn đẹp nhưng dữ kiện sai. |

Các thay đổi rubric ở bảng là đề xuất sau audit, chưa phải một judge mới đã được chứng minh tốt hơn. Không sửa replay verdict, CSV hoặc ngưỡng FLOORS để biến helpful thành PASS.

## Cách chạy và bằng chứng do script sinh

Từ `src/`:

```powershell
..\.venv\Scripts\python.exe -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5 --out reports/judge_tone_m2.json
# Exit 0: PASS floors.

..\.venv\Scripts\python.exe -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5 --out reports/judge_helpful_m2.json
# Exit 1: FAIL floors, kết quả mong đợi.

..\.venv\Scripts\python.exe -m pytest -q tests/test_lab9_stats.py tests/test_lab9_m2.py -o addopts= -k "not paired"
```

| Report | Run ID | SHA256 nguồn (12 ký tự đầu) |
|---|---|---|
| `reports/judge_tone_m2.json` | `J-judge_tone_public-716e3dc3b394` | `716e3dc3b394` |
| `reports/judge_helpful_m2.json` | `J-judge_helpful_public-670c133b2f56` | `670c133b2f56` |

Report lưu toàn bộ SHA256 nguồn, ngưỡng, confusion matrix và danh sách bất đồng. File report bị Git bỏ qua theo starter, có thể sinh lại bằng lệnh trên; mọi con số trong tài liệu lấy từ report thực.

Tại thời điểm hoàn thành M2, kiểm tra kết hợp M1+M2 có **55 passed, 2 deselected** (hai test bootstrap khi đó thuộc M4). Sau đó bootstrap đã hoàn thiện và được chạy trong kiểm tra toàn lab; kết quả mới ở [final_review.md](final_review.md). Test M2 bao gồm polarity FAIL, κ âm/0/1/không xác định, mẫu không hợp lệ, Rogan–Gladen, verdict CLI, report JSON và trường hợp làm tròn gần ngưỡng.

## Giới hạn và bước tiếp theo

- Giữ nguyên nhãn H-081 khi tính số liệu tham chiếu. Nhãn người cũng có thể sai; cần adjudication có context thay vì mặc định mọi bất đồng đều do judge.
- Mỗi tập chỉ có 100 dòng công khai. Calibration, audit và hiệu chỉnh tỷ lệ lỗi cùng dùng một tập nên chưa phải kiểm tra held-out độc lập.
- Tone đạt FLOORS trên replay chỉ đủ cho phạm vi tiêu chí này; không chứng minh một model thật hoặc prompt judge mới đạt cùng chất lượng.
- Helpful chưa được dùng làm gate. Sau khi sửa rubric, cần nhãn độc lập mới và chạy lại toàn bộ ngưỡng; không dùng độ chính xác tổng hoặc precision cao để bỏ qua recall thấp.
- M3 đã kiểm tra tiền/approval bằng code, đặc biệt so reply với ledger để bắt FM-08; kết quả ở [eval_card.md](eval_card.md). Một judge tone đạt chuẩn không thay thế các phép kiểm tra đó.
