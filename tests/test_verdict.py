"""A row must never be more confident than the evidence under it."""

from __future__ import annotations

from pathlib import Path

from truecost import manifest, verdict
from truecost.core.report import Comparison

SUBJECTS = Path(__file__).resolve().parent.parent / "subjects"


def _comparison(baseline=0.3127, treatment=0.2787, lo=-0.05, hi=-0.01, pairs=3):
    return Comparison(
        metric="cost_usd",
        baseline_arm="off",
        treatment_arm="on",
        pairs=pairs,
        baseline_mean=baseline,
        treatment_mean=treatment,
        mean_delta=treatment - baseline,
        ci_low=lo,
        ci_high=hi,
    )


def _subject(name="portal-shunt"):
    return manifest.load(SUBJECTS / f"{name}.toml")


def test_verified_when_delivery_confirmed_and_control_clean():
    s = _subject()
    row = verdict.build(s, s.pairings[0], _comparison(), delivery_ok=True, control_clean=True)
    assert row.status == verdict.VERIFIED


def test_invalid_when_control_received_the_treatment():
    """Not a result about the tool. A result about the run."""
    s = _subject()
    row = verdict.build(s, s.pairings[0], _comparison(), delivery_ok=True, control_clean=False)
    assert row.status == verdict.INVALID
    assert row.measured == "—"
    assert "control" in row.reason


def test_invalid_when_treatment_never_delivered():
    s = _subject()
    row = verdict.build(s, s.pairings[0], _comparison(), delivery_ok=False, control_clean=True)
    assert row.status == verdict.INVALID


def test_unverifiable_arm_is_never_reported_as_verified():
    """A proxy tool leaves no transcript evidence. Say so rather than assume."""
    s = _subject("rtk")
    row = verdict.build(s, s.pairings[0], _comparison(), delivery_ok=True, control_clean=True)
    assert row.status == verdict.UNVERIFIED


def test_no_effect_when_interval_spans_zero():
    s = _subject()
    row = verdict.build(
        s,
        s.pairings[0],
        _comparison(lo=-0.05, hi=+0.05),
        delivery_ok=True,
        control_clean=True,
    )
    assert row.measured == "no effect"
    assert row.holds_up is False


def test_portal_claim_does_not_survive_billing_both_models():
    """-90% claimed; -10.9% once the delegate is billed."""
    s = _subject()
    row = verdict.build(
        s,
        s.pairings[0],
        _comparison(baseline=0.3127, treatment=0.2787),
        delivery_ok=True,
        control_clean=True,
        their_accounting_pct=-25.7,
    )
    assert row.claim.display == "-90.0%"
    assert row.measured == "-10.9%"
    assert row.holds_up is False
    assert row.their_accounting_pct == -25.7


def test_render_reports_their_accounting_beside_ours():
    s = _subject()
    row = verdict.build(
        s,
        s.pairings[0],
        _comparison(),
        delivery_ok=True,
        control_clean=True,
        their_accounting_pct=-25.7,
    )
    out = verdict.render([row])
    assert "-10.9%" in out
    assert "-25.7%" in out
    assert "their accounting" in out
    assert "0 claim(s) reproduced, 1 did not" in out


def test_render_flags_unverified_subjects():
    s = _subject("rtk")
    row = verdict.build(s, s.pairings[0], _comparison(), delivery_ok=True, control_clean=True)
    assert "delivery unverifiable" in verdict.render([row])


def test_insufficient_pairs_yields_no_interval():
    s = _subject()
    row = verdict.build(
        s, s.pairings[0], _comparison(pairs=1), delivery_ok=True, control_clean=True
    )
    assert row.interval == ""
