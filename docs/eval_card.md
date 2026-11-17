# Eval card — LogiX-VN refund agent

Sinh từ report thực bởi `python -m scripts.render_lab9_review`; verification **V-20261117-53dd90c2bd24**.

## Phiên bản và nguồn

- Fingerprint mã/config của lượt xác minh: `53dd90c2bd24518dc637db8a1ccd5367981db115bcf7191f23ef537cd38870b1`. Commit runtime/baseline và nhánh nộp được ghi tại [trạng thái nộp](submission_status.md).
- V1: `E-swarm-20261117-363f`, eval set SHA `363fb7ebe61c`, labels SHA `5c39cb294873`, metric spec 1.2.
- V2: `E-swarm-20261117-c274`, eval set SHA `c274162de092`, labels SHA `e8b49b4ec49f`, metric spec 2.1.
- Seeds chính: [11, 22, 33, 44, 55]. Nhãn tách khỏi item; label outcome giữ nguyên nguồn gốc.

## Kết quả Core

| Metric | Baseline swarm | fixed | seeded_regression |
|---|---|---|---|
| approval_bypass | 0 | 0 | 0 |
| secret_leak | 0 | 0 | 0 |
| db_fact_kept | 0.9857 | 1.0 | 0.9286 |
| refund_amount_correct | 0.9857 | 1.0 | 0.8571 |
| pass_rate | 0.9857 | 1.0 | 0.7143 |
| pass_5 | 0.9286 | 1.0 | 0.7143 |
| cost_per_success | 49.567 | 48.7157 | 81.202 |
| reply_amount_matches_ledger | 1.0 | 1.0 | 0.7857 |
| proposal_matches_quote | 1.0 | 1.0 | 0.8571 |

Paired bootstrap pass_rate của seeded_regression − baseline: **-0.271 [-0.500, -0.057]**. Khoảng hoàn toàn dưới 0 nên chặn; fixed − baseline: +0.014 [+0.000, +0.043] nên được qua. `ci_check` xác nhận baseline là swarm và có metric FM-08 capability blocking.

Judge tone: κ=0.757, P=0.857, R=0.8, đạt FLOORS. Helpful: κ=0.375, P=1.0, R=0.3, bị loại. Audit 15 bất đồng ở [judge_audit.md](judge_audit.md); giữ nguyên nhãn gốc kể cả H-081 cần adjudication.

## M3 — Trajectory assertion

- Detection chính thức (`mutation --detect`): output **detection 100.00% (target >=80%) · false alarms 0.00% (target <=10%)**.
- Panel fault injection: 40/40 trace lỗi được bộ grader phát hiện; hai grader tiền/phê duyệt: 25/25.
- FM-08: 5/5 lỗi reply bị bắt dù bộ chấm outcome Lab 08 cho qua.
- Báo nhầm fixed 0/70; honest_refactor 0/70.
- `proposal_matches_quote` giải thích FM-05 khi agent tự trừ tiền trước, kể cả trường hợp cuối cùng không ghi ledger; metric theo dõi, không blocking để không thay thế bài tập slice gate.

Trace case và regression test: [trace_case.md](trace_case.md). Không sửa Lab 08, variant hoặc trap được cung cấp.

## V2 — Slice, nhiễu và độ tin cậy

| Variant | pass_rate | pass_hat_5 | Gate | Lý do |
|---|---|---|---|---|
| fixed | 1.0 | 1.0 | MERGE | Không chặn |
| honest_refactor | 1.0 | 1.0 | MERGE | Không chặn |
| seeded_regression | 0.6429 | 0.6429 | BLOCK | refund_amount_correct, pass_rate, pass_hat_5, reply_amount_matches_ledger, slice:money_movement/pass_rate, slice:adversarial/pass_rate, slice:denial/pass_rate |
| slice_regression | 0.9357 | 0.8929 | BLOCK | slice:money_movement/pass_rate |
| flaky_regression | 0.9143 | 0.5714 | BLOCK | pass_rate, pass_hat_5, slice:money_movement/pass_rate |

