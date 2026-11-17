"""Reproduce the complete local Lab 09 review, preserving expected negative exits.

python -m lab9.verify
This runs offline and writes generated reports/logs only. It neither commits nor
pushes code. GitHub job execution and instructor hidden tests remain separate.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from lab8.console import utf8_stdio


def main() -> int:
    utf8_stdio()
    source_root = Path(__file__).resolve().parents[1]
    output = source_root / "reports" / "verification"
    output.mkdir(parents=True, exist_ok=True)
    files = sorted(list((source_root / "lab9").glob("*.py")) + list((source_root / "config").glob("*.yaml")))
    digest = hashlib.sha256()
    for path in files:
        digest.update(str(path.relative_to(source_root)).replace("\\", "/").encode("utf-8"))
        digest.update(path.read_bytes())
    run_id = f"V-{datetime.now(timezone(timedelta(hours=7))):%Y%m%d}-{digest.hexdigest()[:12]}"
    results = []

    def run(name: str, module: str, args: list[str], expected: int = 0, required: tuple[str, ...] = ()) -> bool:
        print(f"[{len(results) + 1:02d}] {name} ...", flush=True)
        command = [sys.executable, "-m", module, *args]
        completed = subprocess.run(command, cwd=source_root, env={**os.environ, "PYTHONUTF8": "1"},
                                   capture_output=True, text=True, encoding="utf-8")
        body = completed.stdout + completed.stderr
        (output / f"{name}.txt").write_text(body, encoding="utf-8")
        passed = completed.returncode == expected and all(fragment in body for fragment in required)
        results.append({"name": name, "module": module, "args": args, "expected_exit": expected,
                        "actual_exit": completed.returncode, "passed": passed, "output": body})
        print(f"     {'PASS' if passed else 'FAIL'} (exit {completed.returncode}, expected {expected})", flush=True)
        if not passed:
            print(body, flush=True)
        return passed

    def evaluate(name: str, shape: str, spec: str, report: str) -> bool:
        return run(name, "lab9.eval", ["--shape", shape, "--spec", spec, "--out", report])

    core, advanced = "config/metric_spec.yaml", "config/metric_spec_v2.yaml"
    base1, base2 = "reports/baseline_v1.json", "reports/baseline_v2.json"
    steps = [
        ("smoke", "lab9.smoke", []),
        ("evalset_v1", "lab9.evalset", ["--check"]),
        ("evalset_v2", "lab9.evalset", ["--v2", "--check"]),
        ("tests_core", "pytest", ["-q", "-m", "student", "-o", "addopts=", "-k", "lab9 and not advanced"]),
        ("tests_advanced", "pytest", ["-q", "-m", "student", "-o", "addopts=", "-k", "advanced"]),
        ("tests_evalset_cli", "pytest", ["-q", "tests/test_lab9_evalset.py", "-o", "addopts="]),
        ("tests_host", "pytest", ["-q"]),
        ("m1_evidence", "lab9.m1_evidence", []),
        ("m3_evidence", "lab9.m3_evidence", []),
        ("m3_detection", "lab9.mutation", ["--detect"]),
        ("judge_tone", "lab9.judge", ["--csv", "data/eval/judge_tone_public.csv", "--audit", "5", "--out", "reports/judge_tone_m2.json"]),
    ]
    for name, module, args in steps:
        run(name, module, args)
    run("judge_helpful", "lab9.judge", ["--csv", "data/eval/judge_helpful_public.csv", "--audit", "5", "--out", "reports/judge_helpful_m2.json"], 1, ("FAIL floors",))
    evaluate("baseline_v1", "swarm", core, base1)
    evaluate("pr_v1", "swarm", core, "reports/eval_pr.json")
    run("gate_pr_v1", "lab9.gate", ["--pr", "reports/eval_pr.json", "--baseline", base1, "--spec", core, "--base-spec", core])
    run("ci_check", "lab9.ci_check", ["--pr", "reports/eval_pr.json", "--baseline", base1, "--spec", core])
    for shape, expected in (("fixed", 0), ("seeded_regression", 1)):
        report = f"reports/eval_{shape}.json"
        evaluate(f"evaluate_{shape}_v1", shape, core, report)
        run(f"gate_{shape}_v1", "lab9.gate", ["--pr", report, "--baseline", base1, "--spec", core, "--base-spec", core],
            expected, ("blocked:", "pass_rate") if expected else ("exit 0",))
    evaluate("baseline_v2", "swarm", advanced, base2)
    run("gate_self_v2", "lab9.gate", ["--pr", base2, "--baseline", base2, "--spec", advanced, "--base-spec", advanced])
    run("aa_seeds_1", "lab9.mutation", ["--spec", advanced, "--aa", "66,77,88,99,110"])
    run("aa_seeds_2", "lab9.mutation", ["--spec", advanced, "--aa", "121,132,143,154,165"])
    run("mutation_scorecard", "lab9.mutation", ["--spec", advanced, "--baseline", base2, "--base-spec", advanced],
        required=("mutation score 3/3", "false alarms 0"))
    for shape in ("fixed", "honest_refactor", "seeded_regression", "slice_regression", "flaky_regression"):
        evaluate(f"evaluate_{shape}_v2", shape, advanced, f"reports/eval_{shape}_v2.json")
    slice_report = "reports/eval_slice_regression_v2.json"
    run("public_traps", "lab9.traps", ["--pr", slice_report, "--baseline", base2, "--spec", advanced],
        required=("exit 0",))
    for name in ("evaluator_errors_as_nan", "dropped_failing_rows", "cherry_picked_seeds", "loosened_spec"):
        trap_spec = f"reports/traps/{name}.spec.yaml" if name == "loosened_spec" else advanced
        run(f"trap_{name}", "lab9.gate", ["--pr", f"reports/traps/{name}.json", "--baseline", base2,
            "--spec", trap_spec, "--base-spec", advanced], 1, ("INTEGRITY", "exit 1"))
    report = {"run_id": run_id, "code_sha256": digest.hexdigest(), "passed": all(step["passed"] for step in results),
              "checks": len(results), "steps": results}
    (source_root / "reports" / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{run_id}: {sum(step['passed'] for step in results)}/{len(results)} checks passed")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
