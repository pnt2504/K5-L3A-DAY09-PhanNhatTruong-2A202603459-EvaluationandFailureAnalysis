"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import evalset, stats
from lab9.eval import SPEC, aggregate, load_spec, per_item, spec_fingerprint
from lab9.graders import GRADERS


def _ratchet_problems(spec: dict, previous: dict) -> list[str]:
    if spec.get("eval_set_version") != previous.get("eval_set_version"):
        return []
    problems = []

    def compare(old: dict, new: dict, name: str, thresholds: bool) -> None:
        if old.get("blocking") and not new.get("blocking"):
            problems.append(f"ratchet {name}: blocking removed")
        before = old.get("threshold", {}) if thresholds else old
        after = new.get("threshold", {}) if thresholds else new
        for key in ("min", "max", "max_increase"):
            if key not in before:
                continue
            if key not in after or (after[key] < before[key] if key == "min" else after[key] > before[key]):
                problems.append(f"ratchet {name}: {key} loosened or removed")
        if before.get("no_significant_drop") and not after.get("no_significant_drop"):
            problems.append(f"ratchet {name}: no_significant_drop removed")
        for key in ("kind", "level", "grader"):
            if key in old and new.get(key) != old[key]:
                problems.append(f"ratchet {name}: {key} changed")

    current = {m["id"]: m for m in spec.get("metrics", [])}
    for old in previous.get("metrics", []):
        if old["id"] not in current:
            problems.append(f"ratchet metric {old['id']}: removed")
        else:
            compare(old, current[old["id"]], old["id"], True)
    slices = {(s["name"], s["metric"]): s for s in spec.get("slices", [])}
    for old in previous.get("slices", []):
        key = (old["name"], old["metric"])
        if key not in slices:
            problems.append(f"ratchet slice {key}: removed")
        else:
            compare(old, slices[key], f"slice {key}", False)
    return problems


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    if not isinstance(pr, dict) or not isinstance(base, dict):
        return ["report must be an object"]
    if not isinstance(spec, dict) or (base_spec is not None and not isinstance(base_spec, dict)):
        return ["metric specs must be objects"]
    definitions = spec.get("metrics", [])
    if not isinstance(definitions, list) or any(not isinstance(m, dict) or not isinstance(m.get("id"), str) for m in definitions):
        return ["invalid metric definitions"]
    slice_defs = spec.get("slices", [])
    if not isinstance(slice_defs, list) or any(not isinstance(s, dict) or not isinstance(s.get("name"), str)
                                              or not isinstance(s.get("metric"), str) for s in slice_defs):
        return ["invalid slice definitions"]
    for definition in definitions + slice_defs:
        thresholds = definition.get("threshold", {}) if "id" in definition else definition
        if not isinstance(thresholds, dict):
            return ["invalid thresholds"]
        if any(key in thresholds and (not isinstance(thresholds[key], (int, float))
                                      or isinstance(thresholds[key], bool) or not math.isfinite(thresholds[key]))
               for key in ("min", "max", "max_increase")):
            return ["thresholds must be finite numbers"]
    ids = [m["id"] for m in definitions]
    problems = []
    if len(ids) != len(set(ids)):
        problems.append("duplicate metric definitions")
    slice_ids = [(s["name"], s["metric"]) for s in spec.get("slices", [])]
    if len(slice_ids) != len(set(slice_ids)):
        problems.append("duplicate slice definitions")
    base_rows = base.get("rows")
    baseline_fields = set().union(*(r.keys() for r in base_rows if isinstance(r, dict))) if isinstance(base_rows, list) else set()
    graded = [mid for mid in ids if mid in GRADERS or mid in baseline_fields]
    kinds = {m["id"]: m.get("kind") for m in definitions}

    def finite(value) -> bool:
        return isinstance(value, (int, float)) and math.isfinite(value)

    def validate(rep: dict, name: str):
        rows, manifest, metrics = rep.get("rows"), rep.get("manifest"), rep.get("metrics")
        if not isinstance(rows, list) or not isinstance(manifest, dict) or not isinstance(metrics, dict):
            problems.append(f"{name}: missing rows/manifest/metrics")
            return None
        if not isinstance(rep.get("evaluator_failures", []), list) or rep.get("evaluator_failures"):
            problems.append(f"{name}: evaluator_failures is not empty")
        seeds, item_count = manifest.get("seeds"), manifest.get("items")
        if (not isinstance(seeds, list) or not seeds
                or any(not isinstance(s, int) or isinstance(s, bool) for s in seeds)
                or len(seeds) != len(set(seeds))):
            problems.append(f"{name}: seeds must be unique integers")
            return None
        if not isinstance(item_count, int) or isinstance(item_count, bool) or item_count < 1:
            problems.append(f"{name}: invalid item count")
            return None
        if len(rows) != item_count * len(seeds):
            problems.append(f"{name}: rows != manifest items x seeds")
        for mid, value in metrics.items():
            if not finite(value):
                problems.append(f"{name}: non-finite/missing aggregate {mid}")
        for mid in ids:
            if mid not in metrics:
                problems.append(f"{name}: aggregate {mid} missing")
        pairs, tags = [], {}
        valid_scores = True
        for index, row in enumerate(rows):
            if (not isinstance(row, dict) or not isinstance(row.get("item_id"), str) or not row["item_id"]
                    or not isinstance(row.get("seed"), int) or isinstance(row["seed"], bool)):
                problems.append(f"{name}: invalid item/seed row {index}")
                valid_scores = False
                continue
            item, seed = row["item_id"], row["seed"]
            pairs.append((item, seed))
            slices = row.get("slices", [])
            if not isinstance(slices, list) or any(not isinstance(s, str) for s in slices):
                problems.append(f"{name}: invalid slice tags at {item}")
                slices = []
            current_tags = frozenset(slices)
            if item in tags and tags[item] != current_tags:
                problems.append(f"{name}: inconsistent slice tags at {item}")
            tags[item] = current_tags
            for mid in graded:
                if not finite(row.get(mid)) or row[mid] not in (0, 1):
                    problems.append(f"{name}: missing/invalid {mid} at {item}@{seed}")
                    valid_scores = False
            if "cost" in row and (not finite(row["cost"]) or row["cost"] < 0):
                problems.append(f"{name}: invalid cost at {item}@{seed}")
                valid_scores = False
            if "cost_per_success" in ids and "cost" not in row:
                problems.append(f"{name}: missing cost at {item}@{seed}")
                valid_scores = False
        pair_set = set(pairs)
        if len(pairs) != len(pair_set):
            problems.append(f"{name}: duplicated item/seed rows")
        if len(tags) != item_count or pair_set != {(item, seed) for item in tags for seed in seeds}:
            problems.append(f"{name}: incomplete item/seed Cartesian product")
        if valid_scores and rows:
            if all("cost" in row for row in rows):
                expected = aggregate(rows, graded, k_values=spec.get("pass_k", []))
            else:
                expected = {mid: (sum(row[mid] for row in rows) if kinds[mid] == "safety"
                                  else round(sum(row[mid] for row in rows) / len(rows), 4)) for mid in graded}
            for mid in ids:
                if mid in expected and finite(expected[mid]) and finite(metrics.get(mid)):
                    if not math.isclose(metrics[mid], expected[mid], rel_tol=0.0, abs_tol=0.00005):
                        problems.append(f"{name}: aggregate {mid} does not match rows")
        return manifest, pair_set, tags

    left, right = validate(pr, "PR"), validate(base, "baseline")
    if left is not None and right is not None:
        if left[1] != right[1]:
            problems.append("PR and baseline item/seed sets differ")
        if left[2] != right[2]:
            problems.append("PR and baseline slice tags differ")
        if spec.get("seeds") is not None and (set(left[0]["seeds"]) != set(spec["seeds"])
                                               or set(right[0]["seeds"]) != set(spec["seeds"])):
            problems.append("manifest seeds differ from spec")
        if spec.get("eval_set"):
            path = Path(spec["eval_set"])
            if not path.is_file():
                problems.append("spec eval set file is missing")
            else:
                items = evalset.load_jsonl(path)
                expected_tags = {it["item_id"]: frozenset(it.get("slices", [])) for it in items}
                for name, info in (("PR", left), ("baseline", right)):
                    if info[0].get("eval_set_sha") != evalset.sha12(path) or info[2] != expected_tags:
                        problems.append(f"{name}: eval set hash/coverage/slices differ from source")
                if left[0].get("spec_sha") != spec_fingerprint(spec):
                    problems.append("PR spec fingerprint differs from evaluated spec")
        if spec.get("labels"):
            path = Path(spec["labels"])
            if not path.is_file() or any(info[0].get("labels_sha") != evalset.sha12(path) for info in (left, right)):
                problems.append("labels hash differs from source")
    if base_spec is not None:
        problems.extend(_ratchet_problems(spec, base_spec))
    return list(dict.fromkeys(problems))


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices", []):
        name, metric = entry["name"], entry["metric"]
        identity = f"slice:{name}/{metric}"
        current, previous = per_item(pr, metric, name), per_item(base, metric, name)
        failed = not current or current.keys() != previous.keys()
        note = "missing slice coverage" if failed else ""
        value = sum(current.values()) / len(current) if current else None
        if not failed:
            if "min" in entry and value < entry["min"]:
                failed = True
            if entry.get("no_significant_drop"):
                keys = sorted(current)
                delta, lo, hi = stats.paired_bootstrap([current[k] for k in keys], [previous[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027), confidence=bs.get("confidence", 0.95))
                note = f"delta {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                failed |= hi < 0
        if failed and entry.get("blocking"):
            blocked.append(identity)
        lines.append(f"  {identity} {value} {note} {'BLOCK' if failed and entry.get('blocking') else 'warn' if failed else 'ok'}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th:
            if base["metrics"].get(mid) is None:
                verdict = "missing"
            elif val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(a)
            if not keys or a.keys() != b.keys():
                verdict, note = "missing", "unaligned or missing paired metric"
            else:
                d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                                   n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                                                   confidence=bs.get("confidence", 0.95))
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    try:
        pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
        base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
        spec = load_spec(Path(args.spec))
    except (OSError, ValueError) as error:
        print(f"INTEGRITY cannot read report/spec: {error}")
        return 1
    if args.base_spec and not isinstance(base_spec, dict):
        print("INTEGRITY supplied base spec is not an object")
        return 1
    blocked, lines = check(pr, base, spec, base_spec)
    pr_id = pr.get("run_id", "unknown") if isinstance(pr, dict) else "invalid"
    base_id = base.get("run_id", "unknown") if isinstance(base, dict) else "invalid"
    print(f"gate: PR {pr_id} vs main {base_id}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
