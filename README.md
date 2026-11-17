# Lab 09 — Evaluation & Failure Analysis · LogiX-VN

Đánh giá agent xử lý claim hoàn phí: tìm bước sai đầu tiên trong trace, kiểm định judge, viết grader tiền/phê duyệt và chặn regression bằng CI gate. Repo đã tích hợp mã, cấu hình và dữ liệu Lab 08; có thể chạy trực tiếp, không cần chép overlay lần nữa.

Lab chạy bằng **MockLLM + judge replay**, không cần API key hay gọi model thật. Cần Python **3.11 trở lên**. Cài dependency cần truy cập kho package; các lệnh lab chạy offline sau khi cài xong.

## Trạng thái và kết quả

M0–M7 đã triển khai. Lượt xác minh local ngày **17/11/2026**, ID `V-20261117-53dd90c2bd24`, đạt **35/35 bước**:

| Kiểm tra | Kết quả |
|---|---|
| Core | 95 test pass |
| Advanced/Expert | 48 test pass |
| Nền Lab 08 | 152 pass, 7 skip, 5 xfail theo thiết kế |
| Detection M3 | 100% phát hiện, 0% báo nhầm trên bộ công khai đã chạy |
| Mutation | Chặn 3/3 regression; không báo nhầm `fixed`, `honest_refactor` |
| Trap | Chặn đủ 4/4 trap công khai |

Các bộ test có phần trùng nhau, không cộng để suy ra số test duy nhất. Đây là kết quả **local/public**, không tự xác nhận trạng thái GitHub Actions hoặc điểm chấm ẩn. Số liệu và giới hạn đầy đủ: [bản review](docs/final_review.md), [eval card](docs/eval_card.md). Commit baseline, PR và CI remote được cập nhật tại [trạng thái nộp bài](docs/submission_status.md).

## Chạy nhanh trên Windows PowerShell

Mở Terminal tại **gốc repo**. Nếu đã có `.venv` và dependency, bỏ qua hai lệnh cài đặt đầu:

```powershell
uv venv .venv --python 3.11
uv pip install --python .venv\Scripts\python.exe -r src\requirements.txt -r src\requirements-lab9.txt

cd src
..\.venv\Scripts\python.exe -m lab9.verify
..\.venv\Scripts\python.exe -m scripts.render_lab9_review
```

Không có `uv`: từ gốc repo, thay phần cài đặt bằng:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r src\requirements.txt -r src\requirements-lab9.txt
```

Không cần activate môi trường hoặc đổi Execution Policy: các lệnh gọi thẳng Python trong `.venv`. Kiểm tra `python --version` trước khi dùng cách cài không có `uv` để bảo đảm Python ≥3.11.

Lệnh tương đương trên Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r src/requirements.txt -r src/requirements-lab9.txt
cd src
../.venv/bin/python -m lab9.verify
../.venv/bin/python -m scripts.render_lab9_review
```

`lab9.verify` chạy smoke, test, judge, detection, sinh lại report/baseline, thử gate, A/A, mutation và trap. `scripts.render_lab9_review` đọc report thực để cập nhật tài liệu; chỉ chạy sau khi verify đạt. Hai lệnh không commit, push hay mở PR. Chúng ghi lại các report trong `src/reports/`.

## Nội dung đã hoàn thành theo milestone

