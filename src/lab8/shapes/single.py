"""Shape B — one bounded ReAct agent.

The agent may choose read tools for at most 8 steps. It cannot call
issue_refund; the shape submits the full code-computed quote to the host.
Ticket text is not an authority for order facts or policy decisions.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import issue_refund
from lab8.mock_llm import complete
from lab8.runtime import run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
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
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _run(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    seed: int,
    crash_at: str | None,
) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id("single", claim_id, seed))

    def decide(observation: dict[str, Any]) -> dict[str, Any]:
        previous_tool = observation.get("last_tool")
        previous_result = observation.get("last_result") or {}

        # The simulated model sees only the current tool name, never raw ticket text.
        complete(
            budget,
            seed=seed,
            purpose="single_decide",
            prompt=f"claim={claim_id}; previous_tool={previous_tool or 'start'}",
        )

        if previous_tool is None:
            action = {"tool": "get_claim_view", "args": {"claim_id": claim_id}}
        elif previous_tool == "get_claim_view":
            trace.add(
                "tool_result",
                {
                    "tool": previous_tool,
                    "found": bool(previous_result.get("found")),
                    "has_order_id": bool(previous_result.get("order_id")),
                },
            )
            if not previous_result.get("found"):
                action = {"final": {"status": "failed", "error_reason": "unknown_claim"}}
            elif not previous_result.get("order_id"):
                action = {"final": {"status": "needs_info", "error_reason": "missing_order_id"}}
            else:
                action = {
                    "tool": "lookup_order",
                    "args": {
                        "order_id": previous_result["order_id"],
                        "principal_id": previous_result["principal_id"],
                    },
                }
        elif previous_tool == "lookup_order":
            trace.add(
                "tool_result",
                {
                    "tool": previous_tool,
                    "visible": bool(previous_result.get("visible")),
                },
            )
            if not previous_result.get("visible"):
                action = {
                    "final": {
                        "status": "escalated",
                        "error_reason": previous_result.get("reason", "order_not_visible"),
                    }
                }
            else:
                action = {
                    "tool": "compute_compensation",
                    "args": {"order": previous_result["order"]},
                }
        elif previous_tool == "compute_compensation":
            quote = {
                "amount_vnd": int(previous_result.get("amount_vnd", 0)),
                "reason": previous_result.get("reason"),
                "clause_ids": previous_result.get("clause_ids", []),
                "parts": previous_result.get("parts", {}),
            }
            trace.add("quote", quote)
            action = {"final": {"decision": "quote", "quote": quote}}
        else:
            action = {"final": {"status": "failed", "error_reason": "unexpected_agent_state"}}

        trace.add(
            "agent_turn",
            {
                "turn": budget.model_calls,
                "previous_tool": previous_tool,
                "action": action.get("tool", "final"),
            },
        )
        return action

    react = run_react(
        conn,
        budget,
        observation={"claim_id": claim_id},
        decide=decide,
        max_steps=8,
    )
    final = react["final"]
    if final.get("decision") != "quote":
        trace.add("decision", {"status": final["status"]})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status=final["status"],
            proposal_amount=int(final.get("proposal_amount", 0)),
            budget=budget,
            trace=trace,
            error_reason=final.get("error_reason"),
        )

    proposal = int(final["quote"]["amount_vnd"])
    if proposal <= 0:
        trace.add("decision", {"status": "denied", "proposal_amount": 0})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="denied",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=final["quote"].get("reason"),
        )

    trace.add("host_request", {"tool": "issue_refund", "proposal_amount": proposal})
    # Persist a clean trace before the host call so an injected crash still has evidence.
    trace.write()
    outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    if not outcome["ok"]:
        status = "failed" if outcome["conflict"] else "denied"
        trace.add("host_result", {"status": status, "reason": outcome["reason"]})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=outcome["reason"],
        )

    trace.add("host_result", {"status": "resolved"})
    return finish(
        conn,
        shape="single",
        claim_id=claim_id,
        seed=seed,
        status="resolved",
        proposal_amount=proposal,
        budget=budget,
        trace=trace,
    )
