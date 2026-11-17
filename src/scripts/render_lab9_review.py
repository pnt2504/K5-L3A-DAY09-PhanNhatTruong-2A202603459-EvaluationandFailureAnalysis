"""Render submission documents from actual verification/evaluation reports.

Run from src/: python -m scripts.render_lab9_review
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re

from lab9.eval import load_spec, per_item
from lab9.gate import check
from lab9.stats import paired_bootstrap


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
                     + ["| " + " | ".join(str(value) for value in row) + " |" for row in rows])


def main():
    root = Path(__file__).resolve().parents[1]
    docs = root.parent / "docs"
    read = lambda name: json.loads((root / "reports" / name).read_text(encoding="utf-8"))
    verified = read("verification.json")
    if not verified["passed"]:
        raise SystemExit("Verification has failures; do not render a successful review.")
    steps = {step["name"]: step for step in verified["steps"]}
    b1, b2 = read("baseline_v1.json"), read("baseline_v2.json")
    fixed, seeded = read("eval_fixed.json"), read("eval_seeded_regression.json")
    spec1, spec2 = load_spec(), load_spec(Path("config/metric_spec_v2.yaml"))
    m3 = read("m3_evidence.json")
    tone, helpful = read("judge_tone_m2.json"), read("judge_helpful_m2.json")
    variants = {name: read(f"eval_{name}_v2.json") for name in
                ("fixed", "honest_refactor", "seeded_regression", "slice_regression", "flaky_regression")}

    def ci(candidate, base, metric):
        left, right = per_item(candidate, metric), per_item(base, metric)
        keys = sorted(left)
        delta, lo, hi = paired_bootstrap([left[k] for k in keys], [right[k] for k in keys])
        return f"{delta:+.3f} [{lo:+.3f}, {hi:+.3f}]"

    metrics = [m["id"] for m in spec1["metrics"]]
    v1_table = table(["Metric", "Baseline swarm", "fixed", "seeded_regression"],
                     [(metric, b1["metrics"][metric], fixed["metrics"][metric], seeded["metrics"][metric]) for metric in metrics])
    decisions = []
    for name, report in variants.items():
        blocked, _ = check(report, b2, spec2, spec2)
        decisions.append((name, report["metrics"]["pass_rate"], report["metrics"]["pass_hat_5"],
                          "BLOCK" if blocked else "MERGE", ", ".join(blocked) or "Không chặn"))
    variant_table = table(["Variant", "pass_rate", "pass_hat_5", "Gate", "Lý do"], decisions)
    test_rows = []
    for name in ("tests_core", "tests_advanced", "tests_evalset_cli", "tests_host"):
        summary = re.findall(r"\d+ passed[^\n]*", steps[name]["output"])[-1]
        test_rows.append((name, summary))
    tests_table = table(["Bộ kiểm tra", "Output thực"], test_rows)
    threshold_table = table(["Metric", "Loại", "Ngưỡng", "Blocking", "Baseline v1"],
        [(m["id"], m["kind"], json.dumps(m["threshold"], ensure_ascii=False),
          "Có" if m.get("blocking") else "Không", b1["metrics"][m["id"]]) for m in spec1["metrics"]])
    items2 = [json.loads(line) for line in Path(spec2["eval_set"]).read_text(encoding="utf-8").splitlines() if line.strip()]
    attacked = {fm for item in items2 if item["split"] == "adversarial" for fm in item["failure_modes"]}
    count = Counter(fm for item in items2 for fm in item["failure_modes"])
    coverage = table(["FM bị tấn công", "Số item trong v2"], [(fm, count[fm]) for fm in sorted(attacked)])
    reliability_floor = next(m for m in spec2["metrics"] if m["id"] == "pass_hat_5")["threshold"]["min"]
    slices_text = "; ".join(f"{s['name']} min {s['min']}" for s in spec2["slices"])
    v2_thresholds = table(["Metric v2 blocking", "Ngưỡng", "Baseline"],
        [(m["id"], json.dumps(m["threshold"]), b2["metrics"][m["id"]]) for m in spec2["metrics"] if m.get("blocking")])
    smoke_id = verified["run_id"]
    limitations = """- Dữ liệu synthetic, MockLLM và judge replay; chưa có người dùng thật hoặc held-out judge mới.
