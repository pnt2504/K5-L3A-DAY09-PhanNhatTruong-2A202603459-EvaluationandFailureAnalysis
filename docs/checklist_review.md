# Đối chiếu yêu cầu nộp Lab 09

## Kết luận

Các hạng mục bắt buộc của SUBMISSION.md đã có code, dữ liệu, tài liệu, commit và PR thực tế. Hai job bắt buộc eval-gate và eval-gate-v2 đã SUCCESS trên runtime đang nộp.

- [PR #1](https://github.com/pnt2504/K5-L3A-DAY09-PhanNhatTruong-2A202603459-EvaluationandFailureAnalysis/pull/1): starter/d09 → main.
- [CI Core và Advanced/Expert](https://github.com/pnt2504/K5-L3A-DAY09-PhanNhatTruong-2A202603459-EvaluationandFailureAnalysis/actions/runs/44130310352): SUCCESS cho commit runtime d20416d.
- Baseline tin cậy đã bootstrap trên main tại commit 5d6b8e7.
- Source đã được theo dõi và commit; không còn thiếu do file untracked.
- Mô tả PR chứa output gate exit 1, mutation score 3/3, hai A/A và bốn trap.
- Eval card và PRD có số liệu thực, run ID, ngưỡng, phạm vi và giới hạn.

## Bằng chứng theo mốc

| Mốc | Kết quả |
|---|---|
| M0 | Smoke PASS, Lab 08 và dependency đầy đủ |
| M1 | Taxonomy 8 lỗi dương, 14 item có FM/provenance, nhãn riêng, trace case và test |
| M2 | Tone đạt, helpful bị loại; audit 15 bất đồng |
| M3 | Detection 100%, báo nhầm 0%; FM-08 kiểm tra reply/ledger |
| M4 | Fixed qua, seeded_regression bị chặn; CI khớp tham chiếu |
| M5 | V2 có 28 item, đủ map, mỗi FM bị tấn công có ≥3 item; slice gate hoạt động |
| M6 | pass@k/pass^k đúng test, hai A/A Δ=0, pass_hat_5 blocking |
| M7 | Chặn 3/3 regression và 4/4 public trap, không báo nhầm refactor |

Local verification V-20261117-53dd90c2bd24 đạt 35/35 bước; 95 test Core, 48 test Advanced, 152 test nền pass. Không cộng các lượt test trùng nhau.

## Những gì chưa được tuyên bố

- Key 5 anchor và hidden grader chỉ giảng viên có; chưa khẳng định điểm chấm ẩn.
- Bonus Inspect AI/DeepEval là tùy chọn, chưa thực hiện.
- Product approver/phê duyệt vận hành thật chưa được xác nhận, không giả chữ ký.
- Job macOS Python 3.11 bổ sung đang xử lý thiếu capacity; không thay thế hoặc làm mất hai job Lab 09 bắt buộc đã xanh. Chi tiết mới nhất: [trạng thái nộp](submission_status.md).
