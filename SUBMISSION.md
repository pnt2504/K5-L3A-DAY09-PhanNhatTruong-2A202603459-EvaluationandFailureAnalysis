# Nộp bài (hạn 23:59 cùng ngày)
PR từ `starter/d09` → `main` của repo nhóm. Chấm commit cuối trước 23:59; commit sau hạn không tính.

> Đối chiếu ngày 17/11/2026: [checklist review](docs/checklist_review.md). Các hạng mục nộp đã hoàn tất: [PR #1](https://github.com/pnt2504/K5-L3A-DAY09-PhanNhatTruong-2A202603459-EvaluationandFailureAnalysis/pull/1), [CI Lab 09](https://github.com/pnt2504/K5-L3A-DAY09-PhanNhatTruong-2A202603459-EvaluationandFailureAnalysis/actions/runs/44130310352). Xem [trạng thái nộp](docs/submission_status.md) cho commit và kiểm tra mới nhất; không suy ra kết quả chấm ẩn.

## Core (nên xong trước 17:00)
- [x] `src/lab9/{stats,graders,evalset}.py` đã hoàn thành TODO M1–M4
- [x] `src/data/eval/eval_set_v1.jsonl` có `failure_modes`, `labels_v1.json` tách riêng
- [x] `docs/failure_taxonomy.md`, `docs/trace_case.md` (1 case + regression test), `docs/judge_audit.md`, `docs/eval_card.md`, `docs/PRD_v1.1.md`
- [x] `src/reports/baseline_v1.json`, `eval_fixed.json`, `eval_seeded_regression.json` (sinh bằng script)
- [x] `harness_map.yaml` có section `eval` (mẫu: `src/harness_map.eval.yaml`)
- [x] Job `eval-gate` xanh; dán output gate exit 1 của `seeded_regression` vào mô tả PR
  - Output đã đăng trong PR #1; job eval-gate đã SUCCESS, bằng chứng tại https://github.com/pnt2504/K5-L3A-DAY09-PhanNhatTruong-2A202603459-EvaluationandFailureAnalysis/actions/runs/44130310352.

## Advanced / Expert (tới 23:59)
- [x] `config/fm_map.yaml`, `config/metric_spec_v2.yaml` (slices, `pass_hat_5`, metric FM-08), `stats.pass_at_k/pass_hat_k`, `gate.slice_check`, `gate.integrity_check`
- [x] `src/data/eval/eval_set_v2.jsonl` + `labels_v2.json` (sinh bằng `evalset --v2 --build`)
- [x] `src/reports/baseline_v2.json` (sinh bằng script) → job `eval-gate-v2` chạy và xanh
  - Baseline đã commit trên main tại 5d6b8e7; job eval-gate-v2 đã SUCCESS.
- [x] Mô tả PR: output `lab9.mutation` (scorecard + `--aa`) và 4 dòng `exit 1` của các trap
  - Nội dung đầy đủ trong docs/PR_DESCRIPTION.md đã được đăng vào PR #1.
- [x] `docs/eval_card.md` thêm mục v2: ngưỡng chọn từ A/A, slice nào bắt lỗi nào, và giới hạn cỡ mẫu (bug 1/3 seed không phát hiện ổn định với 5 seed)
