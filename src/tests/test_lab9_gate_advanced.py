"""General integrity/ratchet tests beyond the public trap names."""

import copy
import math

import pytest

pytestmark = pytest.mark.student


def fixture_report():
    spec = {"eval_set_version": "v2", "metrics": [
        {"id": "pass_rate", "kind": "capability", "blocking": True,
         "threshold": {"min": 0.8, "no_significant_drop": True}}],
        "slices": [{"name": "money_movement", "metric": "pass_rate", "min": 0.9,
                    "blocking": True, "no_significant_drop": True}]}
    rows = [{"item_id": f"item-{i}", "seed": seed, "pass_rate": True, "slices": ["money_movement"]}
            for i in range(4) for seed in (1, 2)]
    report = {"manifest": {"eval_set_sha": "same", "items": 4, "seeds": [1, 2]},
              "metrics": {"pass_rate": 1.0}, "rows": rows, "evaluator_failures": []}
    return spec, report


@pytest.mark.parametrize("fault", ["duplicate", "green_evaluator_error", "missing_score", "nan_score",
                                   "forged_summary", "relabel_slice", "replace_item", "changed_seed"])
def test_lab9_advanced_untrusted_rows_are_blocked(fault):
    from lab9.gate import integrity_check

    spec, baseline = fixture_report()
    candidate = copy.deepcopy(baseline)
    if fault == "duplicate":
        candidate["rows"][-1] = copy.deepcopy(candidate["rows"][0])
    elif fault == "green_evaluator_error":
        candidate["evaluator_failures"] = ["grader crashed despite all scores being green"]
    elif fault == "missing_score":
        candidate["rows"][0]["pass_rate"] = None
    elif fault == "nan_score":
        candidate["rows"][0]["pass_rate"] = math.nan
    elif fault == "forged_summary":
        candidate["metrics"]["pass_rate"] = 0.999
    elif fault == "relabel_slice":
        for row in candidate["rows"]:
            if row["item_id"] == "item-0":
                row["slices"] = ["unimportant"]
    elif fault == "replace_item":
        for row in candidate["rows"]:
            if row["item_id"] == "item-0":
                row["item_id"] = "easy-replacement"
    else:
        candidate["manifest"]["seeds"] = [1, 3]
        for row in candidate["rows"]:
            if row["seed"] == 2:
                row["seed"] = 3
    assert integrity_check(baseline, baseline, spec) == []
    assert integrity_check(candidate, baseline, spec)


@pytest.mark.parametrize("fault", ["min", "drop_metric", "unblock", "remove_ci", "drop_slice", "slice_min", "slice_ci"])
def test_lab9_advanced_ratchet_rejects_different_ways_to_loosen(fault):
    from lab9.gate import integrity_check

    original, baseline = fixture_report()
    current = copy.deepcopy(original)
    if fault == "min":
        current["metrics"][0]["threshold"]["min"] = 0.7
    elif fault == "drop_metric":
        current["metrics"] = []
    elif fault == "unblock":
        current["metrics"][0]["blocking"] = False
    elif fault == "remove_ci":
        current["metrics"][0]["threshold"].pop("no_significant_drop")
    elif fault == "drop_slice":
        current["slices"] = []
    elif fault == "slice_min":
        current["slices"][0]["min"] = 0.8
    else:
        current["slices"][0].pop("no_significant_drop")
    assert any("ratchet" in error for error in integrity_check(baseline, baseline, current, original))


def test_lab9_advanced_stricter_thresholds_and_self_comparison_are_allowed():
    from lab9.gate import check

    original, baseline = fixture_report()
    current = copy.deepcopy(original)
    current["metrics"][0]["threshold"]["min"] = 0.9
    blocked, _ = check(baseline, baseline, current, original)
    assert blocked == []