| Mốc | Nội dung | Bằng chứng / mã nguồn |
|---|---|---|
| M0 | Tích hợp Lab 08, môi trường riêng, smoke | [Nguồn nhập và phạm vi](docs/lab08_import.md), `lab9.smoke` |
| M1 | Taxonomy, gắn FM/provenance cho 14 claim, trace case có regression test | [Taxonomy](docs/failure_taxonomy.md), [trace case](docs/trace_case.md), `lab9.evalset`, `lab9.m1_evidence` |
| M2 | Confusion, precision/recall, κ, Rogan–Gladen; audit 15 bất đồng | [Judge audit](docs/judge_audit.md), `lab9.stats`, `lab9.judge` |
| M3 | ApprovalBypass, RefundAmountCorrect, metric FM-08; assertion quote/proposal | `lab9.graders`, `lab9.mutation --detect`, `lab9.m3_evidence` |
| M4 | Paired bootstrap, baseline v1 và gate | `lab9.stats`, `lab9.gate`, `lab9.ci_check` |
| M5 | Eval v2, map cơ chế tấn công sang FM, slice gate | `config/fm_map.yaml`, `config/metric_spec_v2.yaml`, `lab9.evalset --v2` |
| M6 | pass@k/pass^k, hai bộ seed A/A, sàn pass_hat_5 | `lab9.stats`, `lab9.mutation --aa` |
| M7 | Integrity, ratchet, mutation scorecard và trap | `lab9.gate`, `lab9.mutation`, `lab9.traps` |

V1 có **14 item × 5 seed**, v2 có **28 item × 5 seed**; nhãn outcome tách khỏi item. Seeds chính: `11,22,33,44,55`. Metric spec hiện tại: **1.2** cho v1, **2.1** cho v2. [PRD v1.1](docs/PRD_v1.1.md) mô tả tiêu chí chạy đúng và cổng release; [harness map](src/harness_map.yaml) chỉ tới các thành phần.

## Kiểm tra từng phần và đọc exit code

Đoạn sau chạy từ gốc repo trong một PowerShell mới; `$py` giữ đường dẫn Python tuyệt đối sau khi chuyển vào `src/`:

```powershell
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
cd src
& $py -m lab9.smoke
& $py -m lab9.evalset --check
& $py -m lab9.evalset --v2 --check
& $py -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5
& $py -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5
& $py -m lab9.mutation --detect
& $py -m lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json --base-spec config/metric_spec_v2.yaml
```

| Lệnh / trường hợp | Exit mong đợi | Ý nghĩa |
|---|---|---|
| `lab9.verify` | 0 | Tất cả bước khớp kết quả mong đợi, kể cả các lệnh cần exit 1 |
| Judge tone | 0 | Đạt FLOORS: κ≥0,6, precision≥0,8, recall≥0,7 |
| Judge helpful | **1** | Bị loại đúng kỳ vọng vì κ và recall thấp |
| Gate trên `fixed` / `honest_refactor` | 0 | Chấp nhận phiên bản đúng |
| Gate trên regression / từng trap | **1** | Chặn phiên bản hoặc report lỗi; cần đọc lý do, không chỉ nhìn exit code |
| `lab9.mutation` scorecard | 0 | Chặn đủ 3 regression, không báo nhầm |
| `lab9.traps` | 0 | Tất cả trap bị chặn; exit 1 của lệnh tổng này nghĩa là có trap lọt |

Để sinh lại eval set sau khi thay logic gắn FM, chạy `lab9.evalset --build --check`, rồi `lab9.evalset --v2 --build`. Sau khi đổi eval set, nhãn hoặc grader/spec, chạy lại verify để report và baseline cùng nguồn. Không sửa tay JSON kết quả. `.gitattributes` và bộ sinh dữ liệu cố định LF để hash không đổi khi Git chuyển file giữa Windows/Linux.

## Baseline tin cậy và GitHub Actions

Workflow [eval-gate.yml](.github/workflows/eval-gate.yml) chạy khi có **pull request** hoặc **workflow_dispatch**, không chạy chỉ vì push thẳng lên `main`.

