"""Judge-the-judge: calibrate a replayed LLM judge against human labels.

    python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5

Default backend is REPLAY (the judge verdicts are stored in the CSV, zero key).
Floors (lecture S6): kappa >= 0.6, precision >= 0.8, recall >= 0.7.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats

FLOORS = {"kappa": 0.6, "precision": 0.8, "recall": 0.7}


def calibrate(path: Path) -> dict:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    human = [r["human"].strip().upper() for r in rows]
    judge = [r["judge"].strip().upper() for r in rows]
    p, r = stats.precision_recall(human, judge)
    try:
        k = stats.cohen_kappa(human, judge)
    except ValueError:
        k = float("nan")
    cm = stats.confusion(human, judge)
    spec = cm["tn"] / (cm["tn"] + cm["fp"]) if cm["tn"] + cm["fp"] else 0.0
    obs = (cm["tp"] + cm["fp"]) / len(rows)
    try:
        corrected = stats.rogan_gladen(obs, r, spec)
    except ValueError:
        corrected = None  # An uninformative judge cannot support prevalence correction.
    res = {"n": len(rows), "precision": round(p, 3), "recall": round(r, 3), "kappa": round(k, 3),
           "confusion": cm, "observed_fail_rate": round(obs, 3),
           "corrected_fail_rate": round(corrected, 3) if corrected is not None else None,
           "disagreements": [x for x, h, j in zip(rows, human, judge) if h != j]}
    # Judge the unrounded measurements; display rounding must never turn a fail into a pass.
    res["passed"] = all(value >= FLOORS[name] for name, value in
                        (("kappa", k), ("precision", p), ("recall", r)))
    return res


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.judge")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--audit", type=int, default=0, help="print N disagreements to audit by hand")
    ap.add_argument("--out", type=Path, help="save a reproducible calibration report as JSON")
    args = ap.parse_args(argv)
    res = calibrate(Path(args.csv))
    print(f"n={res['n']} P={res['precision']} R={res['recall']} kappa={res['kappa']} {res['confusion']}")
    print(f"fail rate observed {res['observed_fail_rate']} -> corrected {res['corrected_fail_rate']}")
    for row in res["disagreements"][: args.audit]:
        print(f"  {row['item_id']} human={row['human']} judge={row['judge']} | {row['reply'][:90]}")
    print("PASS floors" if res["passed"] else "FAIL floors", FLOORS)
    if args.out:
        source = Path(args.csv)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        payload = {"run_id": f"J-{source.stem}-{digest[:12]}", "source": str(source),
                   "source_sha256": digest, "floors": FLOORS,
                   "calibration": {**res, "kappa": res["kappa"] if math.isfinite(res["kappa"]) else None}}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                            encoding="utf-8")
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