@pytest.mark.parametrize("bad", [None, {}, {"rows": []}, {"rows": [None], "metrics": {}, "manifest": {}}])
def test_lab9_advanced_malformed_reports_fail_closed(bad):
    from lab9.gate import check

    spec, baseline = fixture_report()
    blocked, lines = check(bad, baseline, spec)
    assert blocked == ["integrity"]
    assert any("INTEGRITY" in line for line in lines)


def test_lab9_advanced_pass_k_estimators_obey_probability_order():
    from lab9.stats import pass_at_k, pass_hat_k

    for n in range(1, 10):
        for c in range(n + 1):
            for k in range(1, n + 1):
                assert -1e-12 <= pass_hat_k(n, c, k) <= c / n + 1e-12
                assert c / n - 1e-12 <= pass_at_k(n, c, k) <= 1 + 1e-12


@pytest.mark.parametrize("args", [(0, 0, 1), (5, -1, 1), (5, 6, 1), (5, 1, 0), (5, 1, 6),
                                 (5.0, 1, 1), (5, True, 1), (5, 1, 1.5)])
def test_lab9_advanced_both_pass_k_estimators_validate_arguments(args):
    from lab9.stats import pass_at_k, pass_hat_k

    for function in (pass_at_k, pass_hat_k):
        with pytest.raises(ValueError):
            function(*args)


@pytest.mark.parametrize("a,b", [([], []), ([1], [1, 0]), ([1, math.nan], [1, 0])])
def test_lab9_advanced_bootstrap_rejects_invalid_pairs(a, b):
    from lab9.stats import paired_bootstrap

    with pytest.raises(ValueError):
        paired_bootstrap(a, b)


def test_lab9_advanced_bootstrap_preserves_pairing_and_sign():
    from lab9.stats import paired_bootstrap

    assert paired_bootstrap([1, 0.5, 0], [0.5, 0, -0.5]) == (0.5, 0.5, 0.5)
    delta, lo, hi = paired_bootstrap([0, 0, 0], [1, 1, 1])
    assert (delta, lo, hi) == (-1.0, -1.0, -1.0)


def test_lab9_advanced_per_item_reliability_uses_all_seeds():
    from lab9.eval import per_item

    report = {"rows": [{"item_id": item, "seed": seed, "pass_rate": item == "reliable" or seed != 5}
                       for item in ("reliable", "flaky") for seed in (1, 2, 3, 4, 5)]}
    assert per_item(report, "pass_hat_5") == {"reliable": 1.0, "flaky": 0.0}
    assert per_item(report, "pass_at_5") == {"reliable": 1.0, "flaky": 1.0}


def test_lab9_advanced_cost_growth_from_a_zero_baseline_is_not_ignored():
    from lab9.gate import check

    spec, baseline = fixture_report()
    spec["metrics"].append({"id": "cost_per_success", "kind": "system", "blocking": True,
                            "threshold": {"max_increase": 0.1}})
    baseline["metrics"]["cost_per_success"] = 0.0
    for row in baseline["rows"]:
        row["cost"] = 0.0
    candidate = copy.deepcopy(baseline)
    candidate["metrics"]["cost_per_success"] = 1.0
    for row in candidate["rows"]:
        row["cost"] = 1.0
    assert check(baseline, baseline, spec)[0] == []
    assert check(candidate, baseline, spec)[0] == ["cost_per_success"]


def test_lab9_advanced_cli_reports_invalid_json_shape_without_traceback(tmp_path, capsys):
    import json
    from lab9.gate import main

    spec, baseline = fixture_report()
    candidate = tmp_path / "pr.json"
    base = tmp_path / "base.json"
    config = tmp_path / "spec.yaml"
    candidate.write_text("null", encoding="utf-8")
    base.write_text(json.dumps(baseline), encoding="utf-8")
    config.write_text(json.dumps(spec), encoding="utf-8")
    assert main(["--pr", str(candidate), "--baseline", str(base), "--spec", str(config)]) == 1
    output = capsys.readouterr().out
    assert "INTEGRITY" in output and "Traceback" not in output