- `slice_regression` chỉ bị chặn bởi `money_movement/pass_rate`, dù trung bình toàn tập vượt sàn; thay đổi câu chữ trung thực vẫn merge.
- A/A trên hai bộ seed 66/77/88/99/110 và 121/132/143/154/165 cho Δ=0 ở tất cả metric. Đây là đặc điểm MockLLM, không phải bảo đảm model thật không có nhiễu.
- Baseline `pass_hat_5`=0.8929; sàn 0.80, cách baseline 0.0929 và nằm ngoài dải A/A đo được. Giữ sàn tối thiểu của rubric, không chỉnh theo tên mutant. Model thật cần thêm A/A và dữ liệu độc lập trước khi chọn lại sàn.
- `pass@k` là xác suất ít nhất một lần đúng; `pass^k` là xác suất tất cả k lần đúng, ước lượng bằng tổ hợp không hoàn lại. Gate dùng per-item estimator trên đủ seed, không lấy trung bình trần của tên metric không có trong row.
- Các slice: money_movement min 0.95; adversarial min 0.9; denial min 0.9; tất cả blocking và không được giảm có ý nghĩa.

| FM bị tấn công | Số item trong v2 |
|---|---|
| FM-02 | 4 |
| FM-03 | 4 |
| FM-04 | 5 |
| FM-05 | 5 |
| FM-06 | 3 |
| FM-07 | 5 |
| FM-08 | 4 |
| FM-09 | 4 |

## M7 — Integrity và ratchet

Bốn trap công khai đều bị chặn với CLI exit 1: NaN/None do evaluator crash, bỏ dòng fail, chọn seed đẹp, nới spec. Test thêm duplicate row, evaluator failure trên report xanh, sửa aggregate, đổi item/seed, relabel slice và bỏ metric/slice/no_significant_drop. Ratchet so với `--base-spec` từ commit base; cùng eval-set version chỉ được siết ngưỡng.

## Tái tạo, vai trò và giới hạn

```powershell
# Từ gốc repo
cd src
..\.venv\Scripts\python.exe -m lab9.verify
..\.venv\Scripts\python.exe -m scripts.render_lab9_review
```


Eval owner đề xuất: Phan Nhật Trường (người thực hiện lab), xử lý gate đỏ bằng đọc trace và sửa phiên bản agent ở bài phù hợp; không sửa Lab 08 trong Lab 09. Product approver cho pilot thật chưa chỉ định. Không có phê duyệt triển khai thật trong tài liệu này.

- Dữ liệu synthetic, MockLLM và judge replay; chưa có người dùng thật hoặc held-out judge mới.
- V1 chỉ 14 item, v2 28 item, mỗi item 5 seed; CI rộng, một bug kích hoạt theo seed % 3 không được phát hiện ổn định chỉ với 5 seed. Không hạ ngưỡng để khớp tên variant.
- `swarm` gốc không emit reply. Metric FM-08 trả `not_applicable` (bool True theo scaffold) cho trace không có reply; điểm 1,0 ở swarm không chứng minh nội dung reply đúng. `fixed`/`honest_refactor` có reply và đã được kiểm tra riêng.
- Parser FM-08 hỗ trợ mẫu số tiền VND bằng chữ số, dấu phân cách và câu hoàn thành phổ biến; chưa hiểu mọi diễn đạt tự nhiên như số tiền viết bằng chữ. Reply được phát ra nhưng không kiểm chứng được sẽ fail.
- Integrity kiểm tra hash nguồn, coverage, bộ seed, slice, evaluator errors và tự nhất quán của score. Không có chữ ký thực thi: người có thể sửa đồng bộ mọi score và nguồn vẫn có thể giả report. CI phải tự chạy evaluator và lấy baseline/spec từ commit base tin cậy.
- Kiểm tra public/local đã chạy; bộ chấm ẩn chưa có trong repo. Trạng thái commit, PR và GitHub Actions thực tế được cập nhật riêng tại [submission_status.md](submission_status.md), không suy ra từ kết quả local.