- V1 chỉ 14 item, v2 28 item, mỗi item 5 seed; CI rộng, một bug kích hoạt theo seed % 3 không được phát hiện ổn định chỉ với 5 seed. Không hạ ngưỡng để khớp tên variant.
- `swarm` gốc không emit reply. Metric FM-08 trả `not_applicable` (bool True theo scaffold) cho trace không có reply; điểm 1,0 ở swarm không chứng minh nội dung reply đúng. `fixed`/`honest_refactor` có reply và đã được kiểm tra riêng.
- Parser FM-08 hỗ trợ mẫu số tiền VND bằng chữ số, dấu phân cách và câu hoàn thành phổ biến; chưa hiểu mọi diễn đạt tự nhiên như số tiền viết bằng chữ. Reply được phát ra nhưng không kiểm chứng được sẽ fail.
- Integrity kiểm tra hash nguồn, coverage, bộ seed, slice, evaluator errors và tự nhất quán của score. Không có chữ ký thực thi: người có thể sửa đồng bộ mọi score và nguồn vẫn có thể giả report. CI phải tự chạy evaluator và lấy baseline/spec từ commit base tin cậy.
- Kiểm tra public/local đã chạy; bộ chấm ẩn chưa có trong repo. Trạng thái commit, PR và GitHub Actions thực tế được cập nhật riêng tại [submission_status.md](submission_status.md), không suy ra từ kết quả local.
"""
    commands = """```powershell
# Từ gốc repo
cd src
..\\.venv\\Scripts\\python.exe -m lab9.verify
..\\.venv\\Scripts\\python.exe -m scripts.render_lab9_review
```
"""
    eval_card = f"""# Eval card — LogiX-VN refund agent

Sinh từ report thực bởi `python -m scripts.render_lab9_review`; verification **{smoke_id}**.

## Phiên bản và nguồn

- Fingerprint mã/config của lượt xác minh: `{verified['code_sha256']}`. Commit runtime/baseline và nhánh nộp được ghi tại [trạng thái nộp](submission_status.md).
- V1: `{b1['run_id']}`, eval set SHA `{b1['manifest']['eval_set_sha']}`, labels SHA `{b1['manifest']['labels_sha']}`, metric spec {spec1['metric_spec_version']}.
- V2: `{b2['run_id']}`, eval set SHA `{b2['manifest']['eval_set_sha']}`, labels SHA `{b2['manifest']['labels_sha']}`, metric spec {spec2['metric_spec_version']}.
- Seeds chính: {b1['manifest']['seeds']}. Nhãn tách khỏi item; label outcome giữ nguyên nguồn gốc.

## Kết quả Core

{v1_table}

Paired bootstrap pass_rate của seeded_regression − baseline: **{ci(seeded, b1, 'pass_rate')}**. Khoảng hoàn toàn dưới 0 nên chặn; fixed − baseline: {ci(fixed, b1, 'pass_rate')} nên được qua. `ci_check` xác nhận baseline là swarm và có metric FM-08 capability blocking.

Judge tone: κ={tone['calibration']['kappa']}, P={tone['calibration']['precision']}, R={tone['calibration']['recall']}, đạt FLOORS. Helpful: κ={helpful['calibration']['kappa']}, P={helpful['calibration']['precision']}, R={helpful['calibration']['recall']}, bị loại. Audit 15 bất đồng ở [judge_audit.md](judge_audit.md); giữ nguyên nhãn gốc kể cả H-081 cần adjudication.

## M3 — Trajectory assertion

- Detection chính thức (`mutation --detect`): output **{steps['m3_detection']['output'].strip()}**.
- Panel fault injection: {m3['summary']['known_fault_detection']['count']}/{m3['summary']['known_fault_detection']['total']} trace lỗi được bộ grader phát hiện; hai grader tiền/phê duyệt: {m3['summary']['money_approval_detection']['count']}/{m3['summary']['money_approval_detection']['total']}.
- FM-08: {m3['summary']['fm08_detection']['count']}/{m3['summary']['fm08_detection']['total']} lỗi reply bị bắt dù bộ chấm outcome Lab 08 cho qua.
- Báo nhầm fixed {m3['summary']['fixed_false_positives']['count']}/{m3['summary']['fixed_false_positives']['total']}; honest_refactor {m3['summary']['honest_refactor_false_positives']['count']}/{m3['summary']['honest_refactor_false_positives']['total']}.
- `proposal_matches_quote` giải thích FM-05 khi agent tự trừ tiền trước, kể cả trường hợp cuối cùng không ghi ledger; metric theo dõi, không blocking để không thay thế bài tập slice gate.

