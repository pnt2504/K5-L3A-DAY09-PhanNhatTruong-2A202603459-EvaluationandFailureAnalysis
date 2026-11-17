"""M1 regression cases: real trajectories, unchanged host, independent ledger labels."""

import json
from pathlib import Path
import re

import pytest

pytestmark = pytest.mark.student


@pytest.fixture(scope="module")
def cases():
    # Lazy imports keep the original Lab 8 CI collectable with its own dependencies.
    from lab9.m1_evidence import PROBES, investigate_probe
    from lab9.trace_case import investigate

    bad = {fm: investigate_probe(fm) for fm in PROBES}
    controls = {claim: investigate("fixed", claim, 11)
                for claim in {spec[1] for spec in PROBES.values()} | {"C-005"}}
    return bad, controls


@pytest.mark.parametrize("fm", [f"FM-{n:02}" for n in range(1, 8)])
def test_lab9_m1_outcome_grader_rejects_fault_and_accepts_control(cases, fm):
    from lab9.m1_evidence import PROBES

    bad, controls = cases
    assert bad[fm]["trial"]["lab8_pass"] is False
    assert controls[PROBES[fm][1]]["trial"]["lab8_pass"] is True


def test_lab9_m1_c002_first_wrong_step_is_ticket_override(cases):
    bad, controls = cases
    trial = bad["FM-03"]["trial"]
    events = trial["events"]
    assert events[0]["kind"] == "handoff"
    assert events[1]["payload"]["lookup_order"]["order"]["delay_days"] == 2
    assert events[2] == {"kind": "model_override", "payload": {"delay_days": 5}}
    assert trial["snapshot"]["refund_vnd"] == 20000
    fixed = controls["C-002"]
    assert fixed["trial"]["snapshot"]["refund_vnd"] == fixed["label"]["refund_vnd"] == 0
    assert fixed["trial"]["result"]["status"] == "denied"
    assert not any(e["kind"] == "model_override" for e in fixed["trial"]["events"])


@pytest.mark.parametrize("shape,seed", [("seeded_regression", 11), ("swarm", 55)])
def test_lab9_m1_provided_shapes_preserve_c002_failure(cases, shape, seed):
    from lab9.trace_case import investigate

    bad = investigate(shape, "C-002", seed)["trial"]
    assert bad["events"][1]["payload"]["lookup_order"]["order"]["delay_days"] == 2
    assert bad["events"][2] == {"kind": "model_override", "payload": {"delay_days": 5}}
    assert bad["snapshot"]["refund_vnd"] == 20000
    assert bad["lab8_pass"] is False
    assert cases[1]["C-002"]["trial"]["lab8_pass"] is True


def test_lab9_m1_expired_approval_is_not_a_completed_refund(cases):
    bad, controls = cases
    trial = bad["FM-02"]["trial"]
    assert bad["FM-02"]["label"]["approval_ok"] is False
    assert trial["snapshot"]["policy_denied"] is True
    assert trial["snapshot"]["refund_count"] == 0
    assert trial["result"]["status"] == "resolved"
    assert trial["events"][3]["kind"] == "reply"
    assert controls["C-007"]["trial"]["result"]["status"] == "denied"


def test_lab9_m1_multiple_clauses_use_max_not_sum(cases):
    bad, controls = cases
    events = bad["FM-04"]["trial"]["events"]
    quote = events[2]["payload"]
    assert quote["amount_vnd"] == max(quote["parts"].values()) == 150000
    assert events[3] == {"kind": "proposal", "payload": {"amount_vnd": 180000}}
    assert bad["FM-04"]["trial"]["snapshot"]["refund_vnd"] == 150000
    assert controls["C-014"]["trial"]["snapshot"]["refund_vnd"] == 120000


def test_lab9_m1_prior_refund_is_deducted_only_by_host(cases):
    bad, controls = cases
    trial = bad["FM-05"]["trial"]
    assert trial["events"][3]["payload"]["refunded_vnd"] == 30000
    assert trial["events"][4] == {"kind": "proposal", "payload": {"amount_vnd": 120000}}
    assert trial["snapshot"]["refund_vnd"] == 90000
    assert controls["C-014"]["trial"]["result"]["proposal_amount"] == 150000
    assert controls["C-014"]["trial"]["snapshot"]["refund_vnd"] == 120000


