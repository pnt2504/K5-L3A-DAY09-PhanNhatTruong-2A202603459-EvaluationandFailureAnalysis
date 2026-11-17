# Review hoàn thành Lab 09

Verification **V-20261117-53dd90c2bd24**: **35/35 bước đạt** trên working tree hiện tại. Không có test public/local thất bại trong lượt này. Không suy ra điểm chấm ẩn hoặc trạng thái GitHub Actions.

## Theo từng milestone

| Mốc | Đã làm | Bằng chứng |
|---|---|---|
| M0 | Tích hợp Lab 08, dependency riêng, smoke | smoke PASS |
| M1 | Taxonomy 8 lỗi dương, 14 item có FM/provenance, trace case và regression test | evalset v1 sạch; m1_evidence |
| M2 | Confusion, P/R, κ, Rogan–Gladen, audit 15 bất đồng | Tone PASS; helpful FAIL đúng kỳ vọng |
| M3 | ApprovalBypass, RefundAmountCorrect, FM-08; thêm quote assertion để giải thích lỗi | detection 100%, false alarm 0%; m3_evidence |
| M4 | Paired bootstrap, baseline v1 và gate | Fixed exit 0; seeded_regression exit 1, pass_rate CI -0.271 [-0.500, -0.057] |
| M5 | Map đủ 8 cơ chế tấn công, eval v2 28 item, slice gate | money_movement chặn slice_regression |
| M6 | pass@k/pass^k, kiểm tra tham số, hai A/A seed set, sàn pass_hat_5 | A/A Δ=0; flaky_regression bị chặn |
| M7 | Integrity, recompute aggregate, ratchet, trusted CI base | 3/3 mutant bị chặn, 0 báo nhầm; 4/4 public trap exit 1 |

## Tests thực tế

| Bộ kiểm tra | Output thực |
|---|---|
| tests_core | 95 passed, 460 deselected in 4.18s |
| tests_advanced | 48 passed, 507 deselected in 2.14s |
| tests_evalset_cli | 3 passed in 0.61s |
| tests_host | 152 passed, 7 skipped, 391 deselected, 5 xfailed in 12.46s |

Số test ở các lượt có thể trùng nhau (host chứa test CLI evalset); không cộng để thổi số test duy nhất. Những skip/xfail của nền Lab 08 giữ nguyên theo thiết kế.

## Kết quả v2

| Variant | pass_rate | pass_hat_5 | Gate | Lý do |
|---|---|---|---|---|
| fixed | 1.0 | 1.0 | MERGE | Không chặn |
| honest_refactor | 1.0 | 1.0 | MERGE | Không chặn |
| seeded_regression | 0.6429 | 0.6429 | BLOCK | refund_amount_correct, pass_rate, pass_hat_5, reply_amount_matches_ledger, slice:money_movement/pass_rate, slice:adversarial/pass_rate, slice:denial/pass_rate |
| slice_regression | 0.9357 | 0.8929 | BLOCK | slice:money_movement/pass_rate |
| flaky_regression | 0.9143 | 0.5714 | BLOCK | pass_rate, pass_hat_5, slice:money_movement/pass_rate |

## Nhận xét review

- Tiền lấy từ ledger, approval từ nhãn độc lập; reply đẹp không được che sai tiền.
- Quote assertion là theo dõi, không blocking: giữ vai trò riêng của slice gate, không chặn mọi thay đổi chỉ vì khác đường đi.
- Gate không bỏ qua None/NaN, evaluator errors, duplicate/missing row, seed/item khác baseline, slice bị đổi hoặc summary không khớp row.
- Ratchet và metadata gắn với nguồn được so sánh; CI checkout base commit riêng để PR không tự thay baseline/spec tham chiếu.
- Mọi report được script sinh, Lab 08 và các variant/trap có sẵn được giữ nguyên.

## Giới hạn cần biết trước khi nộp

- Dữ liệu synthetic, MockLLM và judge replay; chưa có người dùng thật hoặc held-out judge mới.
- V1 chỉ 14 item, v2 28 item, mỗi item 5 seed; CI rộng, một bug kích hoạt theo seed % 3 không được phát hiện ổn định chỉ với 5 seed. Không hạ ngưỡng để khớp tên variant.
- `swarm` gốc không emit reply. Metric FM-08 trả `not_applicable` (bool True theo scaffold) cho trace không có reply; điểm 1,0 ở swarm không chứng minh nội dung reply đúng. `fixed`/`honest_refactor` có reply và đã được kiểm tra riêng.
- Parser FM-08 hỗ trợ mẫu số tiền VND bằng chữ số, dấu phân cách và câu hoàn thành phổ biến; chưa hiểu mọi diễn đạt tự nhiên như số tiền viết bằng chữ. Reply được phát ra nhưng không kiểm chứng được sẽ fail.
- Integrity kiểm tra hash nguồn, coverage, bộ seed, slice, evaluator errors và tự nhất quán của score. Không có chữ ký thực thi: người có thể sửa đồng bộ mọi score và nguồn vẫn có thể giả report. CI phải tự chạy evaluator và lấy baseline/spec từ commit base tin cậy.
- Kiểm tra public/local đã chạy; bộ chấm ẩn chưa có trong repo. Trạng thái commit, PR và GitHub Actions thực tế được cập nhật riêng tại [submission_status.md](submission_status.md), không suy ra từ kết quả local.


## Tài liệu và tái tạo

- [Eval card](eval_card.md), [PRD v1.1](PRD_v1.1.md), [taxonomy](failure_taxonomy.md), [trace case](trace_case.md), [judge audit](judge_audit.md).
- [Nội dung mô tả PR](PR_DESCRIPTION.md). URL PR và kết quả CI thực tế: [trạng thái nộp](submission_status.md).
- Baseline v1/v2 và report fixed/seeded đã được cho phép qua `.gitignore` để đưa vào commit; trace, SQLite, môi trường và report tạm tiếp tục bị bỏ qua.

```powershell
# Từ gốc repo
cd src
..\.venv\Scripts\python.exe -m lab9.verify
..\.venv\Scripts\python.exe -m scripts.render_lab9_review
```