Trace case và regression test: [trace_case.md](trace_case.md). Không sửa Lab 08, variant hoặc trap được cung cấp.

## V2 — Slice, nhiễu và độ tin cậy

{variant_table}

- `slice_regression` chỉ bị chặn bởi `money_movement/pass_rate`, dù trung bình toàn tập vượt sàn; thay đổi câu chữ trung thực vẫn merge.
- A/A trên hai bộ seed 66/77/88/99/110 và 121/132/143/154/165 cho Δ=0 ở tất cả metric. Đây là đặc điểm MockLLM, không phải bảo đảm model thật không có nhiễu.
- Baseline `pass_hat_5`={b2['metrics']['pass_hat_5']}; sàn {reliability_floor:.2f}, cách baseline {b2['metrics']['pass_hat_5'] - reliability_floor:.4f} và nằm ngoài dải A/A đo được. Giữ sàn tối thiểu của rubric, không chỉnh theo tên mutant. Model thật cần thêm A/A và dữ liệu độc lập trước khi chọn lại sàn.
- `pass@k` là xác suất ít nhất một lần đúng; `pass^k` là xác suất tất cả k lần đúng, ước lượng bằng tổ hợp không hoàn lại. Gate dùng per-item estimator trên đủ seed, không lấy trung bình trần của tên metric không có trong row.
- Các slice: {slices_text}; tất cả blocking và không được giảm có ý nghĩa.

{coverage}

## M7 — Integrity và ratchet

Bốn trap công khai đều bị chặn với CLI exit 1: NaN/None do evaluator crash, bỏ dòng fail, chọn seed đẹp, nới spec. Test thêm duplicate row, evaluator failure trên report xanh, sửa aggregate, đổi item/seed, relabel slice và bỏ metric/slice/no_significant_drop. Ratchet so với `--base-spec` từ commit base; cùng eval-set version chỉ được siết ngưỡng.

## Tái tạo, vai trò và giới hạn

{commands}

Eval owner đề xuất: Phan Nhật Trường (người thực hiện lab), xử lý gate đỏ bằng đọc trace và sửa phiên bản agent ở bài phù hợp; không sửa Lab 08 trong Lab 09. Product approver cho pilot thật chưa chỉ định. Không có phê duyệt triển khai thật trong tài liệu này.

{limitations}
"""
    prd = f"""# PRD v1.1 — LogiX-VN: tiêu chí đánh giá và cổng release

Sinh từ report của verification `{smoke_id}`. Kế thừa nghiệp vụ Lab 08; không thay đổi tính năng agent hoặc ký phê duyệt vận hành.

## Phạm vi pilot

Trong lab: claim text thuộc một đơn, principal sở hữu đơn, hoàn phí vận chuyển trễ hoặc bồi thường damage đã xác minh bằng dữ liệu synthetic. Chính sách hiện hành và order DB là nguồn sự thật. Tiền bị giới hạn bởi approval, paid amount và trần theo đơn; host trừ lịch sử hoàn đúng một lần. Model không tạo approval, tính tiền hoặc tự ghi ledger.

Ngoài phạm vi: thanh toán thật, claim gom nhiều đơn, tranh chấp pháp lý, tự tạo quyền duyệt, xử lý dữ kiện chủ đơn khác. Thiếu mã đơn phải hỏi lại; ngoài scope phải chuyển xử lý, không tiết lộ PII. Đây là thử nghiệm MockLLM, chưa đo trên khách hàng thật.

## Định nghĩa chạy đúng

Baseline v1: `{b1['run_id']}`. Các ngưỡng đọc trực tiếp từ metric spec {spec1['metric_spec_version']}:

{threshold_table}

Giảm có ý nghĩa: CI 95% paired bootstrap của PR − baseline nằm hoàn toàn dưới 0; đơn vị resample là item đã lấy trung bình các seed, cặp item giữ nguyên. Safety đếm số vi phạm và phải bằng 0.

V2 dùng `{b2['run_id']}` và spec {spec2['metric_spec_version']}:

{v2_thresholds}

Slices: {slices_text}, tất cả có no_significant_drop. Mọi con số nguồn và so sánh nằm ở [eval_card.md](eval_card.md).

## Failure mode và trách nhiệm đo

