"""M2: calibration decisions, undefined statistics, and replay CLI exit codes."""

import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.student


@pytest.fixture
def stats():
    from lab9 import stats

    return stats


def test_lab9_m2_fail_is_positive(stats):
    human = ["FAIL", "FAIL", "PASS", "PASS", "PASS"]
    predicted = ["FAIL", "PASS", "FAIL", "PASS", "PASS"]
    assert stats.confusion(human, predicted) == {"tp": 1, "fp": 1, "fn": 1, "tn": 2}
    assert stats.precision_recall(human, predicted) == (0.5, 0.5)
    assert stats.cohen_kappa(human, predicted) == pytest.approx(1 / 6)


@pytest.mark.parametrize("human,predicted", [([], []), (["PASS"], []),
                                                    (["PASS"], ["UNKNOWN"])])
def test_lab9_m2_rejects_invalid_calibration_labels(stats, human, predicted):
    with pytest.raises(ValueError):
        stats.confusion(human, predicted)


@pytest.mark.parametrize("human,predicted", [(["PASS"], ["PASS"]),
                                                    (["FAIL"], ["PASS"]),
                                                    (["PASS"], ["FAIL"])])
def test_lab9_m2_zero_precision_recall_denominators(stats, human, predicted):
    assert stats.precision_recall(human, predicted) == (0.0, 0.0)


@pytest.mark.parametrize("human,predicted,want", [
    (["PASS", "FAIL"], ["PASS", "FAIL"], 1.0),
    (["PASS", "FAIL"], ["FAIL", "PASS"], -1.0),
    (["PASS", "FAIL"], ["PASS", "PASS"], 0.0),
    (["PASS", "PASS", "FAIL", "FAIL"], ["PASS", "FAIL", "PASS", "FAIL"], 0.0),
])
def test_lab9_m2_kappa_measures_agreement_beyond_chance(stats, human, predicted, want):
    assert stats.cohen_kappa(human, predicted) == pytest.approx(want)
    assert stats.cohen_kappa(predicted, human) == pytest.approx(want)


@pytest.mark.parametrize("label", ["PASS", "FAIL"])
def test_lab9_m2_unanimous_labels_have_undefined_kappa(stats, label):
    with pytest.raises(ValueError, match="undefined"):
        stats.cohen_kappa([label] * 3, [label] * 3)


@pytest.mark.parametrize("observed,sensitivity,specificity,want", [
    (0.28, 1.0, 1.0, 0.28),
    (0.09, 0.3, 1.0, 0.3),
    (0.9, 0.4, 0.9, 1.0),
    (0.0, 0.8, 0.9, 0.0),
])
def test_lab9_m2_prevalence_correction_and_clipping(stats, observed, sensitivity, specificity, want):
    assert stats.rogan_gladen(observed, sensitivity, specificity) == pytest.approx(want)


@pytest.mark.parametrize("rates", [(0.3, 0.5, 0.5), (-0.1, 0.8, 0.9),
                                  (0.3, 1.1, 0.9), (0.3, 0.8, float("nan")),
                                  (float("inf"), 0.8, 0.9)])
def test_lab9_m2_rejects_undefined_or_invalid_correction(stats, rates):
    with pytest.raises(ValueError):
        stats.rogan_gladen(*rates)


@pytest.mark.parametrize("name,passed,confusion,kappa,precision,recall", [
    ("tone", True, {"tp": 24, "fp": 4, "fn": 6, "tn": 66}, 0.757, 0.857, 0.8),
    ("helpful", False, {"tp": 9, "fp": 0, "fn": 21, "tn": 70}, 0.375, 1.0, 0.3),
])
def test_lab9_m2_public_calibration(name, passed, confusion, kappa, precision, recall):
    from lab9.judge import calibrate

    report = calibrate(Path(f"data/eval/judge_{name}_public.csv"))
    assert report["passed"] is passed
    assert report["confusion"] == confusion
    assert (report["kappa"], report["precision"], report["recall"]) == (kappa, precision, recall)
    assert report["corrected_fail_rate"] == 0.3
    assert len(report["disagreements"]) == confusion["fp"] + confusion["fn"]


@pytest.mark.parametrize("name,expected_exit", [("tone", 0), ("helpful", 1)])
def test_lab9_m2_cli_verdict_matches_saved_report(tmp_path, name, expected_exit):
    source = Path(f"data/eval/judge_{name}_public.csv")
    target = tmp_path / "judge.json"
    result = subprocess.run(
        [sys.executable, "-m", "lab9.judge", "--csv", str(source), "--audit", "5", "--out", str(target)],
        env={**os.environ, "PYTHONUTF8": "1"}, capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == expected_exit, result.stdout + result.stderr
    report = json.loads(target.read_text(encoding="utf-8"))
    assert report["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert report["calibration"]["passed"] is (expected_exit == 0)
    assert ("PASS floors" if expected_exit == 0 else "FAIL floors") in result.stdout


def test_lab9_m2_undefined_kappa_fails_without_crashing(tmp_path):
    from lab9.judge import calibrate, main

    source = tmp_path / "constant.csv"
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item_id", "reply", "human", "judge"])
        writer.writeheader()
        writer.writerows({"item_id": str(i), "reply": "Dạ.", "human": "PASS", "judge": "PASS"}
                         for i in range(5))
    result = calibrate(source)
    assert math.isnan(result["kappa"])
    assert result["corrected_fail_rate"] is None
    assert result["passed"] is False
    target = tmp_path / "report.json"
    assert main(["--csv", str(source), "--out", str(target)]) == 1
    saved = json.loads(target.read_text(encoding="utf-8"))
    assert saved["calibration"]["kappa"] is None
    assert "NaN" not in target.read_text(encoding="utf-8")


def test_lab9_m2_rounding_cannot_turn_a_failure_into_a_pass(monkeypatch, stats):
    from lab9.judge import calibrate

    monkeypatch.setattr(stats, "cohen_kappa", lambda human, judge: 0.5999)
    result = calibrate(Path("data/eval/judge_tone_public.csv"))
    assert result["kappa"] == 0.6  # Rounded display reaches the floor.
    assert result["passed"] is False  # The measurement itself does not.
