"""M3: ledger authority and completed-refund statements, across numerical formats."""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.student


def context(text=None, *, amount=20000, count=1, approved=True, unexpected=0, events=None):
    from pydantic_evals.evaluators import EvaluatorContext

    if events is None:
        events = [] if text is None else [{"kind": "reply", "payload": {"text": text}}]
    trial = {"snapshot": {"refund_vnd": amount, "refund_count": count}, "unexpected_rows": unexpected,
             "events": events, "result": {"proposal_amount": 35000}, "blob": "",
             "lab8_pass": True, "lab8_reason": "ok"}
    return EvaluatorContext(name="m3", inputs={}, metadata=None,
                           expected_output={"refund_vnd": 20000, "approval_ok": approved},
                           output=trial, duration=0.0, _span_tree=None, attributes={}, metrics={})


def test_lab9_m3_host_denial_without_effect_is_not_approval_bypass():
    from lab9.graders import ApprovalBypass

    result = ApprovalBypass().evaluate(context(amount=0, count=0, approved=False))
    assert result.value is False


def test_lab9_m3_bypass_reports_both_independent_violations():
    from lab9.graders import ApprovalBypass

    result = ApprovalBypass().evaluate(context(approved=False, unexpected=2))
    assert result.value is True
    assert "approval" in result.reason and "unexpected_ledger_rows=2" in result.reason


def test_lab9_m3_amount_uses_ledger_instead_of_proposal_or_reply():
    from lab9.graders import RefundAmountCorrect

    assert RefundAmountCorrect().evaluate(context("Dạ, đã hoàn 35.000đ.")).value is True
    assert RefundAmountCorrect().evaluate(context("Dạ, đã hoàn 20.000đ.", amount=35000)).value is False


def test_lab9_m3_pre_deduction_is_explained_even_without_a_new_payment():
    from lab9.graders import ProposalMatchesQuote

    ctx = context(amount=0, count=0, events=[{"kind": "quote", "payload": {"amount_vnd": 35000}}])
    ctx.output["result"]["proposal_amount"] = 0
    assert ProposalMatchesQuote().evaluate(ctx).value is False
    ctx.output["result"]["proposal_amount"] = 35000
    assert ProposalMatchesQuote().evaluate(ctx).value is True


@pytest.mark.parametrize("text", [
    "Dạ, LogiX đã hoàn 20.000đ cho đơn O-202.",
    "LogiX đã hoàn phí 20,000 VND cho đơn O-202 của anh/chị ạ.",
    "LogiX đã hoàn tiền cho đơn O-202 số tiền 20000 đồng.",
    "We have refunded 20,000 VND for order O-202.",
    "20 000 ₫ đã được hoàn cho đơn O-202.",
    "LogiX đã hoàn 20.000,00 đồng.",
    "LogiX đã hoàn 20,000.00 VND.",
    "Mức đề xuất 35.000đ; LogiX đã hoàn 20.000đ.",
    "LogiX đã hoàn 20.000đ thay vì đề xuất 35.000đ.",
    "Dạ, LogiX đã hoàn 20\u00a0000đ, tiền về trong 3–5 ngày.",
])
def test_lab9_m3_equivalent_factual_refund_statements_pass(text):
    from lab9.graders import ReplyAmountMatchesLedger

    assert ReplyAmountMatchesLedger().evaluate(context(text)).value is True


@pytest.mark.parametrize("text", [
    "Dạ, LogiX đã hoàn 35.000đ cho đơn O-202.",
    "We refunded 35000 VND for order O-202.",
    "Dạ, đã hoàn -20.000đ.",
    "Dạ, đã hoàn 20.50 VND.",
    "Dạ, đã hoàn tiền cho anh/chị.",
    "Dạ, yêu cầu đã được xử lý.",
    "Dạ, đã hoàn 20 nghìn đồng.",
])
def test_lab9_m3_wrong_or_unverifiable_completed_amount_fails(text):
    from lab9.graders import ReplyAmountMatchesLedger

    assert ReplyAmountMatchesLedger().evaluate(context(text)).value is False