1. Chạy verify local, xem [review](docs/final_review.md) và các thay đổi trước khi đưa lên repo.
2. Bootstrap mã chạy, eval set/nhãn, metric spec và baseline v1/v2 trên nhánh base tin cậy theo quy trình nhóm. Với PR, workflow checkout riêng **commit base** để lấy baseline/spec; thêm baseline chỉ trong PR không thay thế được bước này.
3. Core cần `src/reports/baseline_v1.json` và `src/config/metric_spec.yaml` trên base commit. Advanced cần thêm baseline v2 và spec v2. Nếu thiếu, bổ sung baseline vào base trước; không bỏ kiểm tra hoặc dùng âm thầm baseline từ PR.
4. PR chạy evaluator bằng code của PR, so với baseline base và dùng `--base-spec` để chặn nới ngưỡng. Nhánh base cần được chủ repo bảo vệ. Khi đổi version/phạm vi đánh giá, phải thống nhất và sinh lại baseline tương ứng.
5. Nộp theo [SUBMISSION.md](SUBMISSION.md); nội dung mô tả PR đã chuẩn bị tại [PR_DESCRIPTION.md](docs/PR_DESCRIPTION.md). Chỉ đánh dấu CI xanh khi job remote thực sự chạy đạt.

`workflow_dispatch` lấy baseline/spec từ commit được chọn. Trong kiểm tra local, `--base-spec config/...` dùng chính spec hiện tại; việc này không thay thế kiểm tra ratchet với base commit trên CI.

## File kết quả và tài liệu

| Đường dẫn | Vai trò | Git |
|---|---|---|
| `src/data/eval/eval_set_v1.jsonl`, `labels_v1.json`, `eval_set_v2.jsonl`, `labels_v2.json` | Input đánh giá và nhãn riêng | Cần đưa vào commit |
| `src/reports/baseline_v1.json`, `baseline_v2.json` | Baseline sinh bằng evaluator | Đã có ngoại lệ `.gitignore`, cần đưa vào commit |
| `src/reports/eval_fixed.json`, `eval_seeded_regression.json` | Report Core để nộp | Đã có ngoại lệ `.gitignore`, cần đưa vào commit |
| `src/reports/verification.json`, `verification/*.txt` | Tổng hợp 35 bước và log từng lệnh | Bỏ qua; sinh lại bằng verify |
| Các report judge, M1/M3, variant v2 và `reports/traps/` | Bằng chứng phân tích và trap do script sinh | Bỏ qua; sinh lại bằng verify |
| `docs/final_review.md`, `eval_card.md`, `PRD_v1.1.md`, `PR_DESCRIPTION.md` | Review, tiêu chí sản phẩm và nháp PR từ report | Cần đưa vào commit |

Danh sách report trong bảng lấy `src/reports/` làm thư mục gốc cho các tên viết gọn. Bản đồ mã chính: [graders](src/lab9/graders.py), [stats](src/lab9/stats.py), [eval set](src/lab9/evalset.py), [harness](src/lab9/eval.py), [gate](src/lab9/gate.py), [verify](src/lab9/verify.py), [bộ dựng tài liệu](src/scripts/render_lab9_review.py).

## Quy tắc và giới hạn

- Giữ nguyên `src/lab8/`, variant/trap và test gốc; không sửa tay report hoặc đặt nhãn outcome inline trong item.
- Tiền/phê duyệt chấm bằng code. Tone judge đạt FLOORS không thay thế kiểm tra ledger; helpful judge bị loại.
- `swarm` gốc không có reply event: FM-08 ở đây là không áp dụng, không phải bằng chứng reply đúng. Parser FM-08 hỗ trợ các mẫu số tiền VND bằng chữ số đã kiểm tra, chưa hiểu mọi cách diễn đạt.
- MockLLM, dữ liệu synthetic và cỡ mẫu 5 seed không đại diện cho người dùng thật; chưa bảo đảm phát hiện ổn định mọi lỗi hiếm hoặc trap ẩn. Chi tiết tại [eval card](docs/eval_card.md).
- Không đưa `.env`, `.venv`, trace, SQLite hoặc `src/eval/instructor/` vào commit; các đường dẫn này đã bị bỏ qua.

Yêu cầu chấm và checkpoint: [RUBRIC.md](RUBRIC.md), [CHECKPOINTS.md](CHECKPOINTS.md), [SUBMISSION.md](SUBMISSION.md). Hướng dẫn overlay/lịch làm bài ban đầu được giữ nguyên tại [starter gốc](docs/lab09_starter.md); các TODO ở tài liệu đó mô tả lúc bắt đầu lab.
