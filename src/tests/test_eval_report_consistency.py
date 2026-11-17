"""Eval/report: the numbers in the team's reports come from tool output, not from hand edits.

Owner: eval/report. Part of the default host gate (`python -m pytest -q`).

Checks that:
- `reports/benchmark.json` meets the submission spec (4 shapes, seeds 11..55, >= 10 claims)
  and its per-shape summary is exactly what `lab8.metrics.summarize` recomputes from the
  raw trials (a hand-edited summary would not match);
- every run id cited in `report/team/decision_adr.md` exists in the benchmark trials;
- the ADR's chosen shape, pass rate, cost per success and crash safety match the JSON files;
- the R1 ablation report agrees with the main benchmark on the shapes it shares.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from lab8.metrics import summarize

SRC = Path(__file__).resolve().parents[1]
REPO = SRC.parent
BENCHMARK = SRC / "reports" / "benchmark.json"
CRASH = SRC / "reports" / "crash.json"
ABLATION = SRC / "reports" / "ablation_r1.json"
ADR = REPO / "report" / "team" / "decision_adr.md"

REQUIRED_SHAPES = {"workflow", "single", "orchestrator", "swarm"}
REQUIRED_SEEDS = [11, 22, 33, 44, 55]


def _load(path: Path) -> dict:
    if not path.exists():
        pytest.skip(f"{path.name} chưa được tạo")
    return json.loads(path.read_text(encoding="utf-8"))


def _adr_field(label: str) -> str:
    if not ADR.exists():
        pytest.skip("decision_adr.md không tồn tại")
    for line in ADR.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"- {label}:"):
            value = line.split(":", 1)[1].strip()
            if not value:
                pytest.skip(f"ADR chưa điền '{label}'")
            return value
    pytest.fail(f"ADR mất dòng nhãn '{label}'")


def test_benchmark_meets_submission_spec():
    bench = _load(BENCHMARK)
    controlled = bench["controlled_variables"]

    assert set(bench["by_shape"]) == REQUIRED_SHAPES
    assert controlled["seeds"] == REQUIRED_SEEDS
    assert len(controlled["claim_ids"]) >= 10
    assert controlled["model_backend"] == "MockLLM"
    assert controlled["latency"] == "unavailable"
    assert controlled["pricing"]["simulated"] is True
    for shape in REQUIRED_SHAPES:
        trials = [t for t in bench["trials"] if t["shape"] == shape]
        assert len(trials) == len(controlled["claim_ids"]) * len(REQUIRED_SEEDS), shape


@pytest.mark.parametrize("path", [BENCHMARK, ABLATION], ids=lambda p: p.name)
def test_summary_is_recomputed_from_raw_trials(path):
    report = _load(path)
    assert summarize(report["trials"]) == report["by_shape"]


def test_adr_chosen_shape_and_numbers_match_benchmark():
    bench = _load(BENCHMARK)
    shape = _adr_field("Shape chọn")
    assert shape in REQUIRED_SHAPES
    summary = bench["by_shape"][shape]

    pass_line = _adr_field("Pass rate / pass^5 / seed min-max / variance")
    numbers = [float(x) for x in re.findall(r"\d+\.\d+", pass_line)]
    pass_rate, pass5, seed_min, seed_max, variance = numbers[:5]
    assert pass_rate == pytest.approx(summary["pass_rate"], abs=5e-4)
    assert pass5 == pytest.approx(summary["pass_5"], abs=5e-4)
    assert seed_min == pytest.approx(summary["seed_min"], abs=5e-4)
    assert seed_max == pytest.approx(summary["seed_max"], abs=5e-4)
    assert variance == pytest.approx(summary["seed_variance"], abs=5e-7)

    cost = float(re.search(r"\d+\.\d+", _adr_field("Cost per success (mô phỏng, VND)")).group())
    assert cost == pytest.approx(summary["cost_per_success_vnd"], abs=5e-3)


def test_adr_run_ids_exist_in_benchmark():
    bench = _load(BENCHMARK)
    known = {t["run_id"] for t in bench["trials"]}
    cited = re.findall(r"R-[a-z]+-C-\d{3}-s\d+", _adr_field("Run id dẫn chứng"))
    assert cited, "ADR không trích run id nào"
    assert set(cited) <= known, set(cited) - known


def test_adr_crash_safety_matches_crash_report():
    crash = _load(CRASH)
    assert crash["crash_safety"] == f"{crash['passed']}/{crash['count']}"
    assert crash["count"] == 20
    assert crash["crash_safety"] in _adr_field("Crash safety")


def test_ablation_agrees_with_main_benchmark_on_shared_shapes():
    bench = _load(BENCHMARK)
    ablation = _load(ABLATION)
    assert ablation["controlled_variables"] == bench["controlled_variables"]
    for shape, summary in ablation["by_shape"].items():
        assert summary == bench["by_shape"][shape], shape
