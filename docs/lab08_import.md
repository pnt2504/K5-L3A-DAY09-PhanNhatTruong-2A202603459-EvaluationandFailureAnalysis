# Tích hợp Lab 08 vào Lab 09

Ngày thực hiện: 17/11/2026.

## Nguồn

- Repo cùng thư mục cha: `K5-L3A-DAY08-PSTL-FromWorkflowsToAgents`.
- Nhánh nguồn: `main`.
- Commit nguồn: `322db9c061ed921287e481d0778099dc485cd32e`.
- Sao chép từ working tree sạch; repo Lab 08 được giữ nguyên.

## File được đưa sang

Tổng cộng 74 file từ Lab 08, gồm:

- `src/lab8/`: toàn bộ 28 file của package, bao gồm bốn kiến trúc agent, MockLLM, host hoàn tiền, trace và bộ chấm gốc.
- `src/config/{autonomy_policy.yaml,pricing.yaml,tools.manifest.v1.1.yaml}`: luật tự chủ, giá mô phỏng và hợp đồng tool.
- `src/data/{public_claims.jsonl,public_world_state.json}`: 14 claim công khai và trạng thái thế giới để chạy lại agent.
- `src/requirements.txt`, `src/pytest.ini`, `src/harness_map.yaml`, `src/README.md`: dependency, cấu hình test, bản đồ harness và hướng dẫn chạy Lab 08.
- Các test Lab 08 cùng `src/grader_audit/`, `src/scripts/build_public_fixtures.py`, `src/eval/README.md` để giữ khả năng kiểm tra nền và tái tạo fixture.
- `.github/workflows/ci.yml`: giữ CI nền của Lab 08 bên cạnh workflow đánh giá Lab 09.
- `docs/{architecture,business_rules,contracts,metrics,troubleshooting}.md`: ngữ cảnh kiến trúc, nghiệp vụ, hợp đồng, số đo và xử lý lỗi cần cho phân tích trace.

Mọi file sao chép được đối chiếu SHA256 ngay sau khi chép. Riêng `src/harness_map.yaml` sau đó được nâng lên phiên bản `1.2` và thêm `sections.eval` theo mẫu `src/harness_map.eval.yaml`. Toàn bộ 33 file mã nguồn, cấu hình và dữ liệu gốc trong `src/lab8/`, `src/config/`, `src/data/` vẫn khớp SHA256 với Lab 08.

Không đưa sang lịch sử `.git`, môi trường Python cũ, secret, hidden pack, trace, SQLite hay report kết quả Lab 08. Các file đề bài `README.md`, `CHECKPOINTS.md`, `RUBRIC.md`, `SUBMISSION.md` và tài liệu bài tập Lab 09 được giữ lại; README chỉ được bổ sung hướng dẫn cho bản đã tích hợp.

`.gitignore` được bổ sung quy tắc cho `.venv`, `.env`, cache, SQLite journal và `src/eval/instructor/`, giữ các quy tắc bỏ qua report/trace sẵn có của Lab 09.

## Môi trường và M0

Đã tạo `.venv/` riêng cho Lab 09 bằng Python 3.11.9 và cài cả hai bộ dependency:

```powershell
# Từ gốc repo, khi cần thiết lập lại môi trường
uv venv .venv --python 3.11
uv pip install --python .venv\Scripts\python.exe -r src\requirements.txt -r src\requirements-lab9.txt

# Mọi lệnh lab bên dưới chạy từ src/
cd src
..\.venv\Scripts\python.exe -m lab8.smoke
..\.venv\Scripts\python.exe -m lab9.smoke
..\.venv\Scripts\python.exe -m lab9.evalset --build
..\.venv\Scripts\python.exe -m pytest -q
```

Kết quả đã xác nhận:

- `lab8.smoke`: pass; swarm C-001 hoàn 35.000 đồng, trace sạch.
- `lab9.smoke`: `M0 PASS`.
- `lab9.evalset --build`: tạo `src/data/eval/eval_set_v1.jsonl` với 14 item và `labels_v1.json` với 14 nhãn tách riêng.
- `python -m pytest -q`: **152 passed, 7 skipped, 271 deselected, 5 xfailed**. Bộ test mặc định loại các bài tập mang marker `student`; các test liên quan report Lab 08 chưa có được bỏ qua theo thiết kế của test.

## Phần cần làm tiếp

Phần nhập Lab 08 ở trên là bước chuẩn bị M0. Sau đó M1–M7 đã được triển khai: [taxonomy](failure_taxonomy.md), [trace case](trace_case.md), [judge audit](judge_audit.md), trajectory graders, bootstrap, slice/reliability gate và integrity/ratchet. Trạng thái mới cùng output thực nằm ở [final_review.md](final_review.md). Mã, dữ liệu và cấu hình gốc Lab 08 vẫn giữ nguyên.

`.gitignore` đã được mở ngoại lệ cho baseline v1/v2 và report Core `eval_fixed.json`, `eval_seeded_regression.json` để đưa vào commit; report tạm, trace, SQLite và môi trường tiếp tục bị bỏ qua. Các report chỉ sinh bằng script, không sửa tay.
