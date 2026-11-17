"""Shape C — orchestrator plus read-only investigators. Student work.

1. Build a handoff with `lab8.handoff.make_handoff`. Allowed tools are read-only.
   Never put parent_secret, raw headers, or the full claim row into facts.
2. `lab8.runtime.run_readonly_investigators` runs those tools.
3. The orchestrator quotes from the investigator's order view and calls
   `durability.issue_refund`. Investigators have no write registry.
   Pass the full quote; the host subtracts earlier refunds on the same order.
   `lookup_refund_history` is a read-only tool you may hand to an investigator.
4. Trace the sanitized handoff, not the parent context.

An LLM summary of the parent context is not a sanitizer. Use the allowlist.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import sqlite3

from lab8.db import connect
from lab8.durability import issue_refund
from lab8.handoff import make_handoff
from lab8.runtime import run_readonly_investigators
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.tools import compute_compensation, get_claim_view, tool_cost
from lab8.trace import Trace


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        budget = Budget()
        trace = Trace(make_run_id("orchestrator", claim_id, seed))
        status, proposal, reason = _process_claim(conn, claim_id, budget, trace, crash_at=crash_at)
        trace.add("decision", {"status": status, "proposal_amount": proposal, "reason": reason})
        return finish(
            conn,
            shape="orchestrator",
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=reason,
        )
    finally:
        conn.close()


def _process_claim(
    conn: sqlite3.Connection,
    claim_id: str,
    budget: Budget,
    trace: Trace,
    *,
    crash_at: str | None,
) -> tuple[str, int, str | None]:
    budget.add_tool(tool_cost())
    claim = get_claim_view(conn, claim_id)
    trace.add("claim_lookup", {"found": claim["found"], "has_order_id": bool(claim.get("order_id"))})
    if not claim["found"]:
        return "failed", 0, "unknown_claim"
    if not claim.get("order_id"):
        return "needs_info", 0, "missing_order_id"

    handoff = make_handoff(
        request_id=f"REQ-{trace.run_id}",
        claim_id=claim_id,
        task="check_order_visibility",
        facts={},
        allowed_tools=["lookup_order"],
    )
    trace.add("handoff", handoff)
    investigation = run_readonly_investigators(conn, budget, handoff, principal_id=claim["principal_id"])
    order_view = investigation["tools"]["lookup_order"]
    trace.add("order_lookup", {"visible": order_view["visible"], "reason": order_view["reason"]})
    if not order_view["visible"]:
        return "escalated", 0, order_view["reason"]

    budget.add_tool(tool_cost())
    quote = compute_compensation(conn, order_view["order"])
    proposal = quote["amount_vnd"]
    trace.add("quote", quote)
    if proposal <= 0:
        return "denied", 0, quote["reason"]

    trace.add("host_request", {"tool": "issue_refund", "proposal_amount": proposal})
    trace.write()
    outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    trace.add("host_result", {"ok": outcome["ok"], "reason": outcome["reason"]})
    if outcome["ok"]:
        return "resolved", proposal, None
    return ("failed" if outcome["conflict"] else "denied"), proposal, outcome["reason"]
