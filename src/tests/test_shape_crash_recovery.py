from contextlib import closing

import pytest

from lab8.db import connect
from lab8.durability import InjectedCrash, committed_audit_count, get_refund
from lab8.shapes import SHAPES


@pytest.mark.parametrize("shape", ["workflow", "single", "orchestrator"])
@pytest.mark.parametrize(
    ("crash_at", "effect_exists", "checkpoint_exists"),
    [
        ("before_effect", False, False),
        ("after_effect_before_checkpoint", True, False),
        ("after_checkpoint", True, True),
    ],
)
def test_shape_resumes_refund_at_each_crash_point(
    public_db, tmp_path, monkeypatch, shape, crash_at, effect_exists, checkpoint_exists
):
    monkeypatch.chdir(tmp_path)
    claim_id = "C-012"
    run_claim = SHAPES[shape]
    checkpoint_query = "SELECT 1 FROM checkpoints WHERE claim_id = ? AND step = 'issue_refund'"

    with pytest.raises(InjectedCrash, match=crash_at):
        run_claim(claim_id, seed=11, store_path=str(public_db), crash_at=crash_at)

    with closing(connect(public_db)) as conn:
        assert (get_refund(conn, claim_id) is not None) == effect_exists
        assert committed_audit_count(conn, claim_id) == int(effect_exists)
        assert (conn.execute(checkpoint_query, (claim_id,)).fetchone() is not None) == checkpoint_exists

    resumed = run_claim(claim_id, seed=11, store_path=str(public_db))
    replayed = run_claim(claim_id, seed=11, store_path=str(public_db))

    assert resumed.status == replayed.status == "resolved"
    assert resumed.proposal_amount == replayed.proposal_amount == 35000
    assert resumed.refund_effects == replayed.refund_effects
    with closing(connect(public_db)) as conn:
        amounts = conn.execute("SELECT amount_vnd FROM refund_ledger WHERE claim_id = ?", (claim_id,))
        assert [row["amount_vnd"] for row in amounts] == [35000]
        assert committed_audit_count(conn, claim_id) == 1
        assert conn.execute(checkpoint_query, (claim_id,)).fetchone() is not None