| FM | Grader/kiểm tra | Loại | Vì sao |
|---|---|---|---|
| FM-01 | SecretLeak | code | So canary/chuỗi bị cấm trên artifact |
| FM-02 | TrialPass, ReplyAmountMatchesLedger | code | Đối chiếu trạng thái, quyết định host và tiền thực ghi; không nhầm denial với một bypass có tiền |
| FM-03 | DbFactKept, RefundAmountCorrect | code | Fact DB và ledger có nguồn cấu trúc; lưu ý override im lặng |
| FM-04 | RefundAmountCorrect, ProposalMatchesQuote | code | Tiền nguyên VND, không dùng cảm nhận lời văn |
| FM-05 | ProposalMatchesQuote, RefundAmountCorrect | code | Quote đầy đủ phải vào host, không tự trừ trước |
| FM-06 | TrialPass, RefundAmountCorrect | code | So chính sách hiện hành và nhãn/ledger |
| FM-07 | ApprovalBypass | code | Ledger row ngoài claim là vi phạm phạm vi |
| FM-08 | ReplyAmountMatchesLedger | code | Tiền thông báo phải khớp khoản host ghi |
| FM-09 | Scope read, SecretLeak, ApprovalBypass | code | Kiểm tra ranh giới principal; v2 có tình huống ngoài scope, chưa chứng minh lỗi dương |
| Tone | Judge replay đã calibration | judge | Chỉ giao tiếp; không được quyết tiền/phê duyệt |

## Cổng release và baseline tin cậy

Exit 1 = không merge; đọc lý do, xác minh trace rồi sửa lỗi đúng tầng. Không sửa report hoặc nới ngưỡng cùng version để được qua. Nếu thay phạm vi/eval set, tăng eval_set_version và sinh baseline mới; nếu thay metric, tăng metric_spec_version và kiểm tra ratchet.

Workflow lấy baseline và base-spec từ `github.event.pull_request.base.sha`; workflow_dispatch dùng commit được chọn. Report PR được CI tự chạy. Baseline v1/v2 và runtime đã bootstrap trên main; không có fallback âm thầm dùng baseline từ PR. Chủ repo chịu trách nhiệm bảo vệ nhánh base. Xem [trạng thái nộp](submission_status.md) để xác nhận commit, PR và CI remote.

Người xử lý gate đề xuất: Phan Nhật Trường. Product approver chưa chỉ định; không giả lập chữ ký. Waiver vận hành thật chưa có quy trình được phê duyệt; lab không cho waiver bằng nới ngưỡng hoặc sửa dữ liệu.

## Bằng chứng còn thiếu

{limitations}

## Điều kiện cập nhật tiếp

V1.2 cần dữ liệu held-out và nhãn người mới, kiểm định parser trên reply thực, nhiều seed hơn cho lỗi hiếm, và nguồn report do CI xác thực. Mọi thay đổi phải có giải thích version, baseline mới khi cần và chạy lại `lab9.verify`.
"""
    review = f"""# Review hoàn thành Lab 09

Verification **{smoke_id}**: **{verified['checks']}/{verified['checks']} bước đạt** trên working tree hiện tại. Không có test public/local thất bại trong lượt này. Không suy ra điểm chấm ẩn hoặc trạng thái GitHub Actions.

## Theo từng milestone

| Mốc | Đã làm | Bằng chứng |
|---|---|---|
| M0 | Tích hợp Lab 08, dependency riêng, smoke | smoke PASS |
| M1 | Taxonomy 8 lỗi dương, 14 item có FM/provenance, trace case và regression test | evalset v1 sạch; m1_evidence |
| M2 | Confusion, P/R, κ, Rogan–Gladen, audit 15 bất đồng | Tone PASS; helpful FAIL đúng kỳ vọng |
| M3 | ApprovalBypass, RefundAmountCorrect, FM-08; thêm quote assertion để giải thích lỗi | detection 100%, false alarm 0%; m3_evidence |
| M4 | Paired bootstrap, baseline v1 và gate | Fixed exit 0; seeded_regression exit 1, pass_rate CI {ci(seeded, b1, 'pass_rate')} |
| M5 | Map đủ 8 cơ chế tấn công, eval v2 28 item, slice gate | money_movement chặn slice_regression |
| M6 | pass@k/pass^k, kiểm tra tham số, hai A/A seed set, sàn pass_hat_5 | A/A Δ=0; flaky_regression bị chặn |
| M7 | Integrity, recompute aggregate, ratchet, trusted CI base | 3/3 mutant bị chặn, 0 báo nhầm; 4/4 public trap exit 1 |

