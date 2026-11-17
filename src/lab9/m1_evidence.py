"""Reproduce M1 evidence without implementing M2/M3 or editing the frozen agent.

Run from src/: python -m lab9.m1_evidence
Reports are generated, never hand edited. Diagnostic shapes use existing bug
switches and are registered only for the duration of each investigation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from lab8.console import utf8_stdio
from lab8.shapes import SHAPES
from lab9.evalset import ITEMS, LABELS, SOURCE, load_jsonl, sha12
from lab9.trace_case import investigate
from lab9.variant_agent import make_shape

SEEDS = (11, 22, 33, 44, 55)
# FM -> existing bug switch, public input, first observable wrong event.
# An unlogged internal operation may precede that event; see the taxonomy.
PROBES = {
    "FM-01": ("leaky_trace", "C-010", "debug_claim_row"),
    "FM-02": ("ignore_denied", "C-007", "reply"),
    "FM-03": ("ticket_trust", "C-002", "model_override"),
    "FM-04": ("sum_parts", "C-014", "proposal"),
    "FM-05": ("pre_deducted", "C-014", "proposal"),
    "FM-06": ("stale_clause", "C-006", "quote"),
    "FM-07": ("sibling_refund", "C-001", "batch_refund"),
    "FM-08": ("misreport", "C-008", "reply"),
}


def investigate_probe(failure_mode: str) -> dict[str, Any]:
    bug, claim_id, _ = PROBES[failure_mode]
    name = f"m1_{bug}"
    previous = SHAPES.get(name)
    SHAPES[name] = make_shape(name, {"no_override", bug})
    try:
        return investigate(name, claim_id, 11)
    finally:
        if previous is None:
            SHAPES.pop(name, None)
        else:
            SHAPES[name] = previous


def summarize_case(case: dict[str, Any]) -> dict[str, Any]:
    """Retain observable evidence without propagating a deliberately leaked secret."""
    trial, label = case["trial"], case["label"]
    forbidden = label.get("forbid_substrings") or []

    def redact(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: redact(item) for key, item in value.items()}
        if isinstance(value, list):
            return [redact(item) for item in value]
        if isinstance(value, str):
            for token in sorted(filter(None, forbidden), key=len, reverse=True):
                value = value.replace(token, "[REDACTED]")
        return value

    events = []
    for step, event in enumerate(trial["events"], 1):
        if event["kind"] == "debug_claim_row":
            # The diagnostic intentionally violates the contract; retain keys only.
            payload = {"redacted": True, "field_names": sorted(event["payload"])}
        else:
            payload = redact(event["payload"])
        events.append({"step": step, "kind": event["kind"], "payload": payload})
    return {
        "run_id": trial["result"]["run_id"],
        "claim_id": trial["result"]["claim_id"],
        "seed": trial["result"]["seed"],
        "status": trial["result"]["status"],
        "proposal_amount": trial["result"]["proposal_amount"],
        "snapshot": trial["snapshot"],
        "unexpected_rows": trial["unexpected_rows"],
        "lab8_pass": trial["lab8_pass"],
        "lab8_reason": redact(trial["lab8_reason"]),
        "expected": {key: value for key, value in label.items() if key != "forbid_substrings"},
        "events": events,
    }


def build_evidence() -> dict[str, Any]:
    fixed = [summarize_case(investigate("fixed", item["claim_id"], seed))
             for item in load_jsonl(ITEMS) for seed in SEEDS]
    probes = []
    for fm, (bug, claim_id, kind) in PROBES.items():
        case = summarize_case(investigate_probe(fm))
        case.update({"failure_mode": fm, "bug_switch": bug,
                     "first_observable_wrong_step": next(e["step"] for e in case["events"] if e["kind"] == kind),
                     "control_run_id": f"R-fixed-{claim_id}-s11"})
        probes.append(case)
    # These are provided shapes; no diagnostic switch is needed for the core case.
    anchors = [summarize_case(investigate(shape, claim, seed)) for shape, claim, seed in (
        ("seeded_regression", "C-002", 11),
        ("seeded_regression", "C-007", 11),
        ("seeded_regression", "C-014", 11),
        ("swarm", "C-002", 55),
    )]
    return {
        "run_id": f"M1-{sha12(ITEMS)}",
        "manifest": {"eval_set_sha": sha12(ITEMS), "labels_sha": sha12(LABELS),
                     "source_sha": sha12(SOURCE), "world_sha": sha12(Path("data/public_world_state.json")),
                     "seeds": list(SEEDS), "backend": "MockLLM", "diagnostics": "existing switches; no agent source changes"},
        "fixed": fixed, "probes": probes, "provided_shape_anchors": anchors,
    }


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.m1_evidence")
    ap.add_argument("--out", type=Path, default=Path("reports/m1_evidence.json"))
    args = ap.parse_args(argv)
    report = build_evidence()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    passed = sum(row["lab8_pass"] for row in report["fixed"])
    print(f"{report['run_id']}: fixed {passed}/{len(report['fixed'])}; wrote {args.out}")
    for row in report["probes"]:
        print(f"{row['failure_mode']} {row['run_id']} step={row['first_observable_wrong_step']} "
              f"ledger={row['snapshot']['refund_vnd']} expected={row['expected']['refund_vnd']} "
              f"lab8_pass={row['lab8_pass']}")
    # FM-08 deliberately demonstrates a gap in the unchanged Lab 8 outcome grader.
    # Its reply/ledger assertion is a separate regression test, not a rewritten score.
    return 0 if passed == len(report["fixed"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
