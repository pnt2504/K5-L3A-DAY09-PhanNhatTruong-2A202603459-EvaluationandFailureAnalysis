# Đối chiếu yêu cầu nộp Lab 09

Ngày đối chiếu: **17/11/2026**. Nguồn yêu cầu: [SUBMISSION](../SUBMISSION.md), [CHECKPOINTS](../CHECKPOINTS.md), [RUBRIC](../RUBRIC.md).

Report `V-20261117-53dd90c2bd24` đạt 35/35 bước; fingerprint mã/config của report vẫn khớp working tree lúc đối chiếu. Đây là kiểm tra local/public, chưa phải kết quả GitHub Actions hoặc chấm ẩn.

## Core

| Yêu cầu | Trạng thái | Bằng chứng / phần còn thiếu |
|---|---|---|
| Hoàn thành TODO M1–M4 | Đủ ở local | Stats, graders, evalset và bootstrap đã triển khai; 95 test Core pass. |
| V1 có FM, provenance và nhãn riêng | Đủ ở local | 14 item, 14 nhãn; tất cả có FM; `evalset --check` sạch. |
| Taxonomy ≥5 FM có bằng chứng | Đủ bằng chứng công khai | 8 probe lỗi dương, event sai đầu tiên và đối chứng; chưa đối chiếu 5 anchor với key riêng của giảng viên. |
| Trace case và regression test | Đủ ở local | C-002@11 và swarm@55; test xác nhận DB=2 bị đổi thành 5, ledger sai 20.000. |
| Judge calibration và audit ≥5 bất đồng | Đủ ở local | Tone đạt, helpful bị loại; audit 15 bất đồng, có đề xuất sửa rubric. |
| Grader detection ≥80%, false alarm ≤10% | Đạt ở local | Lệnh `mutation --detect`: detection 100%, false alarms 0%. FM-08 có test harness thực. |
| Baseline v1, fixed, seeded regression do script sinh | Có file, chưa commit | Các file ở `src/reports/` tồn tại, đã được cho phép qua `.gitignore`, nhưng chưa được theo dõi trong Git. |
| Eval card và PRD có số liệu/run ID/giới hạn | Đủ nội dung local | File đã sinh từ report; gate owner mới là đề xuất, Product approver chưa được nhóm xác nhận. |
| Harness map có section eval | Đủ ở local | `src/harness_map.yaml` phiên bản 1.3; file chưa được theo dõi trong Git. |
| Job eval-gate xanh | **Chưa có bằng chứng remote** | Lệnh tương đương đạt local; chưa có PR/URL job GitHub Actions. |
| Output gate đỏ trong mô tả PR | **Có bản nháp, chưa đăng PR** | `docs/PR_DESCRIPTION.md` có output đầy đủ, gồm `pass_rate` bị chặn. |

## Advanced / Expert

| Yêu cầu | Trạng thái | Bằng chứng / phần còn thiếu |
|---|---|---|
| Map cơ chế tấn công và eval set v2 | Đủ ở local | Map đủ 8 cơ chế; 28 item, 28 nhãn; mỗi FM bị tấn công có ít nhất 3 item. |
| money_movement/adversarial và pass_hat_5 blocking | Đủ ở local | Spec v2.1: hai slice blocking; pass_hat_5 sàn 0,80; FM-08 cũng blocking. |
| Slice gate phát hiện regression bị trung bình che khuất | Đạt trên public variant | `slice_regression` chỉ bị chặn bởi `slice:money_movement/pass_rate`. Variant ẩn chưa chạy. |
| pass@k/pass^k và từ chối tham số sai | Đạt test công khai/mở rộng | 48 test Advanced pass, có kiểm tra biên và quan hệ xác suất. |
| A/A hai bộ seed và giải thích sàn | Đủ ở local | Cả hai A/A cho Δ=0; eval card nêu lý do model thật có nhiễu và giới hạn 5 seed. |
| Baseline v2 và job eval-gate-v2 xanh | **File đã có, CI còn thiếu** | Baseline chưa được commit trên base branch; job remote chưa được xác nhận. |
| Mutation scorecard và chấp nhận refactor đúng | Đạt trên public variant | 3/3 regression bị chặn, 0 báo nhầm; fixed/honest_refactor được qua. |
| Chặn bốn trap và kiểm tra integrity/ratchet | Đạt ở local | Mỗi trap CLI exit 1 với INTEGRITY; thêm test duplicate row, evaluator errors trên report xanh, summary/slice/seed bị sửa. |
| Output scorecard, A/A và trap trong PR | **Có bản nháp, chưa đăng PR** | Đã chuẩn bị trong `docs/PR_DESCRIPTION.md`. |
| Chấm hidden variant/trap/vector | Chưa xác nhận | Bộ chấm riêng không có trong repo; public pass không đủ để khẳng định đạt toàn bộ điểm. |

## Những việc còn thiếu để nộp

1. **Đưa đủ file vào Git và commit.** Ngoài mã sửa, nhiều file mới còn untracked: package Lab 08, dependency, test, eval set/nhãn v1/v2, harness map và các baseline/report bắt buộc. Chỉ dùng `git commit -am` sẽ bỏ sót các file mới này. Kiểm tra danh sách cần nộp trước khi stage/commit.
2. **Thiết lập baseline/spec trên base branch tin cậy.** HEAD `d1b9471` lúc đối chiếu chưa chứa baseline v1/v2 hoặc package Lab 08. Workflow hiện checkout commit base riêng; baseline chỉ có trong working tree hoặc trong PR chưa đủ. Cần thống nhất bước bootstrap theo quy trình nhóm trước PR đánh giá.
3. **Tạo/push nhánh và mở PR theo yêu cầu.** Nhánh hiện tại là `main`; chưa có nhánh nộp `starter/d09` hoặc PR được xác nhận trong tác vụ này. Dùng nội dung `docs/PR_DESCRIPTION.md` cho mô tả PR thực tế, gồm log gate, mutation, A/A và trap; bảo đảm commit cuối đúng hạn quy định.
4. **Xác nhận hai job remote.** Sau khi push/mở PR, kiểm tra `eval-gate` và `eval-gate-v2` thực sự chạy và xanh; không dùng kết quả local thay cho mục này. Kiểm tra GitHub branch protection và quyền truy cập theo cấu hình repo nhóm.

Về tài liệu: nhóm nên xác nhận người chịu trách nhiệm gate và người duyệt Product nếu cần dùng phần phê duyệt của PRD; hiện không có chữ ký/phê duyệt vận hành thật. Việc chưa có dữ liệu người dùng thật/held-out judge đã được nêu là giới hạn, không phải một hạng mục lập trình bắt buộc bị bỏ quên của bài lab.

## Không phải yêu cầu bắt buộc còn thiếu

- Bonus port grader sang Inspect AI/DeepEval chưa làm; đây là điểm cộng tùy chọn.
- Không cần sửa agent Lab 08 để xóa lỗi được gài sẵn; yêu cầu là giữ nguyên và đánh giá đúng.
- Các mục chấm ẩn chỉ giảng viên có thể xác nhận; không cần tạo key hoặc giả kết quả.

## Kết luận

Chưa thấy thiếu hạng mục triển khai bắt buộc trong phạm vi local/public đã kiểm tra. **Bài chưa hoàn tất quy trình nộp** vì còn commit đủ file, bootstrap baseline, mở PR và xác nhận CI remote. Checklist ở `SUBMISSION.md` giữ các mục này chưa đánh dấu hoàn thành.