## Tests thực tế

{tests_table}

Số test ở các lượt có thể trùng nhau (host chứa test CLI evalset); không cộng để thổi số test duy nhất. Những skip/xfail của nền Lab 08 giữ nguyên theo thiết kế.

## Kết quả v2

{variant_table}

## Nhận xét review

- Tiền lấy từ ledger, approval từ nhãn độc lập; reply đẹp không được che sai tiền.
- Quote assertion là theo dõi, không blocking: giữ vai trò riêng của slice gate, không chặn mọi thay đổi chỉ vì khác đường đi.
- Gate không bỏ qua None/NaN, evaluator errors, duplicate/missing row, seed/item khác baseline, slice bị đổi hoặc summary không khớp row.
- Ratchet và metadata gắn với nguồn được so sánh; CI checkout base commit riêng để PR không tự thay baseline/spec tham chiếu.
- Mọi report được script sinh, Lab 08 và các variant/trap có sẵn được giữ nguyên.

## Giới hạn cần biết trước khi nộp

{limitations}

## Tài liệu và tái tạo

- [Eval card](eval_card.md), [PRD v1.1](PRD_v1.1.md), [taxonomy](failure_taxonomy.md), [trace case](trace_case.md), [judge audit](judge_audit.md).
- [Nội dung mô tả PR](PR_DESCRIPTION.md). URL PR và kết quả CI thực tế: [trạng thái nộp](submission_status.md).
- Baseline v1/v2 và report fixed/seeded đã được cho phép qua `.gitignore` để đưa vào commit; trace, SQLite, môi trường và report tạm tiếp tục bị bỏ qua.

{commands}
"""
    pr_description = f"""# Hoàn thiện Lab 09 — Evaluation & Failure Analysis

Thêm đánh giá tái lập cho LogiX-VN: taxonomy, judge calibration, trajectory graders, paired bootstrap, slice/reliability gate và kiểm tra integrity/ratchet. Giữ nguyên agent Lab 08, variant và trap của starter.

## Validation

Verification `{smoke_id}` đạt {verified['checks']}/{verified['checks']} bước local. Runtime/baseline đã bootstrap trên base commit tin cậy `5d6b8e7`; trạng thái PR và GitHub Actions được xác nhận riêng tại `docs/submission_status.md`.

{tests_table}

## Core gate: seeded regression phải bị chặn

```text
{steps['gate_seeded_regression_v1']['output'].strip()}
```

## Mutation scorecard

```text
{steps['mutation_scorecard']['output'].strip()}
```

## A/A — hai bộ seed

```text
{steps['aa_seeds_1']['output'].strip()}
{steps['aa_seeds_2']['output'].strip()}
```

## Bốn trap: exit 1

"""
    for name in ("evaluator_errors_as_nan", "dropped_failing_rows", "cherry_picked_seeds", "loosened_spec"):
        step = steps[f"trap_{name}"]
        reasons = [line for line in step["output"].splitlines() if "INTEGRITY" in line]
        pr_description += f"- `{name}`: exit {step['actual_exit']}; {reasons[0].strip() if reasons else 'xem log'}\n"
    pr_description += "\nChi tiết số liệu, ngưỡng và giới hạn: `docs/eval_card.md`, `docs/final_review.md`. Chưa có kết quả chấm ẩn.\n"
    for name, body in (("eval_card.md", eval_card), ("PRD_v1.1.md", prd),
                       ("final_review.md", review), ("PR_DESCRIPTION.md", pr_description)):
        body = "\n".join(line.rstrip() for line in body.splitlines()).rstrip() + "\n"
        (docs / name).write_text(body, encoding="utf-8", newline="\n")
        print(f"wrote docs/{name}")
    # M1 docs cite the generated dataset hash; refresh it after portable LF rebuilds.
    m1_id = read("m1_evidence.json")["run_id"]
    for name in ("failure_taxonomy.md", "trace_case.md"):
        path = docs / name
        body = re.sub(r"M1-[0-9a-f]{12}", m1_id, path.read_text(encoding="utf-8"))
        body = body.replace("bằng chứng lỗi dương cần pack v2.", "v2 bổ sung tình huống scope nhưng chưa quan sát lỗi dương.")
        path.write_text(body, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
