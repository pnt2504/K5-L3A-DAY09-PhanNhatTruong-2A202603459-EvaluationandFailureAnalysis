"""Integration: the three student shapes merged into main behave as one system.

Owner: integration. Part of the default host gate (`python -m pytest -q`).

The student matrix checks each shape against labels one at a time. These tests
check what only shows up after merging: the shapes agree with each other on
the same claim and seed, they share the host's idempotency on one store, and
every shape keeps the `run_claim` contract (run_id, status set, clean trace).
"""

from __future__ import annotations

import time

import pytest

from lab8.db import connect, init_store
from lab8.durability import committed_audit_count, get_refund
from lab8.metrics import check_trace, ledger_snapshot
from lab8.schemas import STATUSES, make_run_id
from lab8.shapes import orchestrator, single, workflow
from tests.conftest import CLAIMS, WORLD

SHAPES = {
    "workflow": workflow.run_claim,
    "single": single.run_claim,
    "orchestrator": orchestrator.run_claim,
}
CLAIM_IDS = [row["claim_id"] for row in CLAIMS]


@pytest.fixture(autouse=True)
def _traces_in_tmp(tmp_path, monkeypatch):
    # lab8.trace.Trace writes to ./traces: keep test traces out of the repo.
    monkeypatch.chdir(tmp_path)


def _fresh_store(tmp_path, name: str):
    store = tmp_path / f"{name}.sqlite"
    init_store(store, WORLD, CLAIMS).close()
    return store


@pytest.mark.parametrize("claim_id", CLAIM_IDS)
def test_three_shapes_agree_on_status_amount_and_ledger(tmp_path, claim_id):
    """Same claim, same seed, fresh store per shape -> same decision and same ledger."""
    outcomes = {}
    for shape, run_claim in SHAPES.items():
        store = _fresh_store(tmp_path, f"{shape}-{claim_id}")
        result = run_claim(claim_id, seed=11, store_path=str(store))
        conn = connect(store)
        try:
            ledger = ledger_snapshot(conn, claim_id)
        finally:
            conn.close()
        outcomes[shape] = (
            result.status,
            result.proposal_amount,
            ledger["refund_count"],
            ledger["refund_vnd"],
            ledger["committed_audit_count"],
            ledger["policy_denied"],
        )

    assert len(set(outcomes.values())) == 1, outcomes


@pytest.mark.parametrize("shape", list(SHAPES))
@pytest.mark.parametrize("claim_id", ["C-001", "C-014"])
def test_every_shape_keeps_the_run_claim_contract(tmp_path, shape, claim_id):
    store = _fresh_store(tmp_path, f"contract-{shape}-{claim_id}")
    started_at = time.time()

    result = SHAPES[shape](claim_id, seed=22, store_path=str(store))

    assert result.shape == shape
    assert result.claim_id == claim_id
    assert result.run_id == make_run_id(shape, claim_id, 22)
    assert result.status in STATUSES
    assert isinstance(result.proposal_amount, int)
    assert check_trace(result.as_dict(), started_at=started_at) == (True, "ok")


def test_shapes_share_host_idempotency_on_one_store(tmp_path):
    """Workflow, then single, then orchestrator on the same claim and store -> still one refund."""
    store = _fresh_store(tmp_path, "shared")
    claim_id = "C-001"  # T01: one refund of 35 000 VND

    results = [run_claim(claim_id, seed=11, store_path=str(store)) for run_claim in SHAPES.values()]

    assert [r.status for r in results] == ["resolved", "resolved", "resolved"]
    conn = connect(store)
    try:
        effect = get_refund(conn, claim_id)
        assert effect is not None
        assert int(effect["amount_vnd"]) == 35000
        assert committed_audit_count(conn, claim_id) == 1
        rows = conn.execute(
            "SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = ?", (claim_id,)
        ).fetchone()
        assert int(rows["n"]) == 1
    finally:
        conn.close()


def test_money_does_not_depend_on_seed_for_any_shape(tmp_path):
    """Seed only changes MockLLM; the refund amount must come from code, so it cannot move."""
    claim_id = "C-002"  # T02: ticket says 5 days late, order row says 2 -> no refund
    for shape, run_claim in SHAPES.items():
        amounts = set()
        for seed in (11, 22, 33, 44, 55):
            store = _fresh_store(tmp_path, f"seed-{shape}-{seed}")
            result = run_claim(claim_id, seed=seed, store_path=str(store))
            amounts.add((result.status, result.proposal_amount))
        assert amounts == {("denied", 0)}, (shape, amounts)