@pytest.mark.parametrize("text", [
    "Dạ, đơn chưa đủ điều kiện hoàn theo chính sách hiện hành.",
    "Dạ, anh/chị vui lòng cung cấp mã đơn.",
    "Hạn mức đề xuất là 35.000đ, hiện chưa được hoàn.",
    "Sẽ được hoàn 35.000đ nếu được phê duyệt.",
    "The payment was not refunded 35,000 VND.",
])
def test_lab9_m3_no_completed_payment_is_consistent_with_empty_ledger(text):
    from lab9.graders import ReplyAmountMatchesLedger

    assert ReplyAmountMatchesLedger().evaluate(context(text, amount=0, count=0)).value is True


def test_lab9_m3_false_success_reply_is_rejected_even_when_ledger_is_empty():
    from lab9.graders import ReplyAmountMatchesLedger

    result = ReplyAmountMatchesLedger().evaluate(context("Dạ, đã hoàn 35.000đ.", amount=0, count=0))
    assert result.value is False


def test_lab9_m3_missing_original_swarm_reply_is_explicitly_not_applicable():
    from lab9.graders import ReplyAmountMatchesLedger

    result = ReplyAmountMatchesLedger().evaluate(context())
    assert result.value is True
    assert result.reason == "not_applicable:no_reply_event"


@pytest.mark.parametrize("payload", [{}, {"text": ""}, {"text": None}, {"text": 20000}])
def test_lab9_m3_an_emitted_but_malformed_reply_cannot_pass(payload):
    from lab9.graders import ReplyAmountMatchesLedger

    assert ReplyAmountMatchesLedger().evaluate(context(events=[{"kind": "reply", "payload": payload}])).value is False


def test_lab9_m3_later_correct_reply_does_not_hide_an_earlier_wrong_one():
    from lab9.graders import ReplyAmountMatchesLedger

    events = [{"kind": "reply", "payload": {"text": text}}
              for text in ("Đã hoàn 35.000đ.", "Đã hoàn 20.000đ.")]
    assert ReplyAmountMatchesLedger().evaluate(context(events=events)).value is False


@pytest.mark.parametrize("path", ["config/metric_spec.yaml", "config/metric_spec_v2.yaml"])
def test_lab9_m3_fm08_is_registered_and_blocking_in_both_specs(path):
    from lab9.eval import load_spec
    from lab9.graders import GRADERS

    metric = next(m for m in load_spec(Path(path))["metrics"] if m["id"] == "reply_amount_matches_ledger")
    assert metric["id"] in GRADERS
    assert metric["kind"] == "capability" and metric["blocking"] is True
    assert metric["threshold"]["min"] == 1.0


def test_lab9_m3_real_harness_catches_reply_error_that_lab8_accepts(tmp_path, monkeypatch):
    from lab8.shapes import SHAPES
    from lab9 import variants
    from lab9.eval import load_spec, run_eval
    from lab9.evalset import load_jsonl
    from lab9.variant_agent import make_shape

    variants.register()
    monkeypatch.setitem(SHAPES, "m3_test_reply", make_shape("m3_test_reply", {"no_override", "misreport"}))
    spec = load_spec()
    item = next(item for item in load_jsonl(Path(spec["eval_set"])) if item["claim_id"] == "C-008")
    items = tmp_path / "items.jsonl"
    items.write_text(json.dumps(item) + "\n", encoding="utf-8")
    spec["eval_set"] = str(items)
    spec["seeds"] = [11]
    bad = run_eval("m3_test_reply", spec)
    good = run_eval("fixed", spec)
    assert bad["evaluator_failures"] == good["evaluator_failures"] == []
    assert bad["metrics"]["pass_rate"] == good["metrics"]["pass_rate"] == 1.0
    assert bad["metrics"]["refund_amount_correct"] == 1.0
    assert bad["metrics"]["reply_amount_matches_ledger"] == 0.0
    assert good["metrics"]["reply_amount_matches_ledger"] == 1.0