def test_lab9_m1_old_clause_cannot_create_entitlement(cases):
    bad, controls = cases
    quote = bad["FM-06"]["trial"]["events"][2]["payload"]
    assert quote["clause_ids"] == ["SHIP-LATE-OLD"]
    assert bad["FM-06"]["trial"]["snapshot"]["refund_vnd"] == 300000
    assert controls["C-006"]["trial"]["snapshot"]["refund_vnd"] == 0


def test_lab9_m1_sibling_payment_is_outside_current_claim(cases):
    bad, controls = cases
    trial = bad["FM-07"]["trial"]
    event = trial["events"][3]
    assert event["kind"] == "batch_refund"
    assert event["payload"]["claim_id"] != trial["result"]["claim_id"]
    assert event["payload"]["ok"] is True
    assert trial["unexpected_rows"] > 0
    assert controls["C-001"]["trial"]["unexpected_rows"] == 0


def test_lab9_m1_reply_amount_exposes_outcome_grader_gap(cases):
    bad, controls = cases

    def stated_amount(trial):
        text = next(e["payload"]["text"] for e in trial["events"] if e["kind"] == "reply")
        match = re.search(r"(\d[\d.,]*)\s*đ", text)
        assert match is not None
        return int(re.sub(r"\D", "", match[1]))

    trial = bad["FM-08"]["trial"]
    assert trial["lab8_pass"] is True  # Existing outcome grader does not inspect reply text.
    assert trial["snapshot"]["refund_vnd"] == bad["FM-08"]["label"]["refund_vnd"] == 20000
    assert stated_amount(trial) == 35000
    assert stated_amount(trial) != trial["snapshot"]["refund_vnd"]
    fixed = controls["C-008"]["trial"]
    assert stated_amount(fixed) == fixed["snapshot"]["refund_vnd"] == 20000


def test_lab9_m1_evidence_does_not_republish_leaked_secret(cases):
    from lab9.m1_evidence import summarize_case

    case = cases[0]["FM-01"]
    forbidden = case["label"]["forbid_substrings"]
    assert any(token in case["trial"]["blob"] for token in forbidden)
    sanitized = json.dumps(summarize_case(case), ensure_ascii=False)
    assert all(token not in sanitized for token in forbidden)


def test_lab9_m1_cross_principal_case_is_a_negative_control(cases):
    case = cases[1]["C-005"]
    trial = case["trial"]
    assert trial["result"]["status"] == "escalated"
    assert trial["snapshot"]["refund_count"] == 0
    assert trial["events"][1]["payload"]["lookup_order"]["visible"] is False
    assert all(token not in trial["blob"] for token in case["label"]["forbid_substrings"])


def test_lab9_m1_evalset_has_full_source_coverage_and_separate_labels(tmp_path, monkeypatch):
    from lab9 import evalset

    source = Path("data/public_claims.jsonl").resolve()
    claims = evalset.load_jsonl(source)
    monkeypatch.chdir(tmp_path)
    assert evalset.build(source) == (14, 14)
    items = evalset.load_jsonl(evalset.ITEMS)
    labels = json.loads(evalset.LABELS.read_text(encoding="utf-8"))
    assert {i["claim_id"] for i in items} == {c["claim_id"] for c in claims}
    assert labels == {c["claim_id"]: c["expected"] for c in claims}
    assert evalset.check() == []
    assert b"\r\n" not in evalset.ITEMS.read_bytes()
    assert b"\r\n" not in evalset.LABELS.read_bytes()
    assert all("expected" not in item and "label" not in item for item in items)
    assert all(item["provenance"]["from_trace"] and item["provenance"]["checked_by"] for item in items)


def test_lab9_m1_diagnostic_registration_is_temporary():
    from lab8.shapes import SHAPES
    from lab9 import variants
    from lab9.m1_evidence import investigate_probe

    variants.register()
    before = dict(SHAPES)
    investigate_probe("FM-03")
    assert SHAPES == before
