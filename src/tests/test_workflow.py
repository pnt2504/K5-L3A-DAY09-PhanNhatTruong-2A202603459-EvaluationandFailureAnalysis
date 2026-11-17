import time

from lab8.metrics import check_trace
from lab8.shapes.workflow import run_claim


def test_unknown_claim_returns_failed_with_fresh_trace(public_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    started_at = time.time()

    result = run_claim("C-UNKNOWN", seed=11, store_path=str(public_db))

    assert result.status == "failed"
    assert result.proposal_amount == 0
    assert result.error_reason == "unknown_claim"
    assert result.refund_effects == []
    assert check_trace(result.as_dict(), started_at=started_at) == (True, "ok")
